#!/usr/bin/env python3
"""
Batch Query Runner for Simple SQL RAG (Gemini)

Reads a list of natural language questions from a text file and, for each:
- Runs the same retrieval + schema injection + LLM generation flow used by app_simple_gemini.py
- Logs all steps and artifacts (prompting context, schema use, token usage)
- Extracts generated SQL from the answer, executes it on BigQuery, and logs results

Usage:
  python scripts/run_batch_questions.py \
    --questions-file questions.txt \
    --output-dir logs/batch_run \
    --index-name index_transformed_sample_queries \
    [--no-execute]

Notes:
- Requires GEMINI_API_KEY (or GOOGLE_API_KEY) for Gemini
- Uses ADC for BigQuery on Cloud Run. Locally, set GOOGLE_APPLICATION_CREDENTIALS or run `gcloud auth application-default login`.
- BIGQUERY_PROJECT_ID and BIGQUERY_DATASET can override defaults.
"""

import argparse
import logging
import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Repo-local imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from langchain_community.vectorstores import FAISS

# RAG pipeline and helpers
from simple_rag_simple_gemini import answer_question_simple_gemini
from utils.embedding_provider import get_embedding_function
from core.bigquery_executor import BigQueryExecutor
from schema_manager import create_schema_manager
from core.sql_validator import ValidationLevel

# Constants consistent with app_simple_gemini.py
FAISS_INDICES_DIR = REPO_ROOT / "faiss_indices"
DEFAULT_INDEX_NAME = "index_transformed_sample_queries"
SCHEMA_CSV_PATH = REPO_ROOT / "data_new/thelook_ecommerce_schema.csv"
LOOKML_SAFE_JOIN_MAP_PATH = FAISS_INDICES_DIR / "lookml_safe_join_map.json"


def setup_logging(output_dir: Path) -> Path:
    """Configure logging to console and a file under output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8")
        ],
    )
    return log_path


def _list_available_indices() -> List[str]:
    if not FAISS_INDICES_DIR.exists():
        return []
    return sorted([p.name for p in FAISS_INDICES_DIR.iterdir() if p.is_dir() and p.name.startswith("index_")])


def load_vector_store(index_name: str) -> Optional[FAISS]:
    """Load FAISS vector store with configured embeddings (safe fallback)."""
    index_path = FAISS_INDICES_DIR / index_name
    if not index_path.exists():
        logging.error(f"Vector store not found at: {index_path}")
        choices = _list_available_indices()
        if choices:
            logging.info(f"Available indices under {FAISS_INDICES_DIR}: {choices}")
            if len(choices) == 1:
                logging.info(f"Auto-selecting the only available index: {choices[0]}")
                return load_vector_store(choices[0])
        logging.info("Run: python standalone_embedding_generator.py --csv 'sample_queries_with_metadata.csv'")
        return None

    try:
        embeddings = get_embedding_function()
        allow_dangerous = os.getenv("FAISS_SAFE_DESERIALIZATION", "0").lower() not in ("1", "true", "yes")
        vector_store = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=allow_dangerous
        )
        logging.info(f"Loaded vector store: {index_path}")
        return vector_store
    except Exception as e:
        logging.exception(f"Failed to load vector store from {index_path}: {e}")
        return None


def load_lookml_safe_join_map() -> Optional[Dict[str, Any]]:
    if LOOKML_SAFE_JOIN_MAP_PATH.exists():
        try:
            with open(LOOKML_SAFE_JOIN_MAP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load LookML safe join map: {e}")
    return None


def read_questions(path: Path) -> List[str]:
    questions: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            questions.append(line)
    return questions


def extract_sql_from_answer_text(text: str) -> Optional[str]:
    """Extract SQL code block from LLM answer text (no BigQuery client needed)."""
    import re
    if not text:
        return None
    sql_patterns = [
        r"```sql\s*\n(.*?)\n\s*```",  # SQL code blocks
        r"```\s*\n(.*?)\n\s*```",     # Generic code blocks
    ]
    for pattern in sql_patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            sql = matches[0].strip()
            sql_upper = sql.upper()
            if (sql_upper.startswith(("SELECT", "WITH")) and 
                ("FROM" in sql_upper or "AS" in sql_upper)):
                return sql
    return None


def save_artifact(text: str, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def copy_debug_log(output_dir: Path, index: int):
    # answer_question_simple_gemini writes to debug_logs.md in CWD
    debug_src = REPO_ROOT / "debug_logs.md"
    if debug_src.exists():
        dest = output_dir / f"q{index:03d}_debug.md"
        try:
            shutil.copy(debug_src, dest)
            logging.info(f"Saved debug log: {dest}")
        except Exception as e:
            logging.warning(f"Failed to copy debug log: {e}")


VARIANTS = [
    "current",       # schema injection + sql validation
    "no_schema",     # no schema injection, yes validation (manual post-validate)
    "schema_only",   # schema injection only, no validation
    "minimal",       # no schema injection, no validation
]


def run_batch(
    questions_file: Path,
    output_dir: Path,
    index_name: str,
    execute_bq: bool,
    k: int = 4,
    agent_type: str = "create",
    validation_strict: bool = True,
    variants: Optional[List[str]] = None,
):
    # Setup
    log_path = setup_logging(output_dir)
    logging.info(f"Batch run started. Log: {log_path}")
    logging.info(f"Questions file: {questions_file}")
    logging.info(f"Output dir: {output_dir}")
    logging.info(f"Index: {index_name}")

    vector_store = load_vector_store(index_name)
    if not vector_store:
        logging.error("Cannot continue without vector store")
        sys.exit(1)

    # Schema manager (optional but recommended for validation and schema injection)
    schema_manager = None
    if SCHEMA_CSV_PATH.exists():
        schema_manager = create_schema_manager(str(SCHEMA_CSV_PATH), verbose=False)
        if schema_manager:
            logging.info(
                f"Schema manager ready: {schema_manager.table_count} tables, {schema_manager.column_count} columns"
            )
    else:
        logging.warning(f"Schema CSV not found at {SCHEMA_CSV_PATH}; proceeding without schema injection/validation")

    lookml_map = load_lookml_safe_join_map()
    if lookml_map:
        logging.info("Loaded LookML safe-join map")

    # BigQuery executor (can be skipped with --no-execute)
    executor = None
    if execute_bq:
        bq_project = os.getenv("BIGQUERY_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "brainrot-453319"
        bq_dataset = os.getenv("BIGQUERY_DATASET") or "bigquery-public-data.thelook_ecommerce"
        try:
            executor = BigQueryExecutor(project_id=bq_project, dataset_id=bq_dataset)
            logging.info(f"BigQuery executor ready (project={bq_project}, dataset={bq_dataset})")
        except Exception as e:
            logging.error(f"Failed to initialize BigQuery executor: {e}")
            execute_bq = False

    # Read questions
    questions = read_questions(questions_file)
    if not questions:
        logging.error("No questions to process")
        return

    # Select variants
    run_variants = variants or ["current"]
    for v in run_variants:
        if v not in VARIANTS:
            logging.warning(f"Unknown variant '{v}'. Skipping.")
    run_variants = [v for v in run_variants if v in VARIANTS]
    if not run_variants:
        logging.error("No valid variants selected. Use --variants current no_schema schema_only minimal or --variants all")
        return

    # Process each question
    for i, q in enumerate(questions, start=1):
        logging.info("=" * 80)
        logging.info(f"Q{i}: {q}")
        for variant in run_variants:
            v_out = output_dir / variant
            v_out.mkdir(parents=True, exist_ok=True)
            results_jsonl = v_out / "results.jsonl"
            with results_jsonl.open("a", encoding="utf-8") as jsonl_f:
                record: Dict[str, Any] = {
                    "index": i,
                    "question": q,
                    "variant": variant,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                try:
                    t0 = datetime.utcnow().timestamp()
                    # Configure schema injection and validation per variant
                    if variant == "current":
                        use_schema_injection = True
                        do_validation_inside = True
                        manual_validation = False
                    elif variant == "no_schema":
                        use_schema_injection = False
                        do_validation_inside = False
                        manual_validation = True  # validate after generation using SchemaManager
                    elif variant == "schema_only":
                        use_schema_injection = True
                        do_validation_inside = False
                        manual_validation = False
                    elif variant == "minimal":
                        use_schema_injection = False
                        do_validation_inside = False
                        manual_validation = False
                    else:
                        use_schema_injection = True
                        do_validation_inside = True
                        manual_validation = False

                    # Run generation with configured schema injection and in-function validation
                    result = answer_question_simple_gemini(
                        question=q,
                        vector_store=vector_store,
                        k=k,
                        gemini_mode=True,
                        hybrid_search=True,
                        query_rewriting=True,
                        schema_manager=(schema_manager if use_schema_injection else None),
                        lookml_safe_join_map=lookml_map,
                        conversation_context=None,
                        agent_type=agent_type,
                        sql_validation=do_validation_inside,
                        validation_level=(ValidationLevel.SCHEMA_STRICT if validation_strict else ValidationLevel.SCHEMA_BASIC),
                    )

                    if not result:
                        logging.error(f"[{variant}] Pipeline returned no result (see debug) ")
                        copy_debug_log(v_out, i)
                        record["error"] = "no_result"
                        jsonl_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        jsonl_f.flush()
                        continue

                    ans, sources, token_usage = result
                    t1 = datetime.utcnow().timestamp()
                    # Timings
                    timings: Dict[str, Any] = {}
                    timings["pipeline_seconds"] = round(t1 - t0, 3)
                    if token_usage:
                        if "retrieval_time" in token_usage:
                            timings["retrieval_seconds"] = round(float(token_usage.get("retrieval_time", 0.0)), 3)
                        if "generation_time" in token_usage:
                            timings["generation_seconds"] = round(float(token_usage.get("generation_time", 0.0)), 3)
                        sv = token_usage.get("sql_validation") or {}
                        if sv.get("enabled") and "validation_time" in sv:
                            try:
                                timings["validation_seconds"] = round(float(sv.get("validation_time", 0.0)), 3)
                            except Exception:
                                pass
                    record["timings"] = timings
                    record["token_usage"] = token_usage or {}
                    record["sources"] = [getattr(d, "metadata", {}) for d in (sources or [])]

                    # Save raw answer
                    save_artifact(ans or "", v_out / f"q{i:03d}_answer.txt")
                    logging.info(f"[{variant}] Answer length: {len(ans or '')}")

                    # Copy detailed pipeline debug log for this question
                    # Save with variant suffix
                    debug_src = Path("debug_logs.md")
                    if debug_src.exists():
                        try:
                            dest = v_out / f"q{i:03d}_debug.md"
                            import shutil
                            shutil.copy(debug_src, dest)
                        except Exception:
                            pass

                    # Extract SQL
                    extracted_sql = extract_sql_from_answer_text(ans or "") if ans else None
                    if extracted_sql:
                        save_artifact(extracted_sql, v_out / f"q{i:03d}_query.sql")
                        record["sql"] = extracted_sql
                        logging.info(f"[{variant}] Extracted SQL found and saved")
                    else:
                        logging.info(f"[{variant}] No SQL extracted from answer")
                        record["sql"] = None

                    # Manual validation path for no_schema variant
                    if manual_validation and extracted_sql:
                        try:
                            from core.sql_validator import validate_sql_query, ValidationLevel as VLevel
                            vres = validate_sql_query(
                                extracted_sql,
                                schema_manager=schema_manager,
                                validation_level=(VLevel.SCHEMA_STRICT if validation_strict else VLevel.SCHEMA_BASIC),
                            )
                            record["validation"] = {
                                "is_valid": vres.is_valid,
                                "errors": vres.errors,
                                "warnings": vres.warnings,
                                "tables_found": list(vres.tables_found),
                                "columns_found": list(vres.columns_found),
                            }
                            logging.info(f"[{variant}] Manual validation: valid={vres.is_valid}, errors={len(vres.errors)}")
                        except Exception as e:
                            logging.warning(f"[{variant}] Manual validation failed: {e}")

                    # Execute SQL if requested and available
                    if execute_bq and executor and extracted_sql:
                        logging.info(f"[{variant}] Executing extracted SQL on BigQuery...")
                        xres = executor.execute_query(extracted_sql)
                        record["execution"] = {
                            "success": xres.success,
                            "error_message": xres.error_message,
                            "execution_time": xres.execution_time,
                            "bytes_processed": xres.bytes_processed,
                            "bytes_billed": xres.bytes_billed,
                            "total_rows": xres.total_rows,
                            "job_id": xres.job_id,
                            "cache_hit": xres.cache_hit,
                        }
                        if xres.success and xres.data is not None:
                            out_csv = v_out / f"q{i:03d}_result.csv"
                            try:
                                xres.data.to_csv(out_csv, index=False)
                                logging.info(f"[{variant}] Saved result CSV: {out_csv} ({len(xres.data)} rows)")
                            except Exception as e:
                                logging.warning(f"[{variant}] Failed to write result CSV: {e}")
                        elif not xres.success:
                            logging.warning(f"[{variant}] BigQuery execution failed: {xres.error_message}")
                    else:
                        if not execute_bq:
                            logging.info(f"[{variant}] Execution disabled (--no-execute)")
                        elif not executor:
                            logging.info(f"[{variant}] BigQuery executor unavailable")
                        elif not extracted_sql:
                            logging.info(f"[{variant}] No SQL to execute")

                except Exception as e:
                    logging.exception(f"[{variant}] Failed to process question {i}: {e}")
                    record["error"] = str(e)
                finally:
                    try:
                        jsonl_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        jsonl_f.flush()
                    except Exception:
                        pass
    logging.info("Batch run completed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch Query Runner for Simple SQL RAG")
    parser.add_argument("--questions-file", required=True, type=Path, help="Path to text file with one question per line")
    parser.add_argument("--output-dir", default=Path("logs") / ("batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")), type=Path, help="Directory to write logs and outputs")
    parser.add_argument("--index-name", default=DEFAULT_INDEX_NAME, help="Name of FAISS index directory in faiss_indices/")
    parser.add_argument("--k", type=int, default=4, help="Number of documents to retrieve")
    parser.add_argument("--agent-type", choices=["create", "explain", "default"], default="create", help="Agent mode for prompting")
    parser.add_argument("--no-execute", action="store_true", help="Do not execute BigQuery SQL")
    parser.add_argument(
        "--variants",
        nargs="+",
        default=["current"],
        help="Pipeline variants to run per question: current no_schema schema_only minimal, or 'all'"
    )
    parser.add_argument("--basic-validation", action="store_true", help="Use basic schema validation instead of strict")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # Expand 'all' into the full set
    variants = args.variants
    if any(v.lower() == "all" for v in variants):
        variants = VARIANTS

    run_batch(
        questions_file=args.questions_file,
        output_dir=args.output_dir,
        index_name=args.index_name,
        execute_bq=not args.no_execute,
        k=args.k,
        agent_type="create" if args.agent_type == "default" else args.agent_type,
        validation_strict=not args.basic_validation,
        variants=variants,
    )
