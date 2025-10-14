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


def run_batch(
    questions_file: Path,
    output_dir: Path,
    index_name: str,
    execute_bq: bool,
    k: int = 4,
    agent_type: str = "create",
    validation_strict: bool = True,
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

    # Prepare JSONL results
    results_jsonl = output_dir / "results.jsonl"
    jsonl_f = results_jsonl.open("a", encoding="utf-8")

    # Process each question
    for i, q in enumerate(questions, start=1):
        logging.info("=" * 80)
        logging.info(f"Q{i}: {q}")
        record: Dict[str, Any] = {
            "index": i,
            "question": q,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        try:
            # Generate answer via RAG pipeline (mirrors app_simple_gemini)
            result = answer_question_simple_gemini(
                question=q,
                vector_store=vector_store,
                k=k,
                gemini_mode=True,
                hybrid_search=True,
                query_rewriting=True,
                schema_manager=schema_manager,
                lookml_safe_join_map=lookml_map,
                conversation_context=None,
                agent_type=agent_type,
                sql_validation=True,
                validation_level=(ValidationLevel.SCHEMA_STRICT if validation_strict else ValidationLevel.SCHEMA_BASIC),
            )

            if not result:
                logging.error("Pipeline returned no result (see qNNN_debug.md for details)")
                copy_debug_log(output_dir, i)
                continue

            ans, sources, token_usage = result

            record["token_usage"] = token_usage or {}
            record["sources"] = [getattr(d, "metadata", {}) for d in (sources or [])]

            # Save raw answer
            save_artifact(ans or "", output_dir / f"q{i:03d}_answer.txt")
            logging.info(f"Answer length: {len(ans or '')}")

            # Copy detailed pipeline debug log for this question
            copy_debug_log(output_dir, i)

            # Extract SQL
            extracted_sql = extract_sql_from_answer_text(ans or "") if ans else None
            if extracted_sql:
                save_artifact(extracted_sql, output_dir / f"q{i:03d}_query.sql")
                record["sql"] = extracted_sql
                logging.info("Extracted SQL found and saved")
            else:
                logging.info("No SQL extracted from answer")
                record["sql"] = None

            # Execute SQL if requested and available
            if execute_bq and executor and extracted_sql:
                logging.info("Executing extracted SQL on BigQuery...")
                result = executor.execute_query(extracted_sql)
                record["execution"] = {
                    "success": result.success,
                    "error_message": result.error_message,
                    "execution_time": result.execution_time,
                    "bytes_processed": result.bytes_processed,
                    "bytes_billed": result.bytes_billed,
                    "total_rows": result.total_rows,
                    "job_id": result.job_id,
                    "cache_hit": result.cache_hit,
                }
                if result.success and result.data is not None:
                    out_csv = output_dir / f"q{i:03d}_result.csv"
                    try:
                        result.data.to_csv(out_csv, index=False)
                        logging.info(f"Saved result CSV: {out_csv} ({len(result.data)} rows)")
                    except Exception as e:
                        logging.warning(f"Failed to write result CSV: {e}")
                elif not result.success:
                    logging.warning(f"BigQuery execution failed: {result.error_message}")
            else:
                if not execute_bq:
                    logging.info("Execution disabled (--no-execute)")
                elif not executor:
                    logging.info("BigQuery executor unavailable")
                elif not extracted_sql:
                    logging.info("No SQL to execute")

        except Exception as e:
            logging.exception(f"Failed to process question {i}: {e}")
            record["error"] = str(e)

        # Persist JSONL record (one per question)
        try:
            jsonl_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            jsonl_f.flush()
        except Exception:
            pass

    jsonl_f.close()
    logging.info("Batch run completed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch Query Runner for Simple SQL RAG")
    parser.add_argument("--questions-file", required=True, type=Path, help="Path to text file with one question per line")
    parser.add_argument("--output-dir", default=Path("logs") / ("batch_" + datetime.now().strftime("%Y%m%d_%H%M%S")), type=Path, help="Directory to write logs and outputs")
    parser.add_argument("--index-name", default=DEFAULT_INDEX_NAME, help="Name of FAISS index directory in faiss_indices/")
    parser.add_argument("--k", type=int, default=4, help="Number of documents to retrieve")
    parser.add_argument("--agent-type", choices=["create", "explain", "default"], default="create", help="Agent mode for prompting")
    parser.add_argument("--no-execute", action="store_true", help="Do not execute BigQuery SQL")
    parser.add_argument("--basic-validation", action="store_true", help="Use basic schema validation instead of strict")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_batch(
        questions_file=args.questions_file,
        output_dir=args.output_dir,
        index_name=args.index_name,
        execute_bq=not args.no_execute,
        k=args.k,
        agent_type="create" if args.agent_type == "default" else args.agent_type,
        validation_strict=not args.basic_validation,
    )
