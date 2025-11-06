#!/usr/bin/env python3
"""
Simple BigQuery Client

A minimal wrapper around the BigQuery Python client that executes SQL
queries and returns results as pandas DataFrames.
"""

import pandas as pd
from google.cloud import bigquery
from typing import Optional


class BigQueryClient:
    """
    Simple BigQuery client for executing queries and returning DataFrames.

    This class provides a minimal interface to BigQuery with support for:
    - Executing queries and returning pandas DataFrames
    - Dry-run byte estimation
    - Configurable billing limits

    Example:
        >>> client = BigQueryClient(project_id="my-project")
        >>> df = client.query_df("SELECT * FROM dataset.table LIMIT 10")
        >>> bytes_estimate = client.dry_run_bytes("SELECT * FROM large_table")
    """


    def __init__(
        self,
        project_id: str = "brainrot-453319",
        location: Optional[str] = None,
        max_bytes_billed: Optional[int] = None
    ):
        """
        Initialize BigQuery client.

        Args:
            project_id: Google Cloud project ID (default: brainrot-453319)
            location: BigQuery location/region (default: None, uses dataset location)
            max_bytes_billed: Maximum bytes to bill for queries (default: None)
        """
        self.project_id = project_id
        self.location = location
        self.max_bytes_billed = max_bytes_billed
        self.client = bigquery.Client(project=project_id)

    def query_df(
        self,
        sql: str,
        timeout: int = 30
    ) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.

        Args:
            sql: SQL query string to execute
            timeout: Query timeout in seconds (default: 30)

        Returns:
            pandas DataFrame containing query results

        Raises:
            Exception: If query execution fails
        """
        # Configure query job
        job_config = bigquery.QueryJobConfig()

        if self.max_bytes_billed is not None:
            job_config.maximum_bytes_billed = self.max_bytes_billed

        # Execute query
        query_job = self.client.query(sql, job_config=job_config, location=self.location)

        # Wait for completion and convert to DataFrame
        df = query_job.result(timeout=timeout).to_dataframe()

        return df

    def dry_run_bytes(self, sql: str) -> int:
        """
        Estimate bytes that would be processed by a query without executing it.

        Args:
            sql: SQL query string to estimate

        Returns:
            Estimated bytes that would be processed

        Raises:
            Exception: If dry run fails (e.g., invalid SQL)
        """
        # Configure dry run
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

        # Run dry run
        query_job = self.client.query(sql, job_config=job_config, location=self.location)

        # Return byte estimate
        return query_job.total_bytes_processed or 0


def execute_query(
    sql: str,
    project_id: str = "brainrot-453319",
    timeout: int = 30
) -> pd.DataFrame:
    """
    Execute a SQL query on BigQuery and return results as a DataFrame.

    Args:
        sql: SQL query string to execute
        project_id: Google Cloud project ID (default: brainrot-453319)
        timeout: Query timeout in seconds (default: 30)

    Returns:
        pandas DataFrame containing query results

    Raises:
        Exception: If query execution fails

    Example:
        >>> df = execute_query("SELECT * FROM `bigquery-public-data.thelook_ecommerce.users` LIMIT 10")
        >>> print(df.head())
    """
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)

    # Execute query
    query_job = client.query(sql)

    # Wait for query to complete and return as DataFrame
    df = query_job.result(timeout=timeout).to_dataframe()

    return df


def execute_query_with_stats(
    sql: str,
    project_id: str = "brainrot-453319",
    timeout: int = 30
) -> tuple[pd.DataFrame, dict]:
    """
    Execute a SQL query and return both results and execution statistics.

    Args:
        sql: SQL query string to execute
        project_id: Google Cloud project ID (default: brainrot-453319)
        timeout: Query timeout in seconds (default: 30)

    Returns:
        Tuple of (DataFrame, stats_dict) where stats_dict contains:
        - total_rows: Number of rows returned
        - bytes_processed: Total bytes processed by query
        - cache_hit: Whether query results were cached

    Example:
        >>> df, stats = execute_query_with_stats("SELECT COUNT(*) FROM `bigquery-public-data.thelook_ecommerce.orders`")
        >>> print(f"Processed {stats['bytes_processed']} bytes")
    """
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)

    # Execute query
    query_job = client.query(sql)

    # Wait for completion
    result = query_job.result(timeout=timeout)

    # Convert to DataFrame
    df = result.to_dataframe()

    # Extract statistics
    stats = {
        "total_rows": query_job.total_rows or len(df),
        "bytes_processed": query_job.total_bytes_processed,
        "cache_hit": query_job.cache_hit
    }

    return df, stats
