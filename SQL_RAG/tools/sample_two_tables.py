#!/usr/bin/env python3
"""
Sample Two BigQuery Tables

Utility script to fetch up to 100 rows from two BigQuery tables
and save them as CSVs for downstream testing.

Example usage:
    python tools/sample_two_tables.py \
      --table-a bigquery-public-data.thelook_ecommerce.orders \
      --table-b bigquery-public-data.thelook_ecommerce.order_items \
      --where-a "order_id IS NOT NULL" \
      --max-bytes-billed 5000000000
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# Add parent directory to path to import bigquery_client
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_app.bigquery_client import BigQueryClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def build_query(table: str, where_clause: Optional[str] = None) -> str:
    """
    Build a SELECT query with LIMIT 100 and optional WHERE clause.

    Args:
        table: Fully-qualified table name (project.dataset.table)
        where_clause: Optional WHERE clause (without the WHERE keyword)

    Returns:
        SQL query string
    """
    query = f"SELECT * FROM `{table}`"

    if where_clause:
        query += f" WHERE {where_clause}"

    query += " LIMIT 100"

    return query


def sanitize_table_name(table: str) -> str:
    """
    Convert fully-qualified table name to safe filename.

    Args:
        table: Table name like project.dataset.table

    Returns:
        Safe filename like project.dataset.table.csv
    """
    # Remove backticks if present
    table = table.strip("`")
    return f"{table}.csv"


def sample_table(
    client: BigQueryClient,
    table: str,
    where_clause: Optional[str],
    out_dir: Path
) -> None:
    """
    Sample a BigQuery table and save results as CSV.

    Args:
        client: BigQueryClient instance
        table: Fully-qualified table name
        where_clause: Optional WHERE clause
        out_dir: Output directory for CSV file

    Raises:
        Exception: If query fails or table doesn't exist
    """
    logger.info(f"Processing table: {table}")

    # Build query
    query = build_query(table, where_clause)
    logger.info(f"Query: {query}")

    # Dry run to get byte estimate
    try:
        bytes_estimate = client.dry_run_bytes(query)
        logger.info(f"Estimated bytes to process: {bytes_estimate:,} ({bytes_estimate / 1024 / 1024:.2f} MB)")
    except Exception as e:
        logger.error(f"Dry run failed for {table}: {e}")
        raise

    # Execute query
    try:
        df = client.query_df(query)
        logger.info(f"Retrieved {len(df)} rows from {table}")
    except Exception as e:
        logger.error(f"Query execution failed for {table}: {e}")
        raise

    # Save to CSV
    output_file = out_dir / sanitize_table_name(table)
    try:
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(df)} rows to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save CSV for {table}: {e}")
        raise


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Sample two BigQuery tables and save as CSVs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python tools/sample_two_tables.py \\
    --table-a bigquery-public-data.thelook_ecommerce.orders \\
    --table-b bigquery-public-data.thelook_ecommerce.order_items \\
    --where-a "order_id IS NOT NULL" \\
    --max-bytes-billed 5000000000
        """
    )

    # Required arguments
    parser.add_argument(
        "--table-a",
        required=True,
        help="Fully-qualified BigQuery table name (project.dataset.table)"
    )
    parser.add_argument(
        "--table-b",
        required=True,
        help="Fully-qualified BigQuery table name (project.dataset.table)"
    )

    # Optional arguments
    parser.add_argument(
        "--where-a",
        help="Optional WHERE clause for table-a (without WHERE keyword)"
    )
    parser.add_argument(
        "--where-b",
        help="Optional WHERE clause for table-b (without WHERE keyword)"
    )
    parser.add_argument(
        "--location",
        help="BigQuery location/region (default: uses dataset location)"
    )
    parser.add_argument(
        "--max-bytes-billed",
        type=int,
        help="Maximum bytes to bill (default: no limit)"
    )
    parser.add_argument(
        "--out-dir",
        default="./artifacts/samples",
        help="Output directory for CSV files (default: ./artifacts/samples)"
    )
    parser.add_argument(
        "--project-id",
        default="brainrot-453319",
        help="Google Cloud project ID (default: brainrot-453319)"
    )

    args = parser.parse_args()

    # Create output directory
    out_dir = Path(args.out_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {out_dir.absolute()}")
    except Exception as e:
        logger.error(f"Failed to create output directory {out_dir}: {e}")
        sys.exit(1)

    # Initialize BigQuery client
    try:
        client = BigQueryClient(
            project_id=args.project_id,
            location=args.location,
            max_bytes_billed=args.max_bytes_billed
        )
        logger.info(f"Initialized BigQuery client for project: {args.project_id}")
    except Exception as e:
        logger.error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)

    # Sample table A
    try:
        sample_table(client, args.table_a, args.where_a, out_dir)
    except Exception as e:
        logger.error(f"Failed to sample table A: {e}")
        sys.exit(1)

    # Sample table B
    try:
        sample_table(client, args.table_b, args.where_b, out_dir)
    except Exception as e:
        logger.error(f"Failed to sample table B: {e}")
        sys.exit(1)

    logger.info("✅ Successfully sampled both tables!")


if __name__ == "__main__":
    main()
