import asyncio
import logging
import argparse
import json
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd
from google import genai
from google.cloud import bigquery
from dotenv import load_dotenv
from utils.rate_limiter import GEMINI_RATE_LIMITER, exponential_backoff_retry
from utils.progress_tracker import ProgressTracker

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

host_table_name = os.getenv("host_table")


def _resolve_default_model() -> str:
    """Determine which Gemini model to use for metadata generation."""
    return (
        os.getenv("DESCRIPTION_GENERATOR_MODEL")
        or os.getenv("GEMINI_DESCRIPTION_MODEL")
        or os.getenv("LLM_CHAT_MODEL")
        or "gemini-2.5-flash"
    )


MODEL_NAME = _resolve_default_model()

_GENAI_CLIENT: Optional[genai.Client] = None


def _infer_client_mode() -> str:
    """Infer whether to use Vertex AI SDK or public API key auth."""
    raw_mode = os.getenv("GENAI_CLIENT_MODE")
    if not raw_mode:
        vertexai_override = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
        if vertexai_override is not None:
            default_mode = "sdk" if vertexai_override.lower() in ("true", "1", "yes") else "api"
        elif os.getenv("GOOGLE_CLOUD_PROJECT") and not (
            os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        ):
            default_mode = "sdk"
        else:
            default_mode = "api"
        raw_mode = default_mode
    mode = raw_mode.strip().lower()
    if mode not in {"api", "sdk"}:
        raise ValueError("GENAI_CLIENT_MODE must be 'api' or 'sdk'")
    return mode


def get_genai_client() -> genai.Client:
    """Return a configured Google GenAI client honoring SDK/API settings."""
    global _GENAI_CLIENT
    if _GENAI_CLIENT is not None:
        return _GENAI_CLIENT

    client_mode = _infer_client_mode()
    if client_mode == "sdk":
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is required when using GENAI_CLIENT_MODE=sdk. "
                "Set GENAI_CLIENT_MODE=api to authenticate with an API key instead."
            )
        location = (
            os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("GOOGLE_CLOUD_REGION")
            or "global"
        )
        _GENAI_CLIENT = genai.Client(vertexai=True, project=project, location=location)
    else:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) must be set when GENAI_CLIENT_MODE=api."
            )
        _GENAI_CLIENT = genai.Client(api_key=api_key)
    return _GENAI_CLIENT


# Update your generate_sql_metadata function's prompt to request more detailed join information
@exponential_backoff_retry(max_retries=3, base_delay=2.0)
async def generate_sql_metadata(query_text, index=None, total=None, return_tokens=False):
    """Generate metadata for a SQL query including description, tables, and joins."""
    if index is not None and total is not None:
        print(f"Processing query {index + 1}/{total}...")
    
    # Wait for rate limiter before making request
    estimated_tokens = len(query_text.split()) * 2  # Rough estimate
    if not await GEMINI_RATE_LIMITER.wait_for_availability(estimated_tokens, max_wait=300):
        raise Exception("Rate limiter timeout - could not get availability within 5 minutes")
    prompt = (
        "You are a SQL analyst. Analyze this SQL query and provide the following information in JSON format:\n"
        "1. description: 1-2 clear sentences about what the query does\n"
        "2. tables: Array of all fully qualified table names (in format project.dataset.table)\n"
        "3. joins: Array of objects with the following structure:\n"
        "   {\n"
        "     \"left_table\": \"fully_qualified_table_name\",\n"
        "     \"left_column\": \"column_name\",\n"
        "     \"right_table\": \"fully_qualified_table_name\",\n"
        "     \"right_column\": \"column_name\",\n"
        "     \"join_type\": \"JOIN type (INNER, LEFT, etc.)\"\n"
        "   }\n\n"
        "Return ONLY a JSON object with these three fields. Tables typically start with 'wmt'.\n\n"
        f"SQL Query:\n{query_text}"
    )
    try:
        client = get_genai_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=prompt,
        )
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", estimated_tokens) if usage else estimated_tokens
        completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        total_tokens = getattr(usage, "total_token_count", prompt_tokens + completion_tokens)

        # Record successful request with rate limiter
        GEMINI_RATE_LIMITER.record_request(total_tokens)
        result_text = getattr(response, "text", "")
        if not result_text:
            raise ValueError("Empty response from Gemini model")
        result = result_text.strip()
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
        if index is not None:
            print(f"Completed query {index + 1} (tokens: {token_usage['total_tokens']})")
        try:
            # First, strip any markdown formatting if present (```json...```)
            json_str = result
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            
            # Parse the JSON
            parsed_result = json.loads(json_str)
            
            # Extract and properly format for CSV
            description = parsed_result.get("description", "")
            tables = json.dumps(parsed_result.get("tables", []))  # Convert lists to JSON strings
            joins = json.dumps(parsed_result.get("joins", []))
            
            if return_tokens:
                return description, tables, joins, token_usage
            return description, tables, joins
        except json.JSONDecodeError:
            print(f"JSON parsing error for result: {result}")
            if return_tokens:
                return "Error parsing result", [], [], token_usage
            return "Error parsing result", [], []
    except Exception as e:
        error_str = str(e).lower()
        
        # Handle rate limit errors specifically
        if "429" in error_str or "resource exhausted" in error_str or "quota" in error_str:
            GEMINI_RATE_LIMITER.record_rate_limit_violation()
            raise e  # Let retry decorator handle this
        else:
            GEMINI_RATE_LIMITER.record_error(e)
        
        if index is not None:
            print(f"Error on query {index + 1}: {str(e)}")
        error_msg = f"Error generating metadata: {str(e)}"
        if return_tokens:
            return error_msg, [], [], {"error": str(e)}
        return error_msg, [], []

async def generate_metadata_async(query_text, index=None, total=None, return_tokens=False):
    """Async wrapper for generate_sql_metadata - now calls async function directly."""
    return await generate_sql_metadata(query_text, index, total, return_tokens)

async def generate_metadata_parallel(
    query_items: List[Tuple[int, str]],
    max_concurrent: Optional[int] = None,
    return_tokens: bool = False,
    progress_tracker: Optional[ProgressTracker] = None,
):
    """
    Generate metadata for multiple SQL queries in parallel with rate limiting.
    
    Args:
        query_items: List of (original_index, query_text) tuples.
        max_concurrent: Maximum number of in-flight LLM calls.
        return_tokens: Whether to include token accounting in the response.
        progress_tracker: Optional tracker to persist progress across runs.
    """
    total = len(query_items)
    if total == 0:
        empty_df = pd.DataFrame(columns=["query", "description", "tables", "joins"])
        if return_tokens:
            empty_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            return empty_df, empty_usage, []
        return empty_df

    if max_concurrent is None:
        max_concurrent = int(os.getenv("GENAI_MAX_CONCURRENT", "6"))
    max_concurrent = max(1, max_concurrent)
    if GEMINI_RATE_LIMITER.requests_per_minute:
        max_concurrent = min(max_concurrent, GEMINI_RATE_LIMITER.requests_per_minute)
    GEMINI_RATE_LIMITER.max_concurrency = max_concurrent
    GEMINI_RATE_LIMITER.current_concurrency = max_concurrent

    # Ensure the daily quota is not the bottleneck for large batches
    desired_rpd = int(os.getenv("GENAI_REQUESTS_PER_DAY", str(total + 100)))
    GEMINI_RATE_LIMITER.requests_per_day = max(GEMINI_RATE_LIMITER.requests_per_day, desired_rpd)

    print(f"Processing {total} queries with up to {max_concurrent} concurrent requests...")

    results: list[Dict[str, Any]] = []

    # Initialize progress tracking
    if progress_tracker:
        remaining_items = progress_tracker.initialize(query_items)
    else:
        remaining_items = query_items

    if not remaining_items:
        print("All queries already processed according to checkpoint!")
        stored_results = progress_tracker.get_results() if progress_tracker else []
        df = pd.DataFrame(stored_results)
        if return_tokens:
            usage_summary = {
                "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in stored_results),
                "completion_tokens": sum(r.get("completion_tokens", 0) for r in stored_results),
                "total_tokens": sum(r.get("total_tokens", 0) for r in stored_results),
            }
            return df, usage_summary, stored_results
        return df

    print(f"Processing {len(remaining_items)} remaining queries after checkpoint resume...")

    batch_number = 1
    start = 0
    while start < len(remaining_items):
        current_concurrency = min(max_concurrent, GEMINI_RATE_LIMITER.get_current_concurrency())
        if current_concurrency < 1:
            current_concurrency = 1
        batch = remaining_items[start:start + current_concurrency]

        print(f"\nProcessing batch {batch_number}: {len(batch)} queries")
        print(f"Current concurrency: {current_concurrency}")
        stats = GEMINI_RATE_LIMITER.get_stats()
        print(
            f"Rate limiter stats - RPM: {stats['requests_last_minute']}/"
            f"{GEMINI_RATE_LIMITER.requests_per_minute}, "
            f"Success rate: {stats['success_rate']:.1f}%"
        )

        if progress_tracker:
            progress_tracker.print_progress()

        batch_tasks = [
            generate_metadata_async(query_text, original_index, total, return_tokens)
            for original_index, query_text in batch
        ]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        for idx, result in enumerate(batch_results):
            original_index, query_text = batch[idx]
            if isinstance(result, Exception):
                error_msg = f"Error processing query: {str(result)}"
                print(f"Failed query (index {original_index}): {error_msg}")

                payload = {
                    "query_index": original_index,
                    "query": query_text,
                    "description": error_msg,
                    "tables": "[]",
                    "joins": "[]",
                }
                if return_tokens:
                    payload.update({
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    })

                results.append(payload)
                if progress_tracker:
                    progress_tracker.record_failure((original_index, query_text), error_msg)
            else:
                if return_tokens:
                    desc, tables, joins, token_data = result
                    payload = {
                        "query_index": original_index,
                        "query": query_text,
                        "description": desc,
                        "tables": tables,
                        "joins": joins,
                        "prompt_tokens": token_data.get("prompt_tokens", 0),
                        "completion_tokens": token_data.get("completion_tokens", 0),
                        "total_tokens": token_data.get("total_tokens", 0),
                    }
                else:
                    desc, tables, joins = result
                    payload = {
                        "query_index": original_index,
                        "query": query_text,
                        "description": desc,
                        "tables": tables,
                        "joins": joins,
                    }

                results.append(payload)
                if progress_tracker:
                    progress_tracker.record_success((original_index, query_text), payload)

        batch_number += 1
        start += len(batch)
        if start < len(remaining_items):
            await asyncio.sleep(0.5)

    print("\n=== BATCH PROCESSING COMPLETE ===")
    final_stats = GEMINI_RATE_LIMITER.get_stats()
    print(f"Final success rate: {final_stats['success_rate']:.1f}%")
    print(f"Total requests: {final_stats['total_processed']}")
    print(f"Total errors: {final_stats['total_errors']}")

    aggregated_results = progress_tracker.get_results() if progress_tracker else results
    if aggregated_results and any("query_index" in r for r in aggregated_results):
        aggregated_results = sorted(aggregated_results, key=lambda r: r.get("query_index", 0))
    df = pd.DataFrame(aggregated_results)

    if return_tokens:
        if not aggregated_results:
            usage_summary = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        else:
            usage_summary = {
                "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in aggregated_results),
                "completion_tokens": sum(r.get("completion_tokens", 0) for r in aggregated_results),
                "total_tokens": sum(r.get("total_tokens", 0) for r in aggregated_results),
            }
        return df, usage_summary, aggregated_results
    return df

def generate_metadata_for_queries(
    query_texts,
    max_concurrent=None,
    return_tokens=False,
    resume_from_checkpoint=True,
    tracker: Optional[ProgressTracker] = None,
):
    """
    Generate metadata for queries and return as DataFrame with progress tracking.
    
    Args:
        query_texts: List of SQL query strings
        max_concurrent: Maximum concurrent requests (None for adaptive)
        return_tokens: Whether to return token usage data
        resume_from_checkpoint: Whether to resume from previous checkpoint
        tracker: Optional pre-initialized progress tracker
    """
    query_items = list(enumerate(query_texts))
    
    # Initialize progress tracker
    effective_tracker = tracker if tracker is not None else (
        ProgressTracker("sql_metadata_generation") if resume_from_checkpoint else None
    )
    
    return asyncio.run(generate_metadata_parallel(
        query_items, max_concurrent, return_tokens, effective_tracker
    ))

def load_queries_from_csv(csv_path, query_column='queries'):
    """
    Load queries from CSV file
    
    Args:
        csv_path: Path to CSV file containing SQL queries
        query_column: Column name containing SQL queries (default: 'sql')
        
    Returns:
        List of SQL query strings
    """
    try:
        df = pd.read_csv(csv_path)
        print(f"📄 Loaded CSV with {len(df)} rows and columns: {list(df.columns)}")
        
        # Check if query column exists
        if query_column not in df.columns:
            available_cols = list(df.columns)
            raise ValueError(f"Column '{query_column}' not found in CSV. Available columns: {available_cols}")
        
        # Filter for queries that have content
        df_queries = df[df[query_column].notna() & (df[query_column].str.strip() != '')].copy()
        initial_count = len(df)
        filtered_count = len(df_queries)
        
        if initial_count != filtered_count:
            print(f"⚠️  Filtered out {initial_count - filtered_count} rows with empty/null queries")
        
        # Remove duplicates
        df_queries = df_queries.drop_duplicates(subset=[query_column]).reset_index(drop=True)
        dedupe_count = len(df_queries)
        
        if filtered_count != dedupe_count:
            print(f"⚠️  Removed {filtered_count - dedupe_count} duplicate queries")
        
        # Clean the queries
        df_queries[query_column] = df_queries[query_column].str.replace('\n', ' ').str.replace('\r', ' ')
        df_queries[query_column] = df_queries[query_column].str.replace(r'\s+', ' ', regex=True).str.strip()
        
        query_list = df_queries[query_column].tolist()
        print(f"✅ Successfully loaded {len(query_list)} unique, valid queries from CSV")
        
        return query_list, df  # Return both query list and original dataframe
        
    except Exception as e:
        print(f"❌ Error loading CSV file: {e}")
        raise

def save_results_to_csv(results, output_path, original_df=None, query_column='sql'):
    """
    Save generated metadata to CSV file
    
    Args:
        results: List of dictionaries with query metadata
        output_path: Path where to save the results CSV
        original_df: Original DataFrame to merge with (optional)
        query_column: Column name that contains SQL queries in original_df
    """
    try:
        results_df = pd.DataFrame(results)
        print(f"📊 Generated metadata for {len(results_df)} queries")
        
        if "query_index" in results_df.columns:
            results_df = results_df.sort_values("query_index").reset_index(drop=True)
            results_df = results_df.drop(columns=["query_index"])
        
        if original_df is not None:
            print("🔗 Merging results with original data to preserve all columns...")
            # Merge with original data to preserve other columns like query_id, difficulty_level
            merged_df = original_df.merge(
                results_df, 
                left_on=query_column, 
                right_on='query', 
                how='left',
                suffixes=('_original', '_generated')
            )
            
            # Clean up duplicate query columns if they exist
            if 'query' in merged_df.columns and query_column != 'query':
                merged_df = merged_df.drop('query', axis=1)
            
            # Rename generated description if original has description
            if 'description' in original_df.columns and 'description' in results_df.columns:
                if 'description_generated' in merged_df.columns:
                    merged_df['ai_description'] = merged_df['description_generated']
                    merged_df = merged_df.drop('description_generated', axis=1)
            
            merged_df.to_csv(output_path, index=False)
            print(f"✅ Merged results saved to: {output_path}")
            print(f"📋 Final CSV has {len(merged_df)} rows and {len(merged_df.columns)} columns")
        else:
            results_df.to_csv(output_path, index=False)
            print(f"✅ Results saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error saving results to CSV: {e}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate SQL metadata (descriptions, tables, joins) using Gemini AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process CSV file
  python description_generator.py --csv "data_new/generated_sql_queries.csv" --query-column "sql"
  
  # Process CSV with custom output
  python description_generator.py --csv "queries.csv" --query-column "sql" --output "enhanced_queries.csv"
  
  # Original BigQuery mode (uses environment variables)
  python description_generator.py
        """
    )
    
    parser.add_argument(
        '--csv', 
        help='Path to CSV file containing SQL queries (alternative to BigQuery mode)'
    )
    
    parser.add_argument(
        '--query-column', 
        default='sql',
        help='Column name containing SQL queries in the CSV (default: sql)'
    )
    
    parser.add_argument(
        '--output', 
        help='Output CSV file path (default: <input_file>_with_metadata.csv)'
    )
    
    parser.add_argument(
        '--preserve-original',
        action='store_true',
        default=True,
        help='Merge results with original CSV to preserve all columns (default: True)'
    )
    
    parser.add_argument(
        '--max-concurrent',
        type=int,
        help='Maximum concurrent API requests (default: adaptive based on rate limiter)'
    )
    
    parser.add_argument(
        '--model',
        default=MODEL_NAME,
        help=f'Gemini model to use for metadata generation (default: {MODEL_NAME})'
    )
    
    parser.add_argument(
        '--requests-per-minute',
        type=int,
        help='Override rate limiter requests-per-minute (default: environment or 15)'
    )
    
    parser.add_argument(
        '--tokens-per-minute',
        type=int,
        help='Override rate limiter tokens-per-minute (default: environment or 250000)'
    )
    
    parser.add_argument(
        '--requests-per-day',
        type=int,
        help='Override rate limiter requests-per-day (default: environment or auto)'
    )
    
    args = parser.parse_args()
    
    # Apply configuration overrides
    if args.model:
        MODEL_NAME = args.model
    
    env_rpm = os.getenv("GENAI_REQUESTS_PER_MINUTE")
    if env_rpm and not args.requests_per_minute:
        try:
            GEMINI_RATE_LIMITER.requests_per_minute = int(env_rpm)
        except ValueError:
            print(f"⚠️  Ignoring invalid GENAI_REQUESTS_PER_MINUTE value: {env_rpm}")
    if args.requests_per_minute:
        GEMINI_RATE_LIMITER.requests_per_minute = args.requests_per_minute
    
    env_tpm = os.getenv("GENAI_TOKENS_PER_MINUTE")
    if env_tpm and not args.tokens_per_minute:
        try:
            GEMINI_RATE_LIMITER.tokens_per_minute = int(env_tpm)
        except ValueError:
            print(f"⚠️  Ignoring invalid GENAI_TOKENS_PER_MINUTE value: {env_tpm}")
    if args.tokens_per_minute:
        GEMINI_RATE_LIMITER.tokens_per_minute = args.tokens_per_minute
    
    env_rpd = os.getenv("GENAI_REQUESTS_PER_DAY")
    if env_rpd and not args.requests_per_day:
        try:
            GEMINI_RATE_LIMITER.requests_per_day = int(env_rpd)
        except ValueError:
            print(f"⚠️  Ignoring invalid GENAI_REQUESTS_PER_DAY value: {env_rpd}")
    if args.requests_per_day:
        GEMINI_RATE_LIMITER.requests_per_day = args.requests_per_day
    
    print("=== SQL METADATA GENERATOR WITH RATE LIMITING ===")
    print(f"Using model: {MODEL_NAME}")
    print(
        "Rate limits: "
        f"{GEMINI_RATE_LIMITER.requests_per_minute} RPM, "
        f"{GEMINI_RATE_LIMITER.tokens_per_minute:,} TPM, "
        f"{GEMINI_RATE_LIMITER.requests_per_day} RPD"
    )
    
    if args.csv:
        print(f"\n🔧 CSV MODE: Processing file {args.csv}")
        
        # Validate CSV file exists
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"❌ CSV file not found: {args.csv}")
            exit(1)
        
        # Set output path
        if args.output:
            output_path = args.output
        else:
            output_path = csv_path.parent / f"{csv_path.stem}_with_metadata.csv"
        
        print(f"📁 Input: {args.csv}")
        print(f"📁 Output: {output_path}")
        print(f"🔍 Query column: {args.query_column}")
    else:
        print(f"\n🔧 BIGQUERY MODE: Using environment configuration")
        # Initialize BigQuery client for traditional mode
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("bigquery_client")
        if not project_id:
            print("❌ GOOGLE_CLOUD_PROJECT (or legacy bigquery_client) must be set for BigQuery mode.")
            exit(1)
        if not host_table_name:
            print("❌ 'host_table' environment variable must be set for BigQuery mode.")
            exit(1)
        bq_client = bigquery.Client(project=project_id)
    
    # Load queries based on mode
    if args.csv:
        # CSV MODE: Load queries from CSV file
        print(f"\n📂 Loading queries from CSV...")
        try:
            query_list, original_df = load_queries_from_csv(args.csv, args.query_column)
        except Exception as e:
            print(f"❌ Failed to load CSV: {e}")
            exit(1)
            
    else:
        # BIGQUERY MODE: Original logic
        print("\nChecking table schema...")
        table_ref = bq_client.get_table(host_table_name)
        schema_fields = {field.name for field in table_ref.schema}
        required_columns = {
            "description": "STRING",
            "tables": "STRING",
            "joins": "STRING"
        }
        missing_columns = []
        for col_name, col_type in required_columns.items():
            if col_name not in schema_fields:
                missing_columns.append((col_name, col_type))
        
        if missing_columns:
            for col_name, col_type in missing_columns:
                print(f"Adding '{col_name}' column to query_host table...")
                add_column_query = f"""
                ALTER TABLE `{host_table_name}`
                ADD COLUMN {col_name} {col_type}
                """
                bq_client.query(add_column_query).result()
                print(f"{col_name} column added successfully!")
        else:
            print("All required columns already exist.")
        
        print("\nLoading queries from BigQuery...")
        print(f"Using host table: {host_table_name}")
        query = f"""
        SELECT DISTINCT query
        FROM `{host_table_name}`
        WHERE description IS NULL OR description = ''
           OR tables IS NULL OR tables = ''
           OR joins IS NULL OR joins = ''
           OR description='None' OR tables='None' or joins='None'
        """
        df_queries = bq_client.query(query).to_dataframe()
        df_queries = df_queries.drop_duplicates(subset=['query']).reset_index(drop=True)
        df_queries['query'] = df_queries['query'].str.replace('\n', ' ').str.replace('\r', ' ')
        df_queries['query'] = df_queries['query'].str.replace(r'\s+', ' ', regex=True).str.strip()
        
        # Optional: limit for testing
        # df_queries = df_queries[:100]  # Uncomment for testing with smaller dataset
        
        query_list = df_queries['query'].tolist()
        original_df = None  # No original dataframe to preserve in BigQuery mode
        
    print(f"📊 Found {len(query_list)} queries to process")
    
    if len(query_list) == 0:
        print("⚠️  No queries to process. Exiting.")
        exit(0)
    
    # Initialize progress tracker
    tracker = ProgressTracker("sql_metadata_generation")
    
    try:
        env_concurrency_default = int(os.getenv("GENAI_MAX_CONCURRENT", "6"))
    except ValueError:
        env_concurrency_default = 6
    target_concurrency = args.max_concurrent or env_concurrency_default

    print("\n=== STARTING METADATA GENERATION ===")
    print("Features enabled:")
    print(f"✅ Rate limiting ({GEMINI_RATE_LIMITER.requests_per_minute} RPM)")
    print(f"✅ Adaptive concurrency (target {target_concurrency})")
    print("✅ Exponential backoff")
    print("✅ Progress checkpointing")
    print("✅ Error recovery")
    
    try:
        df_results, total_token_usage, results = generate_metadata_for_queries(
            query_list,
            max_concurrent=args.max_concurrent,  # Use user-specified or adaptive concurrency
            return_tokens=True,
            resume_from_checkpoint=True,
            tracker=tracker
        )
        
        # Save results based on mode
        if args.csv:
            # CSV MODE: Save to CSV file
            print(f"\n💾 Saving results to CSV...")
            save_results_to_csv(
                results, 
                output_path, 
                original_df if args.preserve_original else None,
                args.query_column
            )
            
            # Also save detailed JSON results
            json_file = str(output_path).replace('.csv', '_detailed_results.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"📋 Detailed results also saved to: {json_file}")
            
        else:
            # BIGQUERY MODE: Original behavior - save detailed results only
            results_file = 'detailed_results_dict.json'
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nResults dictionary exported to: {results_file}")
        
        # Save final progress
        if tracker:
            tracker.save_final_results({
                "total_token_usage": total_token_usage,
                "rate_limiter_stats": GEMINI_RATE_LIMITER.get_stats()
            })
        
        print(f"\n=== PROCESSING SUMMARY ===")
        print(f"✅ Generated metadata for {len(df_results)} queries")
        print(f"✅ Used {total_token_usage['total_tokens']:,} total tokens")
        print(f"✅ Success rate: {GEMINI_RATE_LIMITER.get_stats()['success_rate']:.1f}%")
        
        if args.csv:
            print(f"✅ Results saved to: {output_path}")
            print(f"\n🚀 Next step: Run embedding generator with your enhanced CSV file:")
            print(f"   python standalone_embedding_generator.py --csv \"{output_path}\"")
        
    except KeyboardInterrupt:
        print("\n=== INTERRUPTED BY USER ===")
        print("Progress has been saved. You can resume by running the script again.")
        if tracker:
            tracker.print_progress()
    except Exception as e:
        print(f"\n=== ERROR OCCURRED ===")
        print(f"Error: {str(e)}")
        print("Progress has been saved. You can resume by running the script again.")
        if tracker:
            tracker.print_progress()
        raise
