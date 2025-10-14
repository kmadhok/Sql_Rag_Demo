#!/usr/bin/env python3
"""
bq_join_mapper.py

Discover and test likely join keys across tables in a BigQuery dataset
using only schema + sampled values (no LLM). Results are written to:

- meta.join_tests : every tested pair with metrics
- meta.join_map   : accepted joins (FK->PK / 1-1) with join SQL snippet

Usage:
  python bq_join_mapper.py --project YOUR_PROJECT --dataset YOUR_DATASET \
      [--region US] [--sample_pct 2] [--min_score 0.70] [--max_pairs 10000]
"""

import argparse
import datetime as dt
import json
import re
from typing import Dict, List, Tuple

from google.cloud import bigquery

# ---------- Config defaults ----------
DEFAULT_REGION = "US"
DEFAULT_SAMPLE_PCT = 2         # ≈2% deterministic hash sample
DEFAULT_MIN_SCORE = 0.70
DEFAULT_MAX_PAIRS = 10000
MIN_NONNULL_KEYS = 200         # need enough evidence to evaluate
MAX_BYTES_BILLED = 5 * 10**9   # 5 GB per job cap

# ---------- Helper: create meta tables if not exist ----------
def ensure_meta_tables(bq: bigquery.Client, project: str, region: str):
    dataset_id = f"{project}.meta"
    try:
        bq.get_dataset(dataset_id)
    except Exception:
        bq.create_dataset(bigquery.Dataset(dataset_id), exists_ok=True)

    join_tests_schema = [
        bigquery.SchemaField("run_ts", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("left_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("left_column", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("right_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("right_column", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("left_norm", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("right_norm", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("a_nonnull", "INT64"),
        bigquery.SchemaField("a_matched", "INT64"),
        bigquery.SchemaField("coverage_ab", "FLOAT"),
        bigquery.SchemaField("conflict_rate_ab", "FLOAT"),
        bigquery.SchemaField("uniq_ratio_a", "FLOAT"),
        bigquery.SchemaField("uniq_ratio_b", "FLOAT"),
        bigquery.SchemaField("jaccard", "FLOAT"),
        bigquery.SchemaField("name_signal", "FLOAT"),
        bigquery.SchemaField("type_signal", "FLOAT"),
        bigquery.SchemaField("semantic_match", "FLOAT"),
        bigquery.SchemaField("score", "FLOAT"),
        bigquery.SchemaField("decision", "STRING"),
        bigquery.SchemaField("bytes_estimated", "INT64"),
        bigquery.SchemaField("query_sql", "STRING"),
    ]
    join_map_schema = [
        bigquery.SchemaField("run_ts", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("left_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("left_column", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("right_table", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("right_column", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("left_norm", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("right_norm", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("decision", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("score", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("join_sql", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("coverage_ab", "FLOAT"),
        bigquery.SchemaField("conflict_rate_ab", "FLOAT"),
        bigquery.SchemaField("uniq_ratio_b", "FLOAT"),
        bigquery.SchemaField("jaccard", "FLOAT"),
    ]

    bq.create_table(bigquery.Table(f"{dataset_id}.join_tests", schema=join_tests_schema), exists_ok=True)
    bq.create_table(bigquery.Table(f"{dataset_id}.join_map", schema=join_map_schema), exists_ok=True)


# ---------- Step 1: list columns (exclude time types) ----------
def fetch_candidate_columns(bq: bigquery.Client, project: str, dataset: str, region: str) -> List[Dict]:
    sql = f"""
    SELECT
      CONCAT(table_schema,'.',table_name) AS tbl,
      column_name,
      UPPER(data_type) AS data_type
    FROM `{project}.{region}`.INFORMATION_SCHEMA.COLUMNS
    WHERE table_schema = @dataset
      AND UPPER(data_type) NOT IN ('DATE','DATETIME','TIMESTAMP','TIME')
    ORDER BY tbl, column_name
    """
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("dataset", "STRING", dataset)],
            maximum_bytes_billed=MAX_BYTES_BILLED,
        ),
    )
    return [dict(row) for row in job.result()]


# ---------- Step 2: light semantic tagging + normalizer guess ----------
SEMANTIC_REGEXES = {
    "digits_only": r"^\d+$",
    "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "alnum": r"^[a-z0-9]+$",
}

def pick_normalizers_for_column(data_type: str) -> List[str]:
    """Return a small set of candidate normalizers to try for this column."""
    if data_type in ("INT64", "NUMERIC", "BIGNUMERIC"):
        return ["digits_only"]  # cast to string then strip non-digits is safe
    # STRING and others:
    return ["lower_trim", "alnum", "digits_only"]


# ---------- SQL snippets ----------
def norm_expr(col_expr: str, norm: str) -> str:
    if norm == "digits_only":
        return f"REGEXP_REPLACE(LOWER(TRIM(CAST({col_expr} AS STRING))), r'\\D', '')"
    if norm == "alnum":
        return f"REGEXP_REPLACE(LOWER(TRIM(CAST({col_expr} AS STRING))), r'[^a-z0-9]', '')"
    # default lower_trim
    return f"LOWER(TRIM(CAST({col_expr} AS STRING)))"

SAMPLE_FILTER = "ABS(MOD(FARM_FINGERPRINT(k), CAST(100/ @sample_pct AS INT64))) = 0"  # ~ sample_pct%

# per-column quick profile on sample (uniq_ratio etc.)
def column_profile_sql(table_fqn: str, column: str, norm: str) -> str:
    k = norm_expr(column, norm)
    return f"""
    WITH base AS (
      SELECT {k} AS k
      FROM `{table_fqn}`
      WHERE {column} IS NOT NULL
    ),
    sampled AS (
      SELECT k FROM base
      WHERE {SAMPLE_FILTER}
    )
    SELECT
      COUNT(*) AS nonnull,
      APPROX_COUNT_DISTINCT(k) AS approx_uniques
    FROM sampled
    """

# pair test SQL
def pair_test_sql(left_fqn: str, left_col: str, left_norm: str,
                  right_fqn: str, right_col: str, right_norm: str) -> str:
    la = norm_expr(left_col, left_norm)
    rb = norm_expr(right_col, right_norm)
    return f"""
    DECLARE sample_pct INT64 DEFAULT @sample_pct;

    WITH
    A AS (
      SELECT {la} AS k
      FROM `{left_fqn}`
      WHERE {left_col} IS NOT NULL
    ),
    B AS (
      SELECT {rb} AS k
      FROM `{right_fqn}`
      WHERE {right_col} IS NOT NULL
    ),
    A_s AS (SELECT k FROM A WHERE {SAMPLE_FILTER}),
    B_s AS (SELECT k FROM B WHERE {SAMPLE_FILTER}),

    A_stats AS (
      SELECT COUNT(*) AS a_nonnull, SAFE_DIVIDE(APPROX_COUNT_DISTINCT(k), COUNT(*)) AS uniq_ratio_a FROM A_s
    ),
    B_stats AS (
      SELECT SAFE_DIVIDE(APPROX_COUNT_DISTINCT(k), COUNT(*)) AS uniq_ratio_b FROM B_s
    ),
    J AS (
      SELECT A_s.k, COUNTIF(B_s.k IS NOT NULL) AS b_hits
      FROM A_s LEFT JOIN B_s USING (k)
      GROUP BY 1
    ),
    overlap AS (
      SELECT
        (SELECT COUNT(*) FROM (SELECT k FROM A_s INTERSECT DISTINCT SELECT k FROM B_s)) AS inter_cnt,
        (SELECT COUNT(*) FROM (SELECT k FROM A_s UNION DISTINCT SELECT k FROM B_s))     AS union_cnt
    )
    SELECT
      (SELECT a_nonnull FROM A_stats) AS a_nonnull,
      COUNTIF(b_hits>0)               AS a_matched,
      SAFE_DIVIDE(COUNTIF(b_hits>0), (SELECT a_nonnull FROM A_stats)) AS coverage_ab,
      SAFE_DIVIDE(COUNTIF(b_hits>1), NULLIF(COUNTIF(b_hits>0),0))     AS conflict_rate_ab,
      (SELECT uniq_ratio_a FROM A_stats) AS uniq_ratio_a,
      (SELECT uniq_ratio_b FROM B_stats) AS uniq_ratio_b,
      SAFE_DIVIDE((SELECT inter_cnt FROM overlap), NULLIF((SELECT union_cnt FROM overlap),0)) AS jaccard
    FROM J
    """

# ---------- Scoring ----------
def score_and_decide(metrics: Dict, name_signal: float, type_signal: float, semantic_match: float) -> Tuple[float, str]:
    coverage = metrics["coverage_ab"] or 0.0
    conflict = metrics["conflict_rate_ab"] or 1.0
    uniq_b  = metrics["uniq_ratio_b"] or 0.0
    jaccard = metrics["jaccard"] or 0.0

    score = (
        0.40 * coverage +
        0.20 * (1.0 - min(conflict, 1.0)) +
        0.20 * min(uniq_b, 1.0) +
        0.10 * jaccard +
        0.10 * semantic_match
    )
    decision = "reject"
    if coverage >= 0.90 and (conflict <= 0.01) and uniq_b >= 0.95:
        decision = "FK->PK"
    return score, decision

# ---------- Main process ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--region", default=DEFAULT_REGION)
    ap.add_argument("--sample_pct", type=int, default=DEFAULT_SAMPLE_PCT)
    ap.add_argument("--min_score", type=float, default=DEFAULT_MIN_SCORE)
    ap.add_argument("--max_pairs", type=int, default=DEFAULT_MAX_PAIRS)
    args = ap.parse_args()

    bq = bigquery.Client(project=args.project)
    ensure_meta_tables(bq, args.project, args.region)

    # 1) candidate columns (exclude time types)
    cols = fetch_candidate_columns(bq, args.project, args.dataset, args.region)
    # keep only a few data types that make sense to join
    cols = [c for c in cols if c["data_type"] in ("STRING", "INT64", "NUMERIC", "BIGNUMERIC")]

    # 2) build per-column quick profiles + choose first viable normalizer
    col_profiles: Dict[Tuple[str, str], Dict] = {}  # (tbl, col) -> dict
    for c in cols:
        tbl = c["tbl"]
        col = c["column_name"]
        dtype = c["data_type"]
        chosen_norm = None
        nonnull = 0
        approx_u = 0
        for norm in pick_normalizers_for_column(dtype):
            sql = column_profile_sql(f"{args.project}.{args.dataset}.{tbl.split('.')[-1]}", col, norm)
            job = bq.query(
                sql,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("sample_pct", "INT64", args.sample_pct)],
                    maximum_bytes_billed=MAX_BYTES_BILLED,
                ),
            )
            row = list(job.result())[0]
            nonnull = int(row["nonnull"] or 0)
            approx_u = int(row["approx_uniques"] or 0)
            # basic viability: enough evidence, not constant
            if nonnull >= MIN_NONNULL_KEYS and approx_u > 1:
                chosen_norm = norm
                break
        if chosen_norm is None:
            # keep but mark as weak; we may skip as child later
            chosen_norm = pick_normalizers_for_column(dtype)[0]
        col_profiles[(tbl, col)] = {
            "dtype": dtype,
            "norm": chosen_norm,
            "nonnull": nonnull,
            "approx_uniques": approx_u,
        }

    # 3) generate candidate pairs by type/size/semantic compatibility, avoiding O(n^2) explosion
    # heuristic: same dtype or castable, approx_uniques within [0.3x, 3x]
    candidates = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            la = col_profiles[(a["tbl"], a["column_name"])]
            lb = col_profiles[(b["tbl"], b["column_name"])]
            # skip identical table unless you want self-joins
            if a["tbl"] == b["tbl"]:
                continue
            # basic dtype compatibility
            comp = ((a["data_type"] == b["data_type"]) or
                    (a["data_type"] in ("INT64","NUMERIC","BIGNUMERIC") and b["data_type"] in ("INT64","NUMERIC","BIGNUMERIC")) or
                    (a["data_type"] == "STRING" or b["data_type"] == "STRING"))
            if not comp:
                continue
            # domain size proximity if available
            au = la["approx_uniques"] or 0
            bu = lb["approx_uniques"] or 0
            if au and bu:
                ratio = (max(au, bu) / max(1, min(au, bu)))
                if ratio > 3.0:  # too far apart
                    continue
            candidates.append((a, b))

    # limit pairs
    candidates = candidates[: args.max_pairs]

    # 4) test pairs in both directions (A->B). Name/semantic signals are minimal (we’re name-agnostic)
    join_tests_rows = []
    join_map_rows = []
    run_ts = dt.datetime.utcnow().isoformat()

    def fqn(tbl_short: str) -> str:
        # tbl in form 'schema.table' from INFORMATION_SCHEMA; we need project.dataset.table
        _, table = tbl_short.split(".")
        return f"{args.project}.{args.dataset}.{table}"

    for a, b in candidates:
        left_tbl_s, left_col, left_dtype = a["tbl"], a["column_name"], a["data_type"]
        right_tbl_s, right_col, right_dtype = b["tbl"], b["column_name"], b["data_type"]
        left_prof = col_profiles[(left_tbl_s, left_col)]
        right_prof = col_profiles[(right_tbl_s, right_col)]

        # Skip if left evidence too small to test meaningfully
        if left_prof["nonnull"] < MIN_NONNULL_KEYS:
            continue

        left_fqn = fqn(left_tbl_s)
        right_fqn = fqn(right_tbl_s)

        left_norm = left_prof["norm"]
        right_norm = right_prof["norm"]

        sql = pair_test_sql(left_fqn, left_col, left_norm, right_fqn, right_col, right_norm)
        cfg = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("sample_pct", "INT64", args.sample_pct)],
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )

        # dry run for log
        dry_cfg = bigquery.QueryJobConfig(
            query_parameters=cfg.query_parameters,
            dry_run=True,
            maximum_bytes_billed=MAX_BYTES_BILLED,
        )
        dry_job = bq.query(sql, job_config=dry_cfg)
        est_bytes = int(dry_job.total_bytes_processed or 0)

        job = bq.query(sql, job_config=cfg)
        m = dict(list(job.result())[0])

        # minimal signals (name=0.5 if exact match else 0; type 1 if same else 0.5; semantic = 1 if both numeric-or-both-string else 0.5)
        name_signal = 1.0 if left_col.lower() == right_col.lower() else 0.0
        type_signal = 1.0 if left_dtype == right_dtype else 0.5
        semantic_match = 1.0 if ((left_dtype in ("INT64","NUMERIC","BIGNUMERIC") and right_dtype in ("INT64","NUMERIC","BIGNUMERIC")) or
                                 (left_dtype == "STRING" and right_dtype == "STRING")) else 0.5

        score, decision = score_and_decide(m, name_signal, type_signal, semantic_match)

        join_tests_rows.append({
            "run_ts": run_ts,
            "left_table": left_fqn, "left_column": left_col,
            "right_table": right_fqn, "right_column": right_col,
            "left_norm": left_norm, "right_norm": right_norm,
            "a_nonnull": m["a_nonnull"], "a_matched": m["a_matched"],
            "coverage_ab": m["coverage_ab"], "conflict_rate_ab": m["conflict_rate_ab"],
            "uniq_ratio_a": m["uniq_ratio_a"], "uniq_ratio_b": m["uniq_ratio_b"],
            "jaccard": m["jaccard"],
            "name_signal": name_signal, "type_signal": type_signal, "semantic_match": semantic_match,
            "score": score, "decision": decision,
            "bytes_estimated": est_bytes,
            "query_sql": sql,
        })

        if decision != "reject" and score >= args.min_score:
            # Build ready-to-use JOIN snippet
            left_on = norm_expr(f"{left_fqn}.{left_col}", left_norm)
            right_on = norm_expr(f"{right_fqn}.{right_col}", right_norm)
            join_sql = f"LEFT JOIN `{right_fqn}` r ON {left_on} = {right_on}"
            join_map_rows.append({
                "run_ts": run_ts,
                "left_table": left_fqn, "left_column": left_col,
                "right_table": right_fqn, "right_column": right_col,
                "left_norm": left_norm, "right_norm": right_norm,
                "decision": decision, "score": score,
                "join_sql": join_sql,
                "coverage_ab": m["coverage_ab"],
                "conflict_rate_ab": m["conflict_rate_ab"],
                "uniq_ratio_b": m["uniq_ratio_b"],
                "jaccard": m["jaccard"],
            })

    # 5) Write results
    if join_tests_rows:
        bq.insert_rows_json(f"{args.project}.meta.join_tests", join_tests_rows)
    if join_map_rows:
        bq.insert_rows_json(f"{args.project}.meta.join_map", join_map_rows)

    print(f"Tested {len(join_tests_rows)} pairs; accepted {len(join_map_rows)}.")
    print("Results: meta.join_tests, meta.join_map")


if __name__ == "__main__":
    main()
