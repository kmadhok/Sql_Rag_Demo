#!/usr/bin/env python3
"""
CLI tool for finding joinable columns between two CSV files.

Usage:
    python find_join_candidates.py --left-csv orders.csv --right-csv users.csv \
        --left-name orders --right-name users --use-embeddings

Example:
    python find_join_candidates.py \
        --left-csv /path/to/orders.csv \
        --right-csv /path/to/users.csv \
        --left-name orders \
        --right-name users
"""

import argparse
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from join_infer import find_join_candidates


def main():
    parser = argparse.ArgumentParser(
        description="Find joinable column pairs between two CSV files using NLP + statistical analysis."
    )

    parser.add_argument(
        '--left-csv',
        type=str,
        required=True,
        help='Path to left CSV file'
    )

    parser.add_argument(
        '--right-csv',
        type=str,
        required=True,
        help='Path to right CSV file'
    )

    parser.add_argument(
        '--left-name',
        type=str,
        default='left',
        help='Name of left table (for FK pattern detection)'
    )

    parser.add_argument(
        '--right-name',
        type=str,
        default='right',
        help='Name of right table (for FK pattern detection)'
    )

    parser.add_argument(
        '--use-embeddings',
        action='store_true',
        help='Enable semantic similarity using embeddings (requires sentence-transformers)'
    )

    parser.add_argument(
        '--include-all-columns',
        action='store_true',
        help='Include all columns (disable join key filtering). By default, filters out non-key columns like gender, created_at, etc.'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='join_candidates.csv',
        help='Output CSV file path (default: join_candidates.csv)'
    )

    parser.add_argument(
        '--max-rows',
        type=int,
        default=100,
        help='Maximum rows to sample from each CSV (default: 100)'
    )

    args = parser.parse_args()

    # Validate input files
    left_path = Path(args.left_csv)
    right_path = Path(args.right_csv)

    if not left_path.exists():
        print(f"Error: Left CSV file not found: {left_path}", file=sys.stderr)
        sys.exit(1)

    if not right_path.exists():
        print(f"Error: Right CSV file not found: {right_path}", file=sys.stderr)
        sys.exit(1)

    # Load CSVs
    print(f"Loading {left_path}...")
    try:
        df_left = pd.read_csv(left_path, nrows=args.max_rows)
        print(f"  Loaded {len(df_left)} rows, {len(df_left.columns)} columns")
    except Exception as e:
        print(f"Error loading left CSV: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {right_path}...")
    try:
        df_right = pd.read_csv(right_path, nrows=args.max_rows)
        print(f"  Loaded {len(df_right)} rows, {len(df_right.columns)} columns")
    except Exception as e:
        print(f"Error loading right CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Run join inference
    print(f"\nAnalyzing join candidates between '{args.left_name}' and '{args.right_name}'...")
    if args.use_embeddings:
        print("  Using embeddings for semantic similarity (this may take a moment)...")
    if not args.include_all_columns:
        print("  Filtering out non-key columns (use --include-all-columns to disable)")

    try:
        candidates = find_join_candidates(
            df_left=df_left,
            df_right=df_right,
            left_name=args.left_name,
            right_name=args.right_name,
            use_embeddings=args.use_embeddings,
            filter_non_keys=not args.include_all_columns
        )
    except Exception as e:
        print(f"Error during join inference: {e}", file=sys.stderr)
        sys.exit(1)

    # Display results
    if len(candidates) == 0:
        print("\nNo compatible join candidates found.")
        print("Possible reasons:")
        print("  - No columns have compatible types")
        print("  - Column names and values are too dissimilar")
        sys.exit(0)

    print(f"\nFound {len(candidates)} join candidate(s):")
    print("\nTop 5 candidates:")
    print("=" * 100)

    # Display top 5 with formatting
    top_5 = candidates.head(5)
    for idx, row in top_5.iterrows():
        print(f"\n{idx + 1}. {row['left_table']}.{row['left_col']} ↔ {row['right_table']}.{row['right_col']}")
        print(f"   Confidence:         {row['confidence']:.3f}")
        print(f"   Name Similarity:    {row['name_sim']:.3f}")
        print(f"   Value Overlap:      {row['value_jaccard']:.3f}")
        print(f"   Cardinality Score:  {row['cardinality_score']:.3f}")
        print(f"   Key Pattern Score:  {row['key_pattern_score']:.3f}")
        print(f"   Uniqueness:         L={row['left_uniqueness']:.3f}, R={row['right_uniqueness']:.3f}")
        if args.use_embeddings:
            print(f"   Embedding Sim:      {row['embed_sim']:.3f}")
        if row['notes']:
            print(f"   Notes:              {row['notes']}")

    # Write to CSV
    output_path = Path(args.output)
    try:
        candidates.to_csv(output_path, index=False)
        print(f"\n{'=' * 100}")
        print(f"Full results written to: {output_path}")
        print(f"Total candidates: {len(candidates)}")
    except Exception as e:
        print(f"\nWarning: Could not write output CSV: {e}", file=sys.stderr)

    # Exit with success
    sys.exit(0)


if __name__ == '__main__':
    main()
