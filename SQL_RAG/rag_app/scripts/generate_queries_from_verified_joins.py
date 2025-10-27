#!/usr/bin/env python3
"""
Generate SQL queries from verified joins using the configured LLM.

The script reads:
  • Verified joins from sql_improvement/join_validation_results.csv
  • Table/column metadata from data_new/thelook_ecommerce_schema.csv
  • Existing queries from data_new/sample_queries_with_metadata_recovered.csv

It then crafts a structured prompt for the generation LLM (via llm_registry)
and requests new BigQuery SQL statements with descriptive metadata. Any newly
generated queries are appended to the output CSV (defaulting to the recovered
sample queries file) with duplicate SQL removed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from llm_registry import get_llm_registry

# Limits to keep prompts concise
DEFAULT_MAX_COLUMNS_PER_TABLE = 12
DEFAULT_MAX_EXISTING_EXAMPLES = 5


def load_verified_joins(path: Path) -> pd.DataFrame:
    """Return only successful join validations."""
    df = pd.read_csv(path)
    if "validation_status" not in df.columns:
        raise ValueError(f"'validation_status' column missing in {path}")
    verified = df[df["validation_status"].astype(str).str.lower() == "success"]
    if verified.empty:
        raise ValueError(f"No verified joins found in {path}")
    return verified


def load_schema(path: Path, tables: List[str]) -> pd.DataFrame:
    """Filter schema metadata to tables of interest."""
    schema_df = pd.read_csv(path)
    if not {"table", "column", "column_data_type"}.issubset(schema_df.columns):
        raise ValueError(
            "Schema CSV must contain 'table', 'column', and 'column_data_type' columns"
        )
    schema_filtered = schema_df[schema_df["table"].isin(tables)].copy()
    if schema_filtered.empty:
        raise ValueError(
            "Schema filter produced no rows. Double-check table names in join CSV."
        )
    return schema_filtered


def format_schema_section(
    schema_df: pd.DataFrame, max_columns: int
) -> str:
    """Return a human-readable schema summary for the prompt."""
    lines: List[str] = []
    for table, group in schema_df.groupby("table"):
        trimmed = group.head(max_columns)
        col_desc = ", ".join(
            f"{row.column} ({row.column_data_type})" for row in trimmed.itertuples()
        )
        if len(group) > max_columns:
            remaining = len(group) - max_columns
            col_desc += f", … (+{remaining} more)"
        lines.append(f"- {table}: {col_desc}")
    return "\n".join(lines)


def format_join_section(verified_df: pd.DataFrame) -> str:
    """Return bullet list of joins with cardinality notes."""
    lines: List[str] = []
    for row in verified_df.itertuples():
        cardinality = getattr(row, "cardinality_type", "") or "unspecified"
        notes = getattr(row, "notes", "")
        note_text = f" | notes: {notes}" if notes else ""
        lines.append(
            f"- {row.left_table}.{row.left_col} = "
            f"{row.right_table}.{row.right_col} "
            f"(cardinality: {cardinality}{note_text})"
        )
    return "\n".join(lines)


def sample_existing_queries(
    df: pd.DataFrame, limit: int
) -> List[Dict[str, Any]]:
    """Return lightweight examples to avoid duplicate generations."""
    if df.empty:
        return []
    sample_rows = df.head(limit)
    examples: List[Dict[str, Any]] = []
    for row in sample_rows.itertuples():
        examples.append(
            {
                "query": row.query,
                "description": getattr(row, "description", ""),
                "tables": row.tables,
            }
        )
    return examples


def build_prompt(
    schema_section: str,
    join_section: str,
    examples: List[Dict[str, Any]],
    num_queries: int,
) -> str:
    """Compose the instruction sent to the LLM."""
    example_text = json.dumps(examples, indent=2) if examples else "[]"
    return f"""
You are a BigQuery SQL generation expert. Craft {num_queries} new analytical SQL
queries for the `bigquery-public-data.thelook_ecommerce` dataset.

Goals:
- Each query must include accurate joins that align with the verified join pairs below.
- Diversify business topics (sales, user engagement, logistics, marketing, etc.).
- Produce SELECT statements that will run under BigQuery Standard SQL.
- Return only working SQL; avoid placeholders or comments.

Dataset schema (table: columns):
{schema_section}

Verified joins (use these when joining tables):
{join_section}

Existing query examples (avoid duplicating them):
{example_text}

Return a JSON array with {num_queries} objects. Each object must include:
{{
  "query": "<fully qualified BigQuery SQL>",
  "description": "<1-2 sentence explanation>",
  "tables": ["project.dataset.table", ...],
  "joins": [
    {{
      "left_table": "project.dataset.table",
      "left_column": "column_name",
      "right_table": "project.dataset.table",
      "right_column": "column_name",
      "join_type": "INNER|LEFT|RIGHT|FULL"
    }}
  ]
}}

Output only the JSON array. Do not wrap it in backticks or prose.
""".strip()


def extract_json(response_text: str) -> List[Dict[str, Any]]:
    """Parse the LLM response, tolerating accidental markdown fences."""
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if "```" in cleaned else cleaned
    cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse LLM response as JSON: {exc}\nResponse:\n{cleaned}") from exc
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array from LLM response.")
    return parsed


def normalise_join_records(joins: List[Dict[str, Any]]) -> str:
    """Convert join metadata to a JSON string with consistent ordering."""
    if not joins:
        return "[]"
    normalised = []
    for item in joins:
        normalised.append(
            {
                "left_table": item.get("left_table", ""),
                "left_column": item.get("left_column", ""),
                "right_table": item.get("right_table", ""),
                "right_column": item.get("right_column", ""),
                "join_type": item.get("join_type", ""),
            }
        )
    return json.dumps(normalised, ensure_ascii=False)


def normalise_table_list(tables: Any) -> str:
    """Ensure table metadata is stored as a JSON array string."""
    if isinstance(tables, str):
        try:
            loaded = json.loads(tables)
            if isinstance(loaded, list):
                return json.dumps(loaded, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        return json.dumps([tables], ensure_ascii=False)
    if isinstance(tables, list):
        return json.dumps(tables, ensure_ascii=False)
    return "[]"


def append_new_queries(
    existing_df: pd.DataFrame,
    generations: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Merge new items into the existing dataset without duplicate SQL."""
    existing_queries = set(existing_df["query"].tolist())
    new_rows: List[Dict[str, Any]] = []

    for item in generations:
        query_text = item.get("query", "").strip()
        if not query_text:
            continue
        if query_text in existing_queries:
            continue

        new_rows.append(
            {
                "query": query_text,
                "description": item.get("description", "").strip(),
                "tables": normalise_table_list(item.get("tables", [])),
                "joins": normalise_join_records(item.get("joins", [])),
            }
        )
        existing_queries.add(query_text)

    if not new_rows:
        return existing_df

    new_df = pd.DataFrame(new_rows)
    return pd.concat([existing_df, new_df], ignore_index=True)


def run_generation(args: argparse.Namespace) -> None:
    """Orchestrate data loading, prompt creation, LLM invocation, and persistence."""
    join_csv = Path(args.join_csv)
    schema_csv = Path(args.schema_csv)
    existing_csv = Path(args.existing_csv)
    output_csv = Path(args.output_csv)

    verified = load_verified_joins(join_csv)
    tables_in_scope = sorted(
        set(verified["left_table"].tolist() + verified["right_table"].tolist())
    )
    schema_df = load_schema(schema_csv, tables_in_scope)
    schema_section = format_schema_section(
        schema_df, args.max_columns_per_table
    )
    join_section = format_join_section(verified)

    existing_df = pd.read_csv(existing_csv)
    examples = sample_existing_queries(existing_df, args.sample_existing)

    prompt = build_prompt(
        schema_section=schema_section,
        join_section=join_section,
        examples=examples,
        num_queries=args.num_queries,
    )

    if args.dry_run:
        print(prompt)
        return

    generator = get_llm_registry().get_generator()
    response_text = generator.invoke(prompt)
    generations = extract_json(response_text)
    updated_df = append_new_queries(existing_df, generations)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    updated_df.to_csv(output_csv, index=False)
    print(
        f"✅ Added {len(updated_df) - len(existing_df)} new queries. "
        f"Dataset now contains {len(updated_df)} rows.\nSaved to {output_csv}"
    )


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SQL queries using verified joins and schema metadata."
    )
    parser.add_argument(
        "--join-csv",
        default="sql_improvement/join_validation_results.csv",
        help="CSV with verified joins (default: %(default)s)",
    )
    parser.add_argument(
        "--schema-csv",
        default="data_new/thelook_ecommerce_schema.csv",
        help="CSV containing table/column metadata (default: %(default)s)",
    )
    parser.add_argument(
        "--existing-csv",
        default="data_new/sample_queries_with_metadata_recovered.csv",
        help="Existing dataset to augment (default: %(default)s)",
    )
    parser.add_argument(
        "--output-csv",
        default="data_new/sample_queries_with_metadata_recovered.csv",
        help="Where to write the augmented dataset (default: %(default)s)",
    )
    parser.add_argument(
        "--num-queries",
        type=int,
        default=5,
        help="Number of new SQL queries to request from the LLM (default: %(default)s)",
    )
    parser.add_argument(
        "--max-columns-per-table",
        type=int,
        default=DEFAULT_MAX_COLUMNS_PER_TABLE,
        help="Limit of columns per table to include in the schema prompt section "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--sample-existing",
        type=int,
        default=DEFAULT_MAX_EXISTING_EXAMPLES,
        help="How many existing queries to expose as examples so the LLM avoids duplicates "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated prompt instead of calling the LLM.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    run_generation(args)


if __name__ == "__main__":
    main()
