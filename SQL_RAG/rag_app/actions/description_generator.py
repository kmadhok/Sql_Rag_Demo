import asyncio
from google import genai
from google.genai import types
import base64
import pandas as pd
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor

client = genai.Client(
    vertexai=True,
    project="wmt-dv-bq-analytics",
    location="global",
)

def generate_description(query_text, index=None, total=None, return_tokens=False):
    """Generate a 2-sentence description for a SQL query."""
    if index is not None and total is not None:
        print(f"Processing query {index + 1}/{total}...")
    
    prompt = (
        "You are a SQL analyst. Describe this SQL query in exactly 1-2 clear sentences. "
        "Focus only on: what tables are used, what the query calculates, and the business purpose. "
        "Do not include generic instructions or examples.\n\n"
        f"SQL Query:\n{query_text}"
    )
    
    # Count tokens before API call
    token_count = client.models.count_tokens(
        model="gemini-2.5-flash-lite", 
        contents=prompt
    )
    prompt_tokens = token_count.total_tokens
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        result = response.text.strip()
        
        # Extract token usage data
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", 0)
        }
        
        if index is not None:
            print(f"Completed query {index + 1} (tokens: {token_usage['total_tokens']})")
        
        if return_tokens:
            return result, token_usage
        return result
    except Exception as e:
        if index is not None:
            print(f"Error on query {index + 1}: {str(e)}")
        if return_tokens:
            return f"Error generating description: {str(e)}", {"error": str(e)}
        return f"Error generating description: {str(e)}"

async def generate_description_async(query_text, index=None, total=None, return_tokens=False):
    """Async wrapper for generate_description."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(
            pool, generate_description, query_text, index, total, return_tokens
        )

async def generate_descriptions_parallel(query_texts, max_concurrent=10, return_tokens=False):
    """
    Generate descriptions for multiple SQL queries in parallel.
    """
    total = len(query_texts)
    print(f"Processing {total} queries with max {max_concurrent} concurrent requests...")
    
    results = []
    total_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    for i in range(0, total, max_concurrent):
        batch = query_texts[i:i + max_concurrent]
        print(f"Processing batch of {len(batch)} queries (index {i} to {i+len(batch)-1})")
        batch_tasks = [
            generate_description_async(query, i + idx, total, return_tokens) 
            for idx, query in enumerate(batch)
        ]
        batch_results = await asyncio.gather(*batch_tasks)
        
        if return_tokens:
            # Unzip results and token usage
            for idx, (desc, token_data) in enumerate(batch_results):
                query_idx = i + idx
                results.append({
                    "query": query_texts[query_idx],
                    "description": desc,
                    "prompt_tokens": token_data.get("prompt_tokens", 0),
                    "completion_tokens": token_data.get("completion_tokens", 0),
                    "total_tokens": token_data.get("total_tokens", 0)
                })
                if "error" not in token_data:
                    total_token_usage["prompt_tokens"] += token_data["prompt_tokens"]
                    total_token_usage["completion_tokens"] += token_data["completion_tokens"]
                    total_token_usage["total_tokens"] += token_data["total_tokens"]
        else:
            for idx, desc in enumerate(batch_results):
                query_idx = i + idx
                results.append({
                    "query": query_texts[query_idx],
                    "description": desc
                })
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    if return_tokens:
        return df, total_token_usage
    return df

def generate_descriptions_for_queries(query_texts, max_concurrent=10, return_tokens=False):
    """
    Generate descriptions for queries and return as DataFrame.
    
    Args:
        query_texts: List of SQL query strings
        max_concurrent: Maximum number of concurrent requests
        return_tokens: Whether to return token usage data
        
    Returns:
        If return_tokens=False: DataFrame with 'query' and 'description' columns
        If return_tokens=True: Tuple of (DataFrame, total_token_usage_dict)
    """
    return asyncio.run(generate_descriptions_parallel(query_texts, max_concurrent, return_tokens))

# if __name__ == "__main__":
#     # List of SQL queries
#     queries = [
#         "SELECT product_id, SUM(quantity) FROM sales GROUP BY product_id",
#         "SELECT customer_name, COUNT(*) FROM orders WHERE order_date > '2023-01-01' GROUP BY customer_name"
#     ]
#     df_queries=pd.read_csv(r'C:\Users\k0m0oxq\Desktop\repos\Sql_Rag_Demo\SQL_RAG\sample_queries.csv')
#     df_queries=df_queries['query']
#     # Without token tracking
#     df = generate_descriptions_for_queries(df_queries, max_concurrent=2)
#     print(df)
#     # Output will be a DataFrame with 'query' and 'description' columns

#     # With token tracking
#     df, token_usage = generate_descriptions_for_queries(queries, max_concurrent=2, return_tokens=True)
#     print(df)  # DataFrame with query, description and token columns
#     print(f"Total tokens used: {token_usage['total_tokens']}")

#     df.to_csv('queries_with_descriptions.csv', index=False)
#     token_usage.to_csv('token_usage.csv', index=False)
if __name__ == "__main__":
    # Read queries from CSV file
    bq_client = bigquery.Client(project='wmt-dv-bq-analytics')
    # First, check if description column exists and add it if it doesn't
    print("Checking table schema...")
    table_ref = bq_client.get_table("wmt-de-projects.sbx_kanu.query_host")
    # Check if description column exists
    has_description_column = any(field.name == "description" for field in table_ref.schema)
    
    if not has_description_column:
        print("Adding 'description' column to query_host table...")
        add_column_query = """
        ALTER TABLE `wmt-de-projects.sbx_kanu.query_host`
        ADD COLUMN description STRING
        """
        bq_client.query(add_column_query).result()
        print("Description column added successfully!")
    else:
        print("Description column already exists.")
    print("Loading queries from sample_queries.csv...")
    query="""
    select distinct query
    from `wmt-de-projects.sbx_kanu.query_host`
    where description is null or description=''
    """
    df_queries = bq_client.query(query).to_dataframe()
    query_list = df_queries['query'].tolist()
    print(f"Found {len(query_list)} queries to process")
    
    # Generate descriptions with token tracking
    print("Generating descriptions with token tracking...")
    df_results, total_token_usage = generate_descriptions_for_queries(
        query_list, 
        max_concurrent=10,  # Adjust based on your API limits
        return_tokens=True
    )
    
    # Display results summary
    print(f"\n=== PROCESSING COMPLETE ===")
    print(f"Total queries processed: {len(df_results)}")
    print(f"Total prompt tokens: {total_token_usage['prompt_tokens']:,}")
    print(f"Total completion tokens: {total_token_usage['completion_tokens']:,}")
    print(f"Total tokens used: {total_token_usage['total_tokens']:,}")
    
    # Save detailed results (queries + descriptions + individual token usage)
    output_file = 'queries_with_descriptions_and_tokens.csv'
    df_results.to_csv(output_file, index=False)
    print(f"Detailed results saved to: {output_file}")
    
    # Save summary token usage
    summary_df = pd.DataFrame([{
        'total_queries': len(df_results),
        'total_prompt_tokens': total_token_usage['prompt_tokens'],
        'total_completion_tokens': total_token_usage['completion_tokens'],
        'total_tokens': total_token_usage['total_tokens'],
        'avg_tokens_per_query': total_token_usage['total_tokens'] / len(df_results) if len(df_results) > 0 else 0
    }])
    
    summary_file = 'token_usage_summary.csv'
    summary_df.to_csv(summary_file, index=False)
    print(f"Token usage summary saved to: {summary_file}")
    
    # Display first few results as preview
    print(f"\n=== PREVIEW OF RESULTS ===")
    print(df_results.head())
    
    # # Show token distribution
    # if len(df_results) > 0:
    #     print(f"\n=== TOKEN STATISTICS ===")
    #     print(f"Average tokens per query: {df_results['total_tokens'].mean():.1f}")
    #     print(f"Min tokens per query: {df_results['total_tokens'].min()}")
    #     print(f"Max tokens per query: {df_results['total_tokens'].max()}")
    #     print(f"Median tokens per query: {df_results['total_tokens'].median():.1f}")

    # // ...existing code...
    # Show token distribution
    if len(df_results) > 0:
        print(f"\n=== TOKEN STATISTICS ===")
        print(f"Average tokens per query: {df_results['total_tokens'].mean():.1f}")
        print(f"Min tokens per query: {df_results['total_tokens'].min()}")
        print(f"Max tokens per query: {df_results['total_tokens'].max()}")
        print(f"Median tokens per query: {df_results['total_tokens'].median():.1f}")
    
    # Update BigQuery table with generated descriptions
    print(f"\n=== UPDATING BIGQUERY TABLE ===")
    
    # Prepare data for BigQuery update - only query and description columns
    update_df = df_results[['query', 'description']].copy()
    
    # Upload the results to a temporary table first
    temp_table_id = "wmt-de-projects.sbx_kanu.temp_query_descriptions"
    
    print(f"Uploading {len(update_df)} descriptions to temporary table...")
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # Overwrite the temp table
        autodetect=True
    )
    
    load_job = bq_client.load_table_from_dataframe(
        update_df, temp_table_id, job_config=job_config
    )
    load_job.result()  # Wait for the job to complete
    print(f"Temporary table created successfully with {len(update_df)} rows")
    
    # Update the main table using MERGE statement
    merge_query = f"""
    MERGE `wmt-de-projects.sbx_kanu.query_host` AS target
    USING `{temp_table_id}` AS source
    ON target.query = source.query
    WHEN MATCHED THEN
        UPDATE SET description = source.description
    """
    print("Executing MERGE query to update descriptions...")
    merge_job = bq_client.query(merge_query)
    merge_result = merge_job.result()
    
    print(f"MERGE completed successfully!")
    
    # Get update statistics
    stats_query = """
    SELECT 
        COUNT(*) as total_rows,
        SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) as rows_with_descriptions,
        SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END) as rows_without_descriptions
    FROM `wmt-de-projects.sbx_kanu.query_host`
    """
    
    stats_df = bq_client.query(stats_query).to_dataframe()
    total_rows = stats_df.iloc[0]['total_rows']
    with_desc = stats_df.iloc[0]['rows_with_descriptions']
    without_desc = stats_df.iloc[0]['rows_without_descriptions']
    
    print(f"\n=== BIGQUERY UPDATE SUMMARY ===")
    print(f"Total rows in query_host table: {total_rows:,}")
    print(f"Rows with descriptions: {with_desc:,}")
    print(f"Rows without descriptions: {without_desc:,}")
    print(f"Coverage: {(with_desc/total_rows)*100:.1f}%")
    
    # Clean up temporary table
    print(f"\nCleaning up temporary table...")
    bq_client.delete_table(temp_table_id)
    print("Temporary table deleted successfully")
    
    print(f"\n=== ALL OPERATIONS COMPLETE ===")
    print(f"✅ Generated descriptions for {len(df_results)} queries")
    print(f"✅ Updated BigQuery table with new descriptions")
    print(f"✅ Used {total_token_usage['total_tokens']:,} total tokens")