#!/usr/bin/env python3
"""
CSV Pre-processor for Query Catalog Performance Optimization

This script pre-processes your CSV file to add parsed tables and joins columns,
eliminating the need for real-time parsing in the Streamlit app and dramatically
improving query card display performance.

Usage:
    python preprocess_csv.py --input "your_original.csv" --output "enhanced_queries.csv"
    python preprocess_csv.py --input "data.csv" --output "optimized_data.csv" --format parquet

Features:
- Pre-parses tables and joins columns using the same logic as app_simple_gemini.py
- Adds tables_parsed and joins_parsed columns for instant loading
- Supports both CSV and Parquet output formats
- Maintains backward compatibility with original data
- Provides detailed processing statistics
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_tables_column(tables_value: str) -> List[str]:
    """
    Parse tables column using ast.literal_eval approach for consistency with joins parsing
    Based on the proven logic from extract_joins_from_csv.py
    """
    if not tables_value or tables_value.strip() == '':
        return []
    
    # If already a list, return cleaned version
    if isinstance(tables_value, list):
        clean_tables = []
        for table in tables_value:
            clean_table = str(table).strip()
            # Remove all backticks and quotes
            clean_table = clean_table.replace('`', '').replace('"', '').replace("'", '')
            # Handle BigQuery format: project.dataset.table -> table
            if '.' in clean_table:
                table_parts = clean_table.split('.')
                clean_table = table_parts[-1]  # Take last part (table name)
            
            if clean_table:
                clean_tables.append(clean_table)
        return clean_tables
    
    # If string, try to use ast.literal_eval
    if isinstance(tables_value, str):
        try:
            import ast
            parsed_tables = ast.literal_eval(tables_value)
            if isinstance(parsed_tables, list):
                clean_tables = []
                for table in parsed_tables:
                    clean_table = str(table).strip()
                    # Remove all backticks and quotes
                    clean_table = clean_table.replace('`', '').replace('"', '').replace("'", '')
                    # Handle BigQuery format: project.dataset.table -> table
                    if '.' in clean_table:
                        table_parts = clean_table.split('.')
                        clean_table = table_parts[-1]  # Take last part (table name)
                    
                    if clean_table:
                        clean_tables.append(clean_table)
                return clean_tables
        except Exception as e:
            logger.warning(f"Failed to parse tables column with ast.literal_eval: {e}")
            # Fall back to simple string parsing
            pass
    
    # Simple string format parsing as fallback
    try:
        tables_str = str(tables_value).strip()
        if ',' in tables_str:
            # Multiple tables separated by comma
            tables = [t.strip() for t in tables_str.split(',')]
        else:
            # Single table
            tables = [tables_str.strip()]
        
        # Clean table names (remove BigQuery prefixes and quotes)
        clean_tables = []
        for table in tables:
            if table and table != '':
                # Remove all backticks and quotes
                table = table.replace('`', '').replace('"', '').replace("'", '')
                # Handle BigQuery format: project.dataset.table -> table
                if '.' in table:
                    table_parts = table.split('.')
                    table = table_parts[-1]
                clean_tables.append(table)
        
        return clean_tables
    except Exception as e:
        logger.warning(f"Failed to parse tables column '{tables_value}': {e}")
        return []

def parse_joins_column(joins_value: str) -> List[Dict[str, Any]]:
    """
    Parse joins column using ast.literal_eval approach that works reliably
    Based on the proven logic from extract_joins_from_csv.py
    
    Returns:
        List of dictionaries with join information (empty list if no joins)
    """
    if not joins_value or joins_value.strip() == '':
        return []
    
    def clean_table_name(table_name: str) -> str:
        """Clean and extract table name from BigQuery format"""
        clean_name = str(table_name).strip('`"\'')
        # Handle BigQuery format: project.dataset.table -> table
        if '.' in clean_name:
            clean_name = clean_name.split('.')[-1]
        return clean_name
    
    def process_single_join(join_obj: Dict) -> Dict[str, Any]:
        """Process a single join object"""
        left_table = clean_table_name(join_obj.get('left_table', ''))
        right_table = clean_table_name(join_obj.get('right_table', ''))
        left_column = str(join_obj.get('left_column', '')).strip()
        right_column = str(join_obj.get('right_column', '')).strip()
        join_type = str(join_obj.get('join_type', 'JOIN')).strip()
        transformation = str(join_obj.get('transformation', '')).strip()
        
        # Build condition
        if transformation:
            condition = transformation
        elif left_column and right_column:
            condition = f"{left_table}.{left_column} = {right_table}.{right_column}"
        else:
            condition = f"{left_table} ↔ {right_table}"
        
        return {
            'left_table': left_table,
            'right_table': right_table,
            'left_column': left_column,
            'right_column': right_column,
            'join_type': join_type,
            'transformation': transformation,
            'condition': condition,
            'format': 'json'
        }
    
    # First, try to parse as a list (already parsed)
    if isinstance(joins_value, list):
        join_list = []
        for join_obj in joins_value:
            if isinstance(join_obj, dict):
                try:
                    processed_join = process_single_join(join_obj)
                    join_list.append(processed_join)
                except Exception as e:
                    logger.warning(f"Failed to process join object: {e}")
                    continue
        return join_list
    
    # If string, try to use ast.literal_eval (more robust than json.loads)
    if isinstance(joins_value, str):
        try:
            import ast
            parsed_joins = ast.literal_eval(joins_value)
            if isinstance(parsed_joins, list):
                join_list = []
                for join_obj in parsed_joins:
                    if isinstance(join_obj, dict):
                        try:
                            processed_join = process_single_join(join_obj)
                            join_list.append(processed_join)
                        except Exception as e:
                            logger.warning(f"Failed to process join object: {e}")
                            continue
                return join_list
            elif isinstance(parsed_joins, dict):
                # Single join object
                try:
                    processed_join = process_single_join(parsed_joins)
                    return [processed_join]
                except Exception as e:
                    logger.warning(f"Failed to process single join object: {e}")
                    return []
        except Exception as e:
            logger.warning(f"Failed to parse joins column with ast.literal_eval: {e}")
            return []
    
    return []

def safe_get_value(row, column: str, default: str = '') -> str:
    """Safely get value from dataframe row, handling missing/empty values"""
    try:
        value = row.get(column, default)
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    except:
        return default

def preprocess_csv(input_path: str, output_path: str, output_format: str = 'csv') -> bool:
    """
    Pre-process CSV file to add parsed tables and joins columns
    
    Args:
        input_path: Path to input CSV file
        output_path: Path to output file
        output_format: Output format ('csv' or 'parquet')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load input CSV
        logger.info(f"Loading CSV from: {input_path}")
        df = pd.read_csv(input_path)
        logger.info(f"Loaded {len(df)} rows")
        
        # Validate required columns
        required_columns = ['query']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return False
        
        # Fill NaN values with empty strings for safe processing
        df = df.fillna('')
        
        # Check for expected columns
        tables_col = 'tables' if 'tables' in df.columns else 'table'
        joins_col = 'joins' if 'joins' in df.columns else None
        
        logger.info(f"Using columns: tables='{tables_col}', joins='{joins_col}'")
        
        # Process each row
        logger.info("Pre-processing tables and joins columns...")
        start_time = time.time()
        
        tables_parsed_list = []
        joins_parsed_list = []
        
        for idx, row in df.iterrows():
            # Parse tables
            tables_raw = safe_get_value(row, tables_col)
            tables_list = parse_tables_column(tables_raw)
            tables_parsed_list.append(tables_list)
            
            # Parse joins
            if joins_col and joins_col in row:
                joins_raw = safe_get_value(row, joins_col)
                joins_list = parse_joins_column(joins_raw)
                joins_parsed_list.append(joins_list)
            else:
                joins_parsed_list.append([])
        
        # Add parsed columns to dataframe
        df['tables_parsed'] = tables_parsed_list
        df['joins_parsed'] = joins_parsed_list
        
        processing_time = time.time() - start_time
        logger.info(f"Parsing completed in {processing_time:.2f}s")
        
        # Generate statistics
        total_queries = len(df)
        queries_with_tables = sum(1 for tables in tables_parsed_list if tables)
        queries_with_joins = sum(1 for joins in joins_parsed_list if joins)
        total_individual_joins = sum(len(joins) for joins in joins_parsed_list)
        
        logger.info(f"Statistics:")
        logger.info(f"  Total queries: {total_queries}")
        logger.info(f"  Queries with tables: {queries_with_tables}")
        logger.info(f"  Queries with joins: {queries_with_joins}")
        logger.info(f"  Total individual joins: {total_individual_joins}")
        
        # Save output file
        logger.info(f"Saving enhanced data to: {output_path}")
        
        if output_format.lower() == 'parquet':
            # Convert lists to JSON strings for Parquet compatibility
            df_export = df.copy()
            df_export['tables_parsed'] = df_export['tables_parsed'].apply(json.dumps)
            df_export['joins_parsed'] = df_export['joins_parsed'].apply(json.dumps)
            
            try:
                import pyarrow.parquet as pq
                df_export.to_parquet(output_path, index=False)
                logger.info("✅ Saved as Parquet file")
            except ImportError:
                logger.error("PyArrow not available. Install with: pip install pyarrow")
                return False
        else:
            # Save as CSV with JSON strings
            df_export = df.copy()
            df_export['tables_parsed'] = df_export['tables_parsed'].apply(json.dumps)
            df_export['joins_parsed'] = df_export['joins_parsed'].apply(json.dumps)
            df_export.to_csv(output_path, index=False)
            logger.info("✅ Saved as CSV file")
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 PRE-PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"📁 Input File: {input_path}")
        print(f"📁 Output File: {output_path}")
        print(f"📈 Total Queries: {total_queries:,}")
        print(f"📋 Queries with Tables: {queries_with_tables:,}")
        print(f"🔗 Queries with Joins: {queries_with_joins:,}")
        print(f"⚡ Processing Time: {processing_time:.2f}s")
        print(f"✅ Ready for app_simple_gemini.py!")
        print(f"\n💡 Update CSV_PATH in app_simple_gemini.py to point to: {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Pre-processing failed: {e}")
        return False

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Pre-process CSV for Query Catalog performance optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python preprocess_csv.py --input "queries.csv" --output "enhanced_queries.csv"
  
  # Output as Parquet for better performance
  python preprocess_csv.py --input "data.csv" --output "optimized_data.parquet" --format parquet
  
  # Process large dataset
  python preprocess_csv.py --input "large_queries.csv" --output "processed_large.parquet" --format parquet

Performance Notes:
  - Parquet format provides faster loading times for large datasets
  - Enhanced CSV eliminates real-time parsing in the Streamlit app
  - Backward compatible - app falls back to parsing if enhanced columns missing
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Path to input CSV file'
    )
    
    parser.add_argument(
        '--output', '-o', 
        required=True,
        help='Path to output file'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'parquet'],
        default='csv',
        help='Output format (default: csv)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input file not found: {args.input}")
        return 1
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("🔥 CSV Pre-processor for Query Catalog")
    print("="*50)
    print(f"📄 Input: {args.input}")
    print(f"📄 Output: {args.output}")
    print(f"📋 Format: {args.format}")
    print("")
    
    # Process the file
    success = preprocess_csv(args.input, args.output, args.format)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())