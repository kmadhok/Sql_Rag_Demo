import asyncio
import google.generativeai as genai
import base64
import pandas as pd
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os
from pathlib import Path
import json
import csv
import time
import logging
import argparse
from utils.rate_limiter import GEMINI_RATE_LIMITER, exponential_backoff_retry
from utils.progress_tracker import ProgressTracker

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

bq_client = os.getenv("bigquery_client")
vertex_ai_client = os.getenv("vertex_ai_client")
host_table_name=os.getenv("host_table")
llm_model_name=os.getenv("llm_model_name")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


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
    # Initialize model
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Count tokens before API call
    token_count = model.count_tokens(prompt)
    prompt_tokens = token_count.total_tokens
    try:
        response = model.generate_content(prompt)
        
        # Record successful request with rate limiter
        GEMINI_RATE_LIMITER.record_request(token_count.total_tokens)
        result = response.text.strip()
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, 'usage_metadata') else 0,
            "total_tokens": getattr(response.usage_metadata, "total_token_count", 0) if hasattr(response, 'usage_metadata') else 0
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

async def generate_metadata_parallel(query_texts, max_concurrent=None, return_tokens=False, progress_tracker=None):
    """
    Generate metadata for multiple SQL queries in parallel with rate limiting.
    """
    # Use adaptive concurrency from rate limiter if not specified
    if max_concurrent is None:
        max_concurrent = GEMINI_RATE_LIMITER.get_current_concurrency()
    
    total = len(query_texts)
    print(f"Processing {total} queries with adaptive concurrency (starting with {max_concurrent})...")
    
    results = []
    total_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    # Initialize progress tracker if provided
    if progress_tracker:
        remaining_queries = progress_tracker.initialize(query_texts)
    else:
        remaining_queries = query_texts
    
    if not remaining_queries:
        print("All queries already processed according to checkpoint!")
        return results if not progress_tracker else progress_tracker.get_results()
    
    print(f"Processing {len(remaining_queries)} remaining queries...")
    
    for i in range(0, len(remaining_queries), max_concurrent):
        # Update concurrency based on rate limiter's adaptive algorithm
        current_concurrency = min(max_concurrent, GEMINI_RATE_LIMITER.get_current_concurrency())
        batch = remaining_queries[i:i + current_concurrency]
        
        print(f"\nProcessing batch of {len(batch)} queries (batch {i//max_concurrent + 1})")
        print(f"Current concurrency: {current_concurrency}")
        
        # Print rate limiter stats
        stats = GEMINI_RATE_LIMITER.get_stats()
        print(f"Rate limiter stats - RPM: {stats['requests_last_minute']}/15, "
              f"Success rate: {stats['success_rate']:.1f}%")
        
        if progress_tracker:
            progress_tracker.print_progress()
        
        # Process batch with individual error handling
        batch_tasks = []
        for idx, query in enumerate(batch):
            global_idx = query_texts.index(query) if query in query_texts else i + idx
            batch_tasks.append(
                generate_metadata_async(query, global_idx, total, return_tokens)
            )
        
        # Use gather with return_exceptions to handle individual failures
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Process results and handle errors
        for idx, result in enumerate(batch_results):
            query = batch[idx]
            
            if isinstance(result, Exception):
                error_msg = f"Error processing query: {str(result)}"
                print(f"Failed query {i + idx + 1}: {error_msg}")
                
                if progress_tracker:
                    progress_tracker.record_failure(query, error_msg)
                
                # Add error result to maintain consistency
                if return_tokens:
                    results.append({
                        "query": query,
                        "description": error_msg,
                        "tables": "[]",
                        "joins": "[]",
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    })
                else:
                    results.append({
                        "query": query,
                        "description": error_msg,
                        "tables": "[]",
                        "joins": "[]"
                    })
            else:
                # Successful result
                if return_tokens:
                    desc, tables, joins, token_data = result
                    query_result = {
                        "query": query,
                        "description": desc,
                        "tables": tables,
                        "joins": joins,
                        "prompt_tokens": token_data.get("prompt_tokens", 0),
                        "completion_tokens": token_data.get("completion_tokens", 0),
                        "total_tokens": token_data.get("total_tokens", 0)
                    }
                    if "error" not in token_data:
                        total_token_usage["prompt_tokens"] += token_data["prompt_tokens"]
                        total_token_usage["completion_tokens"] += token_data["completion_tokens"]
                        total_token_usage["total_tokens"] += token_data["total_tokens"]
                else:
                    desc, tables, joins = result
                    query_result = {
                        "query": query,
                        "description": desc,
                        "tables": tables,
                        "joins": joins
                    }
                
                results.append(query_result)
                
                if progress_tracker:
                    progress_tracker.record_success(query, query_result)
        
        # Small delay between batches to be respectful to the API
        if i + current_concurrency < len(remaining_queries):
            await asyncio.sleep(1.0)
    
    print(f"\n=== BATCH PROCESSING COMPLETE ===")
    final_stats = GEMINI_RATE_LIMITER.get_stats()
    print(f"Final success rate: {final_stats['success_rate']:.1f}%")
    print(f"Total requests: {final_stats['total_processed']}")
    print(f"Total errors: {final_stats['total_errors']}")
    df = pd.DataFrame(results)
    if return_tokens:
        return df, total_token_usage, results
    return df

def generate_metadata_for_queries(query_texts, max_concurrent=None, return_tokens=False, resume_from_checkpoint=True):
    """
    Generate metadata for queries and return as DataFrame with progress tracking.
    
    Args:
        query_texts: List of SQL query strings
        max_concurrent: Maximum concurrent requests (None for adaptive)
        return_tokens: Whether to return token usage data
        resume_from_checkpoint: Whether to resume from previous checkpoint
    """
    # Initialize progress tracker
    tracker = ProgressTracker("sql_metadata_generation") if resume_from_checkpoint else None
    
    return asyncio.run(generate_metadata_parallel(
        query_texts, max_concurrent, return_tokens, tracker
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
    
    args = parser.parse_args()
    
    print("=== SQL METADATA GENERATOR WITH RATE LIMITING ===")
    print(f"Using model: gemini-2.5-flash-lite")
    print(f"Rate limits: 15 RPM, 250K TPM, 1K RPD")
    
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
        bq_client = bigquery.Client(project=vertex_ai_client)
    
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
    
    print("\n=== STARTING METADATA GENERATION ===")
    print("Features enabled:")
    print("✅ Rate limiting (15 RPM)")
    print("✅ Adaptive concurrency")
    print("✅ Exponential backoff")
    print("✅ Progress checkpointing")
    print("✅ Error recovery")
    
    try:
        df_results, total_token_usage, results = generate_metadata_for_queries(
            query_list,
            max_concurrent=args.max_concurrent,  # Use user-specified or adaptive concurrency
            return_tokens=True,
            resume_from_checkpoint=True
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
        final_data = tracker.save_final_results({
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
        tracker.print_progress()
    except Exception as e:
        print(f"\n=== ERROR OCCURRED ===")
        print(f"Error: {str(e)}")
        print("Progress has been saved. You can resume by running the script again.")
        tracker.print_progress()
        raise