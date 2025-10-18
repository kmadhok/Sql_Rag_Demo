#!/usr/bin/env python3
"""
Join Cardinality Validation Script

Validates join relationships from join_results_improved.csv by:
1. Executing actual BigQuery joins
2. Counting distinct values on both sides
3. Determining cardinality type (1-1, 1-many, many-1, many-many)
4. Saving validation results to CSV

Usage:
    python validate_join_cardinality.py
    python validate_join_cardinality.py --input join_results_improved.csv --output validation_results.csv
"""

import argparse
import pandas as pd
from pathlib import Path
import sys
from typing import Dict, Tuple, Optional
from bigquery_client import BigQueryClient


def load_schema_mapping(schema_path: Path) -> Dict[str, str]:
    """
    Load table name mapping from schema CSV.

    Args:
        schema_path: Path to schema CSV with columns: full_table_name, table, column, column_data_type

    Returns:
        Dictionary mapping short table name to full BigQuery table name
        Example: {"orders": "bigquery-public-data.thelook_ecommerce.orders"}
    """
    print(f"Loading schema from: {schema_path}")
    schema_df = pd.read_csv(schema_path)

    # Create mapping: short table name -> full table name
    table_mapping = {}
    for _, row in schema_df.iterrows():
        short_name = row['table']
        full_name = row['full_table_name']
        if short_name not in table_mapping:
            table_mapping[short_name] = full_name

    print(f"Loaded {len(table_mapping)} table mappings")
    return table_mapping


def determine_cardinality(
    left_distinct: int,
    right_distinct: int,
    total_rows: int
) -> str:
    """
    Determine join cardinality type based on distinct counts.

    Args:
        left_distinct: Count of distinct values in left column
        right_distinct: Count of distinct values in right column
        total_rows: Total number of rows returned by join

    Returns:
        Cardinality type: "1-to-1", "1-to-many", "many-to-1", "many-to-many"

    Logic:
        - 1-to-1: Both sides have same distinct count as total rows
        - 1-to-many: Left side distinct count equals total rows, right side has fewer
        - many-to-1: Right side distinct count equals total rows, left side has fewer
        - many-to-many: Both sides have fewer distinct counts than total rows
    """
    if total_rows == 0:
        return "no-join-rows"

    # Check if each side has unique values (no duplicates in join result)
    left_is_unique = (left_distinct == total_rows)
    right_is_unique = (right_distinct == total_rows)

    if left_is_unique and right_is_unique:
        return "1-to-1"
    elif left_is_unique and not right_is_unique:
        return "1-to-many"
    elif not left_is_unique and right_is_unique:
        return "many-to-1"
    else:
        return "many-to-many"


def validate_single_join(
    client: BigQueryClient,
    left_table_full: str,
    right_table_full: str,
    left_col: str,
    right_col: str,
    timeout: int = 30
) -> Tuple[Optional[int], Optional[int], Optional[int], str, Optional[str]]:
    """
    Validate a single join by executing BigQuery query.

    Args:
        client: BigQuery client instance
        left_table_full: Full BigQuery table name for left table
        right_table_full: Full BigQuery table name for right table
        left_col: Column name in left table
        right_col: Column name in right table
        timeout: Query timeout in seconds

    Returns:
        Tuple of (left_distinct, right_distinct, total_rows, cardinality_type, error_msg)
    """
    # Construct SQL query
    sql = f"""
    SELECT
        COUNT(DISTINCT left_table.{left_col}) as left_distinct,
        COUNT(DISTINCT right_table.{right_col}) as right_distinct,
        COUNT(*) as total_joined_rows
    FROM `{left_table_full}` AS left_table
    JOIN `{right_table_full}` AS right_table
        ON left_table.{left_col} = right_table.{right_col}
    """

    try:
        # Execute query
        result_df = client.query_df(sql, timeout=timeout)

        if result_df.empty:
            return None, None, 0, "no-join-rows", "Query returned empty result"

        # Extract results
        row = result_df.iloc[0]
        left_distinct = int(row['left_distinct'])
        right_distinct = int(row['right_distinct'])
        total_rows = int(row['total_joined_rows'])

        # Determine cardinality
        cardinality = determine_cardinality(left_distinct, right_distinct, total_rows)

        return left_distinct, right_distinct, total_rows, cardinality, None

    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ Error: {error_msg}")
        return None, None, None, "error", error_msg


def validate_joins(
    input_csv: Path,
    schema_csv: Path,
    output_csv: Path,
    project_id: str = "brainrot-453319",
    timeout: int = 30
) -> pd.DataFrame:
    """
    Validate all joins from input CSV and save results.

    Args:
        input_csv: Path to join_results_improved.csv
        schema_csv: Path to schema CSV with table mappings
        output_csv: Path to save validation results
        project_id: Google Cloud project ID
        timeout: Query timeout in seconds

    Returns:
        DataFrame with validation results
    """
    # Load inputs
    print(f"\n{'='*80}")
    print("JOIN CARDINALITY VALIDATION")
    print(f"{'='*80}\n")

    joins_df = pd.read_csv(input_csv)
    table_mapping = load_schema_mapping(schema_csv)

    print(f"\nLoaded {len(joins_df)} join candidates from: {input_csv}")

    # Initialize BigQuery client
    print(f"Initializing BigQuery client (project: {project_id})")
    client = BigQueryClient(project_id=project_id)

    # Add validation result columns
    joins_df['left_distinct_count'] = None
    joins_df['right_distinct_count'] = None
    joins_df['total_joined_rows'] = None
    joins_df['cardinality_type'] = None
    joins_df['validation_status'] = None
    joins_df['error_message'] = None

    # Process each join
    print(f"\n{'='*80}")
    print("VALIDATING JOINS")
    print(f"{'='*80}\n")

    for idx, row in joins_df.iterrows():
        left_table = row['left_table']
        right_table = row['right_table']
        left_col = row['left_col']
        right_col = row['right_col']

        print(f"[{idx+1}/{len(joins_df)}] Validating: {left_table}.{left_col} → {right_table}.{right_col}")

        # Map short names to full names
        if left_table not in table_mapping:
            error_msg = f"Table '{left_table}' not found in schema"
            print(f"  ❌ {error_msg}")
            joins_df.at[idx, 'validation_status'] = 'error'
            joins_df.at[idx, 'error_message'] = error_msg
            continue

        if right_table not in table_mapping:
            error_msg = f"Table '{right_table}' not found in schema"
            print(f"  ❌ {error_msg}")
            joins_df.at[idx, 'validation_status'] = 'error'
            joins_df.at[idx, 'error_message'] = error_msg
            continue

        left_table_full = table_mapping[left_table]
        right_table_full = table_mapping[right_table]

        print(f"  Left:  {left_table_full}")
        print(f"  Right: {right_table_full}")

        # Validate join
        left_distinct, right_distinct, total_rows, cardinality, error = validate_single_join(
            client=client,
            left_table_full=left_table_full,
            right_table_full=right_table_full,
            left_col=left_col,
            right_col=right_col,
            timeout=timeout
        )

        # Store results
        joins_df.at[idx, 'left_distinct_count'] = left_distinct
        joins_df.at[idx, 'right_distinct_count'] = right_distinct
        joins_df.at[idx, 'total_joined_rows'] = total_rows
        joins_df.at[idx, 'cardinality_type'] = cardinality
        joins_df.at[idx, 'validation_status'] = 'success' if error is None else 'error'
        joins_df.at[idx, 'error_message'] = error

        if error is None:
            print(f"  ✅ Cardinality: {cardinality}")
            print(f"     Left distinct: {left_distinct:,} | Right distinct: {right_distinct:,} | Total rows: {total_rows:,}")

        print()

    # Save results
    print(f"{'='*80}")
    print("SAVING RESULTS")
    print(f"{'='*80}\n")

    joins_df.to_csv(output_csv, index=False)
    print(f"✅ Validation results saved to: {output_csv}")

    # Print summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    total_joins = len(joins_df)
    successful = (joins_df['validation_status'] == 'success').sum()
    failed = (joins_df['validation_status'] == 'error').sum()

    print(f"Total joins analyzed: {total_joins}")
    print(f"Successful validations: {successful}")
    print(f"Failed validations: {failed}")

    if successful > 0:
        print(f"\nCardinality breakdown:")
        cardinality_counts = joins_df[joins_df['validation_status'] == 'success']['cardinality_type'].value_counts()
        for card_type, count in cardinality_counts.items():
            print(f"  {card_type}: {count}")

    return joins_df


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Validate join cardinality by executing BigQuery joins and analyzing distinct counts"
    )
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('join_results_improved.csv'),
        help='Path to input CSV with join candidates (default: join_results_improved.csv)'
    )
    parser.add_argument(
        '--schema',
        type=Path,
        default=Path('../data_new/thelook_ecommerce_schema.csv'),
        help='Path to schema CSV with table mappings (default: ../data_new/thelook_ecommerce_schema.csv)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('join_validation_results.csv'),
        help='Path to output CSV for validation results (default: join_validation_results.csv)'
    )
    parser.add_argument(
        '--project-id',
        type=str,
        default='brainrot-453319',
        help='Google Cloud project ID (default: brainrot-453319)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Query timeout in seconds (default: 30)'
    )

    args = parser.parse_args()

    # Validate input files exist
    if not args.input.exists():
        print(f"❌ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.schema.exists():
        print(f"❌ Error: Schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)

    # Run validation
    try:
        validate_joins(
            input_csv=args.input,
            schema_csv=args.schema,
            output_csv=args.output,
            project_id=args.project_id,
            timeout=args.timeout
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
