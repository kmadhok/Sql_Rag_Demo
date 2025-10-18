#!/usr/bin/env python3
"""
Master Join Analysis Script

Orchestrates complete join discovery workflow:
1. Load schema and extract unique tables
2. Sample 1000 rows from each table (with CSV reuse)
3. Find join candidates for all pairwise table combinations
4. Validate joins using BigQuery to determine cardinality
5. Output aggregated results with validation status

Usage:
    python master_join_analysis.py
    python master_join_analysis.py --schema ../data_new/thelook_ecommerce_schema.csv --sample-limit 1000
"""

import argparse
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from itertools import combinations

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sql_improvement.bigquery_client import BigQueryClient
from sql_improvement.join_infer import find_join_candidates


# ============================================================================
# Phase 1: Schema Loading
# ============================================================================

def load_schema_mapping(schema_path: Path) -> Dict[str, str]:
    """
    Load schema CSV and extract table mappings.

    Args:
        schema_path: Path to schema CSV with columns: full_table_name, table, column, column_data_type

    Returns:
        Dictionary mapping short table name to full BigQuery table name
        Example: {"users": "bigquery-public-data.thelook_ecommerce.users"}
    """
    print(f"\n{'='*80}")
    print("PHASE 1: LOADING SCHEMA")
    print(f"{'='*80}\n")

    print(f"Reading schema from: {schema_path}")
    schema_df = pd.read_csv(schema_path)

    # Create mapping: short table name -> full table name
    table_mapping = {}
    for _, row in schema_df.iterrows():
        short_name = row['table']
        full_name = row['full_table_name']
        if short_name not in table_mapping:
            table_mapping[short_name] = full_name

    print(f"Found {len(table_mapping)} unique tables:")
    for i, (short, full) in enumerate(sorted(table_mapping.items()), 1):
        print(f"  {i}. {short} → {full}")

    return table_mapping


# ============================================================================
# Phase 2: Table Sampling
# ============================================================================

def sample_tables(
    table_mapping: Dict[str, str],
    output_dir: Path,
    client: BigQueryClient,
    sample_limit: int = 1000,
    timeout: int = 60
) -> Dict[str, Path]:
    """
    Sample rows from each table and save to CSV (with reuse logic).

    Args:
        table_mapping: Dictionary mapping table name to full BigQuery path
        output_dir: Directory to save sampled CSV files
        client: Initialized BigQueryClient
        sample_limit: Number of rows to sample per table
        timeout: Query timeout in seconds

    Returns:
        Dictionary mapping table name to CSV file path
    """
    print(f"\n{'='*80}")
    print("PHASE 2: TABLE SAMPLING")
    print(f"{'='*80}\n")

    # Create output directory
    sampled_dir = output_dir / "sampled_tables"
    sampled_dir.mkdir(exist_ok=True, parents=True)
    print(f"Output directory: {sampled_dir}\n")

    csv_paths = {}
    total_tables = len(table_mapping)

    for idx, (table_name, full_table_path) in enumerate(sorted(table_mapping.items()), 1):
        output_csv = sampled_dir / f"{table_name}.csv"

        print(f"[{idx}/{total_tables}] Table: {table_name}")

        # Check if CSV already exists (reuse logic)
        if output_csv.exists():
            print(f"  ✓ CSV exists, reusing: {output_csv}")
            csv_paths[table_name] = output_csv
            continue

        # Sample table from BigQuery
        print(f"  Querying: {full_table_path}")
        query = f"SELECT * FROM `{full_table_path}` LIMIT {sample_limit}"

        try:
            df = client.query_df(query, timeout=timeout)
            df.to_csv(output_csv, index=False)

            file_size_kb = output_csv.stat().st_size / 1024
            print(f"  ✓ Saved {len(df)} rows, {len(df.columns)} columns ({file_size_kb:.2f} KB)")
            print(f"  → {output_csv}")

            csv_paths[table_name] = output_csv

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    print(f"\nSuccessfully sampled {len(csv_paths)}/{total_tables} tables")
    return csv_paths


# ============================================================================
# Phase 3: Join Candidate Discovery
# ============================================================================

def discover_join_candidates(
    csv_paths: Dict[str, Path],
    use_embeddings: bool = False,
    filter_non_keys: bool = True
) -> pd.DataFrame:
    """
    Find join candidates for all pairwise table combinations.

    Args:
        csv_paths: Dictionary mapping table name to CSV file path
        use_embeddings: Whether to use semantic embeddings
        filter_non_keys: Whether to filter out non-key columns

    Returns:
        Aggregated DataFrame with all join candidates
    """
    print(f"\n{'='*80}")
    print("PHASE 3: JOIN CANDIDATE DISCOVERY")
    print(f"{'='*80}\n")

    # Generate all pairwise combinations
    table_names = sorted(csv_paths.keys())
    table_pairs = list(combinations(table_names, 2))

    print(f"Tables: {len(table_names)}")
    print(f"Pairwise combinations: {len(table_pairs)}\n")

    all_candidates = []

    for idx, (left_table, right_table) in enumerate(table_pairs, 1):
        print(f"[{idx}/{len(table_pairs)}] Analyzing: {left_table} ↔ {right_table}")

        # Load CSVs
        try:
            df_left = pd.read_csv(csv_paths[left_table])
            df_right = pd.read_csv(csv_paths[right_table])
        except Exception as e:
            print(f"  ✗ Error loading CSVs: {e}")
            continue

        # Find join candidates
        try:
            candidates = find_join_candidates(
                df_left=df_left,
                df_right=df_right,
                left_name=left_table,
                right_name=right_table,
                use_embeddings=use_embeddings,
                filter_non_keys=filter_non_keys
            )

            if len(candidates) > 0:
                print(f"  ✓ Found {len(candidates)} candidate(s)")
                # Show top candidate
                top = candidates.iloc[0]
                print(f"    Top: {top['left_col']} ↔ {top['right_col']} (confidence: {top['confidence']:.3f})")
                all_candidates.append(candidates)
            else:
                print(f"  - No candidates found")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    # Aggregate all results
    if len(all_candidates) == 0:
        print("\n⚠ No join candidates found across any table pairs")
        return pd.DataFrame()

    aggregated_df = pd.concat(all_candidates, ignore_index=True)
    print(f"\n✓ Total join candidates discovered: {len(aggregated_df)}")

    return aggregated_df


# ============================================================================
# Phase 4: Join Validation
# ============================================================================

def validate_join_candidates(
    candidates_df: pd.DataFrame,
    table_mapping: Dict[str, str],
    client: BigQueryClient,
    timeout: int = 30
) -> pd.DataFrame:
    """
    Validate join candidates by executing BigQuery joins.

    Args:
        candidates_df: DataFrame with join candidates
        table_mapping: Dictionary mapping table name to full BigQuery path
        client: BigQueryClient instance
        timeout: Query timeout in seconds

    Returns:
        DataFrame with validation results added
    """
    print(f"\n{'='*80}")
    print("PHASE 4: JOIN VALIDATION")
    print(f"{'='*80}\n")

    if len(candidates_df) == 0:
        print("⚠ No candidates to validate")
        return candidates_df

    print(f"Validating {len(candidates_df)} join candidate(s)\n")

    # Add validation columns
    candidates_df['left_full_table_name'] = None
    candidates_df['right_full_table_name'] = None
    candidates_df['left_distinct_count'] = None
    candidates_df['right_distinct_count'] = None
    candidates_df['total_joined_rows'] = None
    candidates_df['cardinality_type'] = None
    candidates_df['validation_status'] = None
    candidates_df['error_message'] = None

    for idx, row in candidates_df.iterrows():
        left_table = row['left_table']
        right_table = row['right_table']
        left_col = row['left_col']
        right_col = row['right_col']

        print(f"[{idx+1}/{len(candidates_df)}] {left_table}.{left_col} → {right_table}.{right_col}")

        # Map to full table names
        if left_table not in table_mapping:
            error_msg = f"Table '{left_table}' not found in schema"
            print(f"  ✗ {error_msg}")
            candidates_df.at[idx, 'validation_status'] = 'error'
            candidates_df.at[idx, 'error_message'] = error_msg
            continue

        if right_table not in table_mapping:
            error_msg = f"Table '{right_table}' not found in schema"
            print(f"  ✗ {error_msg}")
            candidates_df.at[idx, 'validation_status'] = 'error'
            candidates_df.at[idx, 'error_message'] = error_msg
            continue

        left_table_full = table_mapping[left_table]
        right_table_full = table_mapping[right_table]

        # Store full table names
        candidates_df.at[idx, 'left_full_table_name'] = left_table_full
        candidates_df.at[idx, 'right_full_table_name'] = right_table_full

        # Construct validation SQL
        sql = f"""
        SELECT
            COUNT(DISTINCT left_table.{left_col}) as left_distinct,
            COUNT(DISTINCT right_table.{right_col}) as right_distinct,
            COUNT(*) as total_joined_rows
        FROM `{left_table_full}` AS left_table
        FULL OUTER JOIN `{right_table_full}` AS right_table
            ON left_table.{left_col} = right_table.{right_col}
        """

        try:
            # Execute validation query
            result_df = client.query_df(sql, timeout=timeout)

            if result_df.empty:
                candidates_df.at[idx, 'total_joined_rows'] = 0
                candidates_df.at[idx, 'cardinality_type'] = 'no-join-rows'
                candidates_df.at[idx, 'validation_status'] = 'success'
                print(f"  ⚠ No rows returned from join")
                continue

            # Extract results
            result_row = result_df.iloc[0]
            left_distinct = int(result_row['left_distinct'])
            right_distinct = int(result_row['right_distinct'])
            total_rows = int(result_row['total_joined_rows'])

            # Determine cardinality
            cardinality = _determine_cardinality(left_distinct, right_distinct, total_rows)

            # Store results
            candidates_df.at[idx, 'left_distinct_count'] = left_distinct
            candidates_df.at[idx, 'right_distinct_count'] = right_distinct
            candidates_df.at[idx, 'total_joined_rows'] = total_rows
            candidates_df.at[idx, 'cardinality_type'] = cardinality
            candidates_df.at[idx, 'validation_status'] = 'success'

            print(f"  ✓ Cardinality: {cardinality} | Rows: {total_rows:,}")

        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Error: {error_msg[:100]}")
            candidates_df.at[idx, 'validation_status'] = 'error'
            candidates_df.at[idx, 'error_message'] = error_msg

    # Summary
    successful = (candidates_df['validation_status'] == 'success').sum()
    failed = (candidates_df['validation_status'] == 'error').sum()
    print(f"\n✓ Validation complete: {successful} successful, {failed} failed")

    return candidates_df


def _determine_cardinality(left_distinct: int, right_distinct: int, total_rows: int) -> str:
    """
    Determine join cardinality type based on distinct counts.

    Args:
        left_distinct: Count of distinct values in left column
        right_distinct: Count of distinct values in right column
        total_rows: Total number of rows returned by join

    Returns:
        Cardinality type: "1-to-1", "1-to-many", "many-to-1", "many-to-many"
    """
    if total_rows == 0:
        return "no-join-rows"

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


# ============================================================================
# Phase 5: Output & Reporting
# ============================================================================

def save_results(
    results_df: pd.DataFrame,
    output_path: Path
) -> None:
    """
    Save aggregated results and print summary statistics.

    Args:
        results_df: DataFrame with all join candidates and validation results
        output_path: Path to save CSV file
    """
    print(f"\n{'='*80}")
    print("PHASE 5: OUTPUT & REPORTING")
    print(f"{'='*80}\n")

    if len(results_df) == 0:
        print("⚠ No results to save")
        return

    # Save to CSV
    results_df.to_csv(output_path, index=False)
    file_size_kb = output_path.stat().st_size / 1024
    print(f"✓ Results saved to: {output_path}")
    print(f"  File size: {file_size_kb:.2f} KB")
    print(f"  Total rows: {len(results_df)}")

    # Print summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}\n")

    print(f"Total join candidates: {len(results_df)}")

    if 'validation_status' in results_df.columns:
        successful = (results_df['validation_status'] == 'success').sum()
        failed = (results_df['validation_status'] == 'error').sum()
        print(f"Validation successful: {successful}")
        print(f"Validation failed: {failed}")

    if 'cardinality_type' in results_df.columns:
        valid_results = results_df[results_df['validation_status'] == 'success']
        if len(valid_results) > 0:
            print(f"\nCardinality breakdown:")
            cardinality_counts = valid_results['cardinality_type'].value_counts()
            for card_type, count in cardinality_counts.items():
                print(f"  {card_type}: {count}")

    # Show top 5 candidates by confidence
    print(f"\nTop 5 join candidates by confidence:")
    print("=" * 100)
    top_5 = results_df.nlargest(5, 'confidence')
    for i, (idx, row) in enumerate(top_5.iterrows(), 1):
        print(f"\n{i}. {row['left_table']}.{row['left_col']} ↔ {row['right_table']}.{row['right_col']}")
        print(f"   Confidence: {row['confidence']:.3f}")
        if 'cardinality_type' in row and pd.notna(row['cardinality_type']):
            print(f"   Cardinality: {row['cardinality_type']}")
        if 'total_joined_rows' in row and pd.notna(row['total_joined_rows']):
            print(f"   Total rows: {int(row['total_joined_rows']):,}")


# ============================================================================
# Main Orchestration
# ============================================================================

def main():
    """Main entry point for master join analysis workflow."""
    parser = argparse.ArgumentParser(
        description="Master join analysis workflow: sample tables, discover joins, validate cardinality"
    )

    parser.add_argument(
        '--schema',
        type=Path,
        default=Path('../data_new/thelook_ecommerce_schema.csv'),
        help='Path to schema CSV (default: ../data_new/thelook_ecommerce_schema.csv)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('.'),
        help='Output directory for results (default: current directory)'
    )

    parser.add_argument(
        '--project-id',
        type=str,
        default='brainrot-453319',
        help='Google Cloud project ID (default: brainrot-453319)'
    )

    parser.add_argument(
        '--sample-limit',
        type=int,
        default=1000,
        help='Number of rows to sample per table (default: 1000)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='BigQuery query timeout in seconds (default: 30)'
    )

    parser.add_argument(
        '--use-embeddings',
        action='store_true',
        help='Enable semantic similarity using embeddings (requires sentence-transformers)'
    )

    parser.add_argument(
        '--include-all-columns',
        action='store_true',
        help='Include all columns (disable join key filtering)'
    )

    args = parser.parse_args()

    # Validate schema file exists
    if not args.schema.exists():
        print(f"✗ Error: Schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)

    print("="*80)
    print("MASTER JOIN ANALYSIS WORKFLOW")
    print("="*80)
    print(f"Schema: {args.schema}")
    print(f"Output directory: {args.output_dir}")
    print(f"Project ID: {args.project_id}")
    print(f"Sample limit: {args.sample_limit} rows/table")
    print(f"Timeout: {args.timeout}s")

    # Initialize BigQuery client
    try:
        print("\nInitializing BigQuery client...")
        client = BigQueryClient(project_id=args.project_id)
        print("✓ BigQuery client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize BigQuery client: {e}", file=sys.stderr)
        print("\nMake sure you have:")
        print("  1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable, OR")
        print("  2. Run: gcloud auth application-default login")
        sys.exit(1)

    try:
        # Phase 1: Load schema
        table_mapping = load_schema_mapping(args.schema)

        # Phase 2: Sample tables
        csv_paths = sample_tables(
            table_mapping=table_mapping,
            output_dir=args.output_dir,
            client=client,
            sample_limit=args.sample_limit,
            timeout=args.timeout
        )

        if len(csv_paths) == 0:
            print("\n✗ No tables were successfully sampled. Exiting.")
            sys.exit(1)

        # Phase 3: Discover join candidates
        candidates_df = discover_join_candidates(
            csv_paths=csv_paths,
            use_embeddings=args.use_embeddings,
            filter_non_keys=not args.include_all_columns
        )

        if len(candidates_df) == 0:
            print("\n⚠ No join candidates discovered. Skipping validation.")
            sys.exit(0)

        # Phase 4: Validate joins
        validated_df = validate_join_candidates(
            candidates_df=candidates_df,
            table_mapping=table_mapping,
            client=client,
            timeout=args.timeout
        )

        # Phase 5: Save results
        output_path = args.output_dir / "join_analysis_results.csv"
        save_results(validated_df, output_path)

        print("\n" + "="*80)
        print("✓ WORKFLOW COMPLETE")
        print("="*80)

    except KeyboardInterrupt:
        print("\n\n⚠ Workflow interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
