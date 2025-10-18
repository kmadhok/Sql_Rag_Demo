#!/usr/bin/env python3
"""
Sample Tables Script

Queries two BigQuery tables and saves the first 100 rows from each as CSV files.

Usage:
    python sql_improvement/sample_tables.py

To modify which tables to sample:
    Edit the TABLE_1 and TABLE_2 constants below with your desired table paths.

Output:
    Creates CSV files in the sql_improvement/ folder with simple table names.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_improvement.bigquery_client import BigQueryClient


# ============================================================================
# CONFIGURATION: Modify these constants to change which tables to sample
# ============================================================================

TABLE_1 = "bigquery-public-data.thelook_ecommerce.users"
TABLE_2 = "bigquery-public-data.thelook_ecommerce.orders"

# BigQuery project ID (modify if needed)
PROJECT_ID = "brainrot-453319"

# Number of rows to sample per table
LIMIT = 100

# Output directory (same folder as this script)
OUTPUT_DIR = SCRIPT_DIR


# ============================================================================
# Main Script Logic
# ============================================================================

def extract_table_name(full_path: str) -> str:
    """
    Extract simple table name from full BigQuery path.

    Example:
        'bigquery-public-data.thelook_ecommerce.users' -> 'users'
    """
    return full_path.split('.')[-1]


def sample_and_save_table(client: BigQueryClient, table_path: str, output_dir: Path) -> None:
    """
    Query a table and save the first LIMIT rows as a CSV file.

    Args:
        client: Initialized BigQueryClient
        table_path: Full BigQuery table path (e.g., 'project.dataset.table')
        output_dir: Directory to save CSV file
    """
    table_name = extract_table_name(table_path)
    output_file = output_dir / f"{table_name}.csv"

    print(f"\n{'='*60}")
    print(f"Processing table: {table_path}")
    print(f"{'='*60}")

    # Build query
    query = f"SELECT * FROM `{table_path}` LIMIT {LIMIT}"
    print(f"Query: {query}")

    try:
        # Execute query
        print("Executing query...")
        df = client.query_df(query, timeout=60)

        # Save to CSV
        print(f"Saving to: {output_file}")
        df.to_csv(output_file, index=False)

        # Report results
        file_size_kb = output_file.stat().st_size / 1024
        print(f"✓ Success!")
        print(f"  - Rows: {len(df)}")
        print(f"  - Columns: {len(df.columns)}")
        print(f"  - File size: {file_size_kb:.2f} KB")
        print(f"  - Saved to: {output_file}")

    except Exception as e:
        print(f"✗ Error processing table {table_path}:")
        print(f"  {str(e)}")
        raise


def main():
    """Main execution function."""
    print("BigQuery Table Sampler")
    print("=" * 60)
    print(f"Project ID: {PROJECT_ID}")
    print(f"Sample size: {LIMIT} rows per table")
    print(f"Output directory: {OUTPUT_DIR}")

    # Initialize BigQuery client
    try:
        print("\nInitializing BigQuery client...")
        client = BigQueryClient(project_id=PROJECT_ID)
        print("✓ Client initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize BigQuery client: {e}")
        print("\nMake sure you have:")
        print("  1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable, OR")
        print("  2. Run: gcloud auth application-default login")
        sys.exit(1)

    # Process each table
    tables = [TABLE_1, TABLE_2]
    successful = 0
    failed = 0

    for table in tables:
        try:
            sample_and_save_table(client, table, OUTPUT_DIR)
            successful += 1
        except Exception:
            failed += 1
            continue

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total tables processed: {len(tables)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\n⚠ Some tables failed to process. Check errors above.")
        sys.exit(1)
    else:
        print("\n✓ All tables processed successfully!")


if __name__ == "__main__":
    main()
