#!/usr/bin/env python3
"""
Append Historical Queries to Host Table

A simplified wrapper for updating the query host table with historical data.
This file provides backward compatibility while using the improved
historical analyzer functionality.
"""

import os
import logging
from typing import Optional
from google.cloud import bigquery
from .pull_personal_query_history import get_bigquery_client, pull_queries_from_personal_history
from .compare_to_host_table import compare_to_host_table

logger = logging.getLogger(__name__)

# Backward compatibility aliases
def pull_queries_from_personal_history_legacy(bq_client):
    """Legacy wrapper for backward compatibility."""
    return pull_queries_from_personal_history(bq_client)

def compare_to_host_table_legacy(bq_client):
    """Legacy wrapper for backward compatibility."""
    return compare_to_host_table(bq_client)
def append_to_host_table(
    bq_client: bigquery.Client,
    host_table: str = 'wmt-de-projects.sbx_kanu.query_host',
    method: str = "append"  # "append" or "replace"
) -> 'pd.DataFrame':
    """Append or replace queries in the host table.
    
    Args:
        bq_client: Authenticated BigQuery client
        host_table: Target table ID
        method: Whether to append new queries or replace entire table
    
    Returns:
        DataFrame containing the processed queries
    """
    import pandas as pd
    
    try:
        logger.info(f"Starting query analysis with method: {method}")
        
        # Get merged queries using the improved function
        if method == "replace":
            all_queries = compare_to_host_table(bq_client, host_table)
        else:
            # For append mode, we need to be more careful
            all_queries = compare_to_host_table(bq_client, host_table)
            
        if all_queries.empty:
            logger.warning("No queries to process")
            return pd.DataFrame()
        
        logger.info(f"Processing {len(all_queries)} queries for host table: {host_table}")
        
        # Prepare DataFrame for BigQuery
        # Convert all columns to strings to avoid schema issues
        df = all_queries.apply(lambda x: x.astype(str) if x.dtype != 'datetime64[ns]' else x)
        
        # Create schema dynamically
        table_schema = []
        for column in df.columns:
            if df[column].dtype == 'datetime64[ns]':
                table_schema.append(
                    bigquery.SchemaField(column, bigquery.enums.SqlTypeNames.TIMESTAMP)
                )
            else:
                table_schema.append(
                    bigquery.SchemaField(column, bigquery.enums.SqlTypeNames.STRING)
                )
        
        # Configure load job
        write_disposition = (
            bigquery.WriteDisposition.WRITE_TRUNCATE 
            if method == "replace" 
            else bigquery.WriteDisposition.WRITE_APPEND
        )
        
        job_config = bigquery.LoadJobConfig(
            schema=table_schema,
            write_disposition=write_disposition,
            create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
            autodetect=False  # Use our explicit schema
        )
        
        # Load data to BigQuery
        job = bq_client.load_table_from_dataframe(
            df, host_table, job_config=job_config
        )
        
        logger.info(f"Starting BigQuery load job: {job.job_id}")
        job.result()
        
        logger.info(f"Successfully {'replaced' if method == 'replace' else 'appended'} {len(df)} queries to {host_table}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to append queries to host table: {e}")
        raise RuntimeError(f"Append operation failed: {e}")

def main():
    """Main execution with improved configuration and error handling."""
    try:
        # Initialize client with proper authentication
        client = get_bigquery_client()
        
        # Configuration from environment
        host_table = os.getenv(
            'QUERY_HOST_TABLE', 
            'wmt-de-projects.sbx_kanu.query_host'
        )
        
        method = os.getenv('UPDATE_METHOD', 'append')
        if method not in ['append', 'replace']:
            logger.warning(f"Invalid method '{method}', defaulting to 'append'")
            method = 'append'
        
        logger.info(f"Starting query table update - Table: {host_table}, Method: {method}")
        
        # Execute the update
        all_queries = append_to_host_table(client, host_table, method)
        
        if not all_queries.empty:
            print(f"\n=== Update Complete ===")
            print(f"Successfully processed {len(all_queries)} queries")
            print(f"Host table: {host_table}")
            print(f"Update method: {method}")
            
            # Save local backup
            local_file = f"host_table_update_{method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            all_queries.to_csv(local_file, index=False)
            print(f"Local backup saved: {local_file}")
        else:
            print("No queries were processed")
        
        return 0
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    from datetime import datetime
    exit(main())
