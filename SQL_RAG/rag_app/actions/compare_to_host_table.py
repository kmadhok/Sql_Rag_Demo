#!/usr/bin/env python3
"""
Compare Historical Queries to Host Table

Compares newly discovered historical queries against existing query host table
to identify and merge new entries while preventing duplicates.
"""

import os
import logging
import pandas as pd
from typing import Dict, Any
from google.cloud import bigquery
from .pull_personal_query_history import pull_queries_from_personal_history, get_bigquery_client

logger = logging.getLogger(__name__)

def compare_to_host_table(
    bq_client: bigquery.Client,
    host_table_id: str = "wmt-de-projects.sbx_kanu.query_host",
    days_back: int = 30
) -> pd.DataFrame:

    """Compare historical queries with host table and merge new entries.
    
    Args:
        bq_client: Authenticated BigQuery client
        host_table_id: Full table ID for the query host table
        days_back: Number of days to look back for historical queries
    
    Returns:
        DataFrame containing merged existing and new queries
    """
    try:
        # Pull fresh historical queries
        logger.info(f"Pulling historical queries for the last {days_back} days")
        fresh_queries = pull_queries_from_personal_history(
            bq_client, 
            days_back=days_back
        )
        
        if fresh_queries.empty:
            logger.warning("No historical queries found")
            return pd.DataFrame()
        
        logger.info(f"Found {len(fresh_queries)} historical queries")
        
        # Try to fetch existing queries from host table
        existing_query = f"SELECT * FROM `{host_table_id}`"
        
        try:
            existing_queries = bq_client.query(existing_query).to_dataframe()
            logger.info(f"Found {len(existing_queries)} existing queries in host table")
            
            # Normalize query text for comparison
            fresh_queries['query_normalized'] = fresh_queries['query'].str.strip().str.upper()
            if 'query' in existing_queries.columns:
                existing_queries['query_normalized'] = existing_queries['query'].str.strip().str.upper()
            else:
                # If the column name is different, find it
                possible_query_cols = [col for col in existing_queries.columns if 'query' in col.lower()]
                if possible_query_cols:
                    existing_queries['query_normalized'] = existing_queries[possible_query_cols[0]].str.strip().str.upper()
                else:
                    raise ValueError("Could not find query column in existing table")
            
            # Find new queries that aren't already in existing table
            existing_query_set = set(existing_queries['query_normalized'].dropna())
            new_mask = ~fresh_queries['query_normalized'].isin(existing_query_set)
            new_queries = fresh_queries[new_mask].copy()
            
            logger.info(f"Found {len(new_queries)} new queries to append")
            
            # Prepare new queries for merging
            if not new_queries.empty:
                # Remove normalization columns
                new_queries = new_queries.drop(columns=['query_normalized'])
                fresh_queries = fresh_queries.drop(columns=['query_normalized'])
                
                # Add missing columns with default values
                for col in ['description', 'category', 'complexity_score']:
                    if col in existing_queries.columns and col not in new_queries.columns:
                        new_queries[col] = pd.NA
                    elif col not in new_queries.columns:
                        new_queries[col] = pd.NA
                
                # Combine existing and new queries
                all_queries = pd.concat([existing_queries, new_queries], ignore_index=True)
            else:
                logger.info("No new queries to add - all queries already exist in host table")
                all_queries = existing_queries
                
        except Exception as e:
            logger.warning(f"No existing table found or error accessing it: {e}")
            logger.info("Starting fresh with historical queries only")
            all_queries = fresh_queries
            
            # Add standard columns if they don't exist
            for col in ['description', 'category', 'complexity_score']:
                if col not in all_queries.columns:
                    all_queries[col] = pd.NA
        
        logger.info(f"Total queries after merge: {len(all_queries)}")
        return all_queries
        
    except Exception as e:
        logger.error(f"Error during comparison process: {e}")
        raise RuntimeError(f"Query comparison failed: {e}")

def upload_merged_queries(
    bq_client: bigquery.Client,
    merged_df: pd.DataFrame,
    host_table_id: str = "wmt-de-projects.sbx_kanu.query_host"
) -> bool:
    """Upload the merged queries back to the host table.
    
    Args:
        bq_client: Authenticated BigQuery client
        merged_df: DataFrame containing merged queries
        host_table_id: Target table ID
    
    Returns:
        True if upload successful, False otherwise
    """
    try:
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True
        )
        
        job = bq_client.load_table_from_dataframe(
            merged_df, host_table_id, job_config=job_config
        )
        job.result()  # Wait for the job to complete
        
        logger.info(f"Successfully uploaded {len(merged_df)} queries to {host_table_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upload queries to BigQuery: {e}")
        return False

def main():
    """Main execution function for comparing and updating query host table."""
    try:
        # Initialize BigQuery client
        client = get_bigquery_client()
        
        # Compare historical queries with host table
        merged_df = compare_to_host_table(
            client,
            host_table_id=os.getenv('QUERY_HOST_TABLE', 'wmt-de-projects.sbx_kanu.query_host'),
            days_back=int(os.getenv('ANALYSIS_DAYS_BACK', '30'))
        )
        
        if merged_df.empty:
            print("No queries to process")
            return 0
        
        # Save locally for backup
        local_file = f"merged_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        merged_df.to_csv(local_file, index=False)
        print(f"Local backup saved to: {local_file}")
        
        # Optionally upload back to BigQuery
        upload_to_bq = os.getenv('UPLOAD_TO_BIGQUERY', 'false').lower() == 'true'
        if upload_to_bq:
            success = upload_merged_queries(client, merged_df)
            if success:
                print("Successfully uploaded merged queries to BigQuery")
            else:
                print("Failed to upload to BigQuery, but local backup was saved")
        else:
            print("Skipping BigQuery upload (set UPLOAD_TO_BIGQUERY=true to enable)")
        
        print(f"\n=== Summary ===")
        print(f"Total queries processed: {len(merged_df)}")
        if 'description' in merged_df.columns:
            print(f"Queries with descriptions: {merged_df['description'].notna().sum()}")
        if 'creation_time' in merged_df.columns:
            print(f"Date range: {merged_df['creation_time'].min()} to {merged_df['creation_time'].max()}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    from datetime import datetime
    exit(main())
