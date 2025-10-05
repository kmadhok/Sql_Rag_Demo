#!/usr/bin/env python3
"""
Transform enhanced CSV file to match standalone_embedding_generator.py requirements.

The embedding generator expects:
- Column named 'query' (required)
- Optional columns: 'description', 'tables', 'joins'
"""

import pandas as pd
import argparse
import sys
import json
from pathlib import Path

def transform_csv(input_file, output_file):
    """Transform enhanced CSV to match embedding generator format."""
    print(f"Reading {input_file}...")
    
    try:
        df = pd.read_csv(input_file)
        print(f"Loaded {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Create output dataframe with required columns
        output_df = pd.DataFrame()
        
        # Map query column (should already be named 'query' from description_generator)
        if 'query' in df.columns:
            output_df['query'] = df['query']
        elif 'Queries' in df.columns:
            output_df['query'] = df['Queries'] 
        else:
            print("Error: No 'query' or 'Queries' column found!")
            return False
            
        # Map other columns
        if 'description' in df.columns:
            output_df['description'] = df['description']
        
        # Handle tables - parse JSON string if needed
        if 'tables' in df.columns:
            output_df['table'] = df['tables'].apply(parse_tables_field)
        elif 'tables_parsed' in df.columns:
            output_df['table'] = df['tables_parsed'].apply(parse_tables_field)
        
        # Handle joins - parse JSON string if needed  
        if 'joins' in df.columns:
            output_df['joins'] = df['joins'].apply(parse_joins_field)
        elif 'joins_parsed' in df.columns:
            output_df['joins'] = df['joins_parsed'].apply(parse_joins_field)
        
        # Remove any rows with empty queries
        initial_count = len(output_df)
        output_df = output_df.dropna(subset=['query'])
        output_df = output_df[output_df['query'].str.strip() != '']
        final_count = len(output_df)
        
        if final_count < initial_count:
            print(f"Removed {initial_count - final_count} rows with empty queries")
        
        print(f"Writing {len(output_df)} rows to {output_file}...")
        output_df.to_csv(output_file, index=False)
        
        print("Transformation completed successfully!")
        print(f"Output columns: {list(output_df.columns)}")
        
        # Show sample
        if len(output_df) > 0:
            print(f"\nSample row:")
            print(f"Query: {output_df.iloc[0]['query'][:100]}...")
            if 'description' in output_df.columns:
                print(f"Description: {output_df.iloc[0]['description']}")
        
        return True
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

def parse_tables_field(tables_value):
    """Parse tables field - could be JSON string or plain text."""
    if pd.isna(tables_value):
        return ""
    
    if isinstance(tables_value, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(tables_value)
            if isinstance(parsed, list):
                return ", ".join(parsed)
            return str(parsed)
        except:
            # If not JSON, return as-is
            return tables_value
    
    return str(tables_value)

def parse_joins_field(joins_value):
    """Parse joins field - could be JSON string or plain text.""" 
    if pd.isna(joins_value):
        return ""
    
    if isinstance(joins_value, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(joins_value)
            if isinstance(parsed, list):
                # Format join information nicely
                join_strs = []
                for join in parsed:
                    if isinstance(join, dict):
                        left_table = join.get('left_table', '')
                        right_table = join.get('right_table', '')
                        join_type = join.get('join_type', 'JOIN')
                        join_strs.append(f"{left_table} {join_type} {right_table}")
                return "; ".join(join_strs)
            return str(parsed)
        except:
            # If not JSON, return as-is
            return joins_value
    
    return str(joins_value)

def main():
    parser = argparse.ArgumentParser(description='Transform enhanced CSV for embedding generator')
    parser.add_argument('input_file', help='Input enhanced CSV file')
    parser.add_argument('output_file', help='Output transformed CSV file')
    
    args = parser.parse_args()
    
    if not Path(args.input_file).exists():
        print(f"Error: Input file {args.input_file} does not exist")
        sys.exit(1)
    
    success = transform_csv(args.input_file, args.output_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()