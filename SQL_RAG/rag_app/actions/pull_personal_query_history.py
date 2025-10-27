#!/usr/bin/env python3
"""
Historical Query Analyzer

Pulls historical SQL queries from BigQuery's INFORMATION_SCHEMA.JOBS_BY_USER
for analysis and pattern detection. Includes proper error handling, 
authentication, and performance optimization.
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bigquery_client(project_id: Optional[str] = None) -> bigquery.Client:
    """Initialize BigQuery client with proper authentication and error handling."""
    try:
        # Use environment variable or provided project ID
        project = project_id or os.getenv('GOOGLE_CLOUD_PROJECT', 'wmt-454116e4ab929d9df44a742fc8')
        
        # Initialize client with default credentials
        client = bigquery.Client(project=project)
        
        # Test the connection
        client.query("SELECT 1").result()
        
        logger.info(f"Successfully connected to BigQuery project: {project}")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        raise RuntimeError(f"BigQuery connection failed: {e}")

def pull_queries_from_personal_history(
    bq_client: bigquery.Client, 
    days_back: int = 30,
    min_query_length: int = 10,
    exclude_system_queries: bool = True
) -> pd.DataFrame:
    """Pull historical queries from BigQuery with filtering and optimization.
    
    Args:
        bq_client: Authenticated BigQuery client
        days_back: Number of days to look back for queries (default: 30)
        min_query_length: Minimum length of query to include (default: 10)
        exclude_system_queries: Whether to filter out system/internal queries
    
    Returns:
        DataFrame with distinct historical queries
    """
    try:
        # Calculate date range for filtering
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Optimized query with proper filtering
        base_query = """
        SELECT 
            DISTINCT TRIM(query) as query,
            creation_time,
            user_email,
            statement_type,
            total_bytes_processed,
            total_slot_ms
        FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_USER`
        WHERE job_type = 'QUERY'
        AND error_result IS NULL
        AND creation_time >= TIMESTAMP('%s')
        AND LENGTH(Trim(query)) >= %d
        AND query IS NOT NULL
        """ % (cutoff_date.isoformat(), min_query_length)
        
        # Add system query exclusions if requested
        if exclude_system_queries:
            exclusions = """
            AND UPPER(query) NOT LIKE 'SELECT %% FROM INFORMATION_SCHEMA%%'
            AND UPPER(query) NOT LIKE 'SHOW %%'
            AND UPPER(query) NOT LIKE 'DESCRIBE %%'
            AND UPPER(query) NOT LIKE 'EXPLAIN %%'
            AND UPPER(query) NOT LIKE 'PRAGMA %%'
            AND query NOT LIKE 'SELECT _PIPELINE_UUID%'
            AND query NOT LIKE 'SELECT %% FROM `%%.__TABLES_SUMMARY__`%%'
            """
            base_query += exclusions
        
        # Add ordering for consistent results
        base_query += " ORDER BY creation_time DESC"
        
        logger.info(f"Executing historical query analysis for the last {days_back} days")
        
        # Execute query with job configuration for performance
        job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            maximum_bytes_billed=10**10  # 10GB limit to prevent overages
        )
        
        query_job = bq_client.query(base_query, job_config=job_config)
        fresh_queries = query_job.to_dataframe()
        
        logger.info(f"Successfully fetched {len(fresh_queries)} distinct historical queries")
        
        # Add metadata about the query run
        fresh_queries['analysis_date'] = datetime.now()
        fresh_queries['days_analyzed'] = days_back
        
        return fresh_queries
        
    except GoogleCloudError as e:
        logger.error(f"BigQuery error during historical analysis: {e}")
        raise RuntimeError(f"BigQuery query failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during historical analysis: {e}")
        raise RuntimeError(f"Historical query analysis failed: {e}")

def analyze_query_patterns(queries_df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze patterns in historical queries."""
    if queries_df.empty:
        return {"error": "No queries to analyze"}
    
    analysis = {
        "total_queries": len(queries_df),
        "avg_bytes_processed": queries_df['total_bytes_processed'].mean() if 'total_bytes_processed' in queries_df.columns else 0,
        "most_common_users": queries_df['user_email'].value_counts().head(5).to_dict() if 'user_email' in queries_df.columns else {},
        "query_types": queries_df['statement_type'].value_counts().to_dict() if 'statement_type' in queries_df.columns else {},
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    return analysis

def main():
    """Main execution function for historical query analysis."""
    try:
        # Initialize client
        client = get_bigquery_client()
        
        # Pull historical queries
        queries_df = pull_queries_from_personal_history(
            client, 
            days_back=30,
            min_query_length=10,
            exclude_system_queries=True
        )
        
        # Analyze patterns
        analysis = analyze_query_patterns(queries_df)
        
        # Print results
        print(f"\n=== Historical Query Analysis ===")
        print(f"Total queries found: {analysis['total_queries']}")
        print(f"Average bytes processed: {analysis['avg_bytes_processed']:,.0f}")
        
        if analysis['most_common_users']:
            print("\nTop users:")
            for user, count in analysis['most_common_users'].items():
                print(f"  {user}: {count} queries")
        
        if analysis['query_types']:
            print("\nQuery types:")
            for qtype, count in analysis['query_types'].items():
                print(f"  {qtype}: {count} queries")
        
        # Save to CSV for further analysis
        output_file = f"historical_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        queries_df.to_csv(output_file, index=False)
        print(f"\nQueries saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())