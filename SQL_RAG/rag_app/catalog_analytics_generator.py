#!/usr/bin/env python3
"""
Query Catalog Analytics Pre-processor

Pre-computes and caches expensive analytics for the Query Catalog page to dramatically
improve Streamlit app performance. Processes join analysis, generates visualizations,
and optimizes DataFrames for fast loading.

Usage:
    python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv"
    python catalog_analytics_generator.py --csv "sample_queries_with_metadata.csv" --force-rebuild

Features:
- Pre-computes join analysis and statistics
- Generates static graph visualizations  
- Optimizes DataFrames with parquet storage
- Smart caching with modification time checking
- Background processing for large datasets
"""

import argparse
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd

# Optional dependencies with graceful degradation
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    print("⚠️ Graphviz not available - graph generation will be skipped")

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    print("⚠️ PyArrow not available - will use CSV instead of Parquet")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CACHE_DIR_NAME = "catalog_analytics"
GRAPH_FORMATS = ["svg", "png"]  # Generate multiple formats


def parse_tables_column(tables_value: str) -> List[str]:
    """
    Parse tables column using ast.literal_eval approach for consistency with joins parsing
    Based on the proven logic from preprocess_csv.py
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
    Based on the proven logic from preprocess_csv.py
    
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


def analyze_joins_optimized(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Optimized join analysis that processes the entire DataFrame once
    and caches results for fast retrieval
    """
    logger.info(f"Analyzing joins for {len(df)} queries...")
    
    join_analysis = {
        'relationships': [],
        'table_usage': defaultdict(int),
        'join_patterns': [],
        'join_types': defaultdict(int),
        'total_queries': len(df),
        'queries_with_joins': 0,
        'queries_with_descriptions': 0,
        'queries_with_tables': 0,
        'total_individual_joins': 0,
        'max_joins_per_query': 0,
        'join_count_distribution': defaultdict(int),
        'json_format_count': 0,
        'string_format_count': 0,
        'processing_time': 0
    }
    
    start_time = time.time()
    
    # Process each row
    for idx, row in df.iterrows():
        query = safe_get_value(row, 'query')
        description = safe_get_value(row, 'description')
        tables_raw = safe_get_value(row, 'tables')
        joins_raw = safe_get_value(row, 'joins')
        
        # Parse using optimized functions
        tables_list = parse_tables_column(tables_raw)
        joins_list = parse_joins_column(joins_raw)
        
        # Count metadata availability
        if description:
            join_analysis['queries_with_descriptions'] += 1
        if tables_list:
            join_analysis['queries_with_tables'] += 1
        if joins_list:
            join_analysis['queries_with_joins'] += 1
            
            # Track join count distribution
            join_count = len(joins_list)
            join_analysis['join_count_distribution'][join_count] += 1
            join_analysis['total_individual_joins'] += join_count
            join_analysis['max_joins_per_query'] = max(join_analysis['max_joins_per_query'], join_count)
        else:
            # Query with no joins
            join_analysis['join_count_distribution'][0] += 1
        
        # Process table usage
        for table in tables_list:
            if table:
                join_analysis['table_usage'][table] += 1
        
        # Process individual joins
        for join_info in joins_list:
            # Track format types
            if join_info['format'] == 'json':
                join_analysis['json_format_count'] += 1
            else:
                join_analysis['string_format_count'] += 1
            
            # Track join type
            join_type = join_info.get('join_type', 'JOIN')
            join_analysis['join_types'][join_type] += 1
            
            # Store join pattern
            if join_info['transformation']:
                join_analysis['join_patterns'].append(join_info['transformation'])
            else:
                join_analysis['join_patterns'].append(join_info['condition'])
            
            # Add table usage from joins
            if join_info['left_table'] and join_info['left_table'] != 'unknown':
                join_analysis['table_usage'][join_info['left_table']] += 1
            if join_info['right_table'] and join_info['right_table'] != 'unknown':
                join_analysis['table_usage'][join_info['right_table']] += 1
            
            # Create relationship entry
            relationship = {
                'left_table': join_info['left_table'],
                'right_table': join_info['right_table'],
                'condition': join_info['condition'],
                'join_type': join_type,
                'format': join_info['format']
            }
            
            if join_info['format'] == 'json':
                relationship.update({
                    'left_column': join_info.get('left_column', ''),
                    'right_column': join_info.get('right_column', ''),
                    'transformation': join_info.get('transformation', '')
                })
            
            join_analysis['relationships'].append(relationship)
    
    # Convert defaultdicts to regular dicts for JSON serialization
    join_analysis['table_usage'] = dict(join_analysis['table_usage'])
    join_analysis['join_types'] = dict(join_analysis['join_types'])
    join_analysis['join_count_distribution'] = dict(join_analysis['join_count_distribution'])
    
    join_analysis['processing_time'] = time.time() - start_time
    
    logger.info(f"Join analysis completed in {join_analysis['processing_time']:.2f}s")
    logger.info(f"Found {join_analysis['total_individual_joins']} joins across {join_analysis['queries_with_joins']} queries")
    
    return join_analysis


def generate_relationship_graph(join_analysis: Dict[str, Any], output_dir: Path) -> List[str]:
    """
    Generate static graph visualizations and save them to files
    
    Returns:
        List of generated graph file paths
    """
    if not GRAPHVIZ_AVAILABLE or not join_analysis['relationships']:
        logger.warning("Skipping graph generation - Graphviz not available or no relationships found")
        return []
    
    logger.info("Generating relationship graphs...")
    
    generated_files = []
    
    try:
        graph = graphviz.Graph(comment='Table Relationships', format='svg')
        graph.attr(rankdir='TB', size='12,8', dpi='150')
        graph.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue', fontsize='12')
        graph.attr('edge', fontsize='10')
        
        # Color map for different join types
        join_colors = {
            'LEFT JOIN': 'blue',
            'RIGHT JOIN': 'red',
            'INNER JOIN': 'green',
            'FULL JOIN': 'orange',
            'JOIN': 'black'
        }
        
        # Add nodes and edges
        tables_added = set()
        edge_count = 0
        
        for rel in join_analysis['relationships']:
            left_table = rel['left_table']
            right_table = rel['right_table']
            join_type = rel.get('join_type', 'JOIN')
            
            # Skip unknown tables from string parsing
            if left_table == 'unknown' or right_table == 'unknown':
                continue
            
            # Add nodes
            if left_table not in tables_added:
                graph.node(left_table, left_table)
                tables_added.add(left_table)
            
            if right_table not in tables_added:
                graph.node(right_table, right_table)
                tables_added.add(right_table)
            
            # Style edge based on join type
            edge_color = join_colors.get(join_type, 'black')
            edge_label = join_type
            
            # Add transformation info if available
            if rel.get('transformation') and rel['format'] == 'json':
                transform = rel['transformation']
                if len(transform) > 30:
                    transform = transform[:30] + '...'
                edge_label = f"{join_type}\\n{transform}"
            
            graph.edge(
                left_table,
                right_table,
                label=edge_label,
                color=edge_color
            )
            edge_count += 1
        
        # Generate multiple formats
        if tables_added:
            for format_type in GRAPH_FORMATS:
                try:
                    graph.format = format_type
                    output_file = output_dir / f"relationships_graph.{format_type}"
                    graph.render(str(output_file.with_suffix('')), cleanup=True)
                    generated_files.append(str(output_file))
                    logger.info(f"Generated {format_type.upper()} graph: {output_file}")
                except Exception as e:
                    logger.warning(f"Failed to generate {format_type} graph: {e}")
            
            logger.info(f"Graph generation completed: {len(tables_added)} tables, {edge_count} relationships")
        else:
            logger.info("No valid table relationships found for graph generation")
    
    except Exception as e:
        logger.error(f"Graph generation failed: {e}")
    
    return generated_files


def create_optimized_dataframe(df: pd.DataFrame, output_dir: Path) -> str:
    """
    Create optimized DataFrame with pre-parsed metadata and save in efficient format
    
    Returns:
        Path to the optimized DataFrame file
    """
    logger.info(f"Creating optimized DataFrame for {len(df)} queries...")
    
    # Create enhanced DataFrame with pre-parsed columns
    enhanced_df = df.copy()
    
    # Pre-parse and expand metadata
    tables_parsed = []
    joins_parsed = []
    join_counts = []
    has_descriptions = []
    has_tables = []
    has_joins = []
    
    for idx, row in df.iterrows():
        tables_raw = safe_get_value(row, 'tables')
        joins_raw = safe_get_value(row, 'joins')
        description = safe_get_value(row, 'description')
        
        # Parse tables and joins
        tables_list = parse_tables_column(tables_raw)
        joins_list = parse_joins_column(joins_raw)
        
        # Store parsed data
        tables_parsed.append(tables_list)
        joins_parsed.append(joins_list)
        join_counts.append(len(joins_list))
        has_descriptions.append(bool(description))
        has_tables.append(bool(tables_list))
        has_joins.append(bool(joins_list))
    
    # Add computed columns
    enhanced_df['tables_parsed'] = tables_parsed
    enhanced_df['joins_parsed'] = joins_parsed
    enhanced_df['join_count'] = join_counts
    enhanced_df['has_description'] = has_descriptions
    enhanced_df['has_tables'] = has_tables
    enhanced_df['has_joins'] = has_joins
    
    # Save in optimal format
    if PARQUET_AVAILABLE:
        output_file = output_dir / "optimized_queries.parquet"
        enhanced_df.to_parquet(output_file, index=False)
        logger.info(f"Saved optimized DataFrame as Parquet: {output_file}")
    else:
        output_file = output_dir / "optimized_queries.csv"
        # Convert lists to JSON strings for CSV compatibility
        enhanced_df_csv = enhanced_df.copy()
        enhanced_df_csv['tables_parsed'] = enhanced_df_csv['tables_parsed'].apply(json.dumps)
        enhanced_df_csv['joins_parsed'] = enhanced_df_csv['joins_parsed'].apply(json.dumps)
        enhanced_df_csv.to_csv(output_file, index=False)
        logger.info(f"Saved optimized DataFrame as CSV: {output_file}")
    
    return str(output_file)


def create_cache_metadata(
    csv_path: Path,
    cache_dir: Path,
    join_analysis: Dict[str, Any],
    graph_files: List[str],
    optimized_df_file: str,
    processing_time: float
) -> Dict[str, Any]:
    """Create metadata about the cache for validation and info display"""
    
    metadata = {
        'version': '1.0',
        'created_at': datetime.now().isoformat(),
        'source_csv': str(csv_path),
        'source_csv_modified': os.path.getmtime(csv_path),
        'source_csv_size': os.path.getsize(csv_path),
        'total_queries': join_analysis['total_queries'],
        'processing_time': processing_time,
        'files_generated': {
            'join_analysis': 'join_analysis.json',
            'table_usage': 'table_usage_stats.json',
            'optimized_dataframe': os.path.basename(optimized_df_file),
            'graph_files': [os.path.basename(f) for f in graph_files]
        },
        'statistics_summary': {
            'queries_with_joins': join_analysis['queries_with_joins'],
            'queries_with_descriptions': join_analysis['queries_with_descriptions'],
            'total_individual_joins': join_analysis['total_individual_joins'],
            'unique_tables': len(join_analysis['table_usage']),
            'max_joins_per_query': join_analysis['max_joins_per_query']
        }
    }
    
    return metadata


def save_analytics_cache(
    csv_path: Path,
    output_dir: Path,
    force_rebuild: bool = False
) -> bool:
    """
    Main function to generate and save all analytics cache files
    
    Returns:
        True if cache was generated successfully, False otherwise
    """
    start_time = time.time()
    
    # Check if rebuild is needed
    cache_metadata_file = output_dir / "cache_metadata.json"
    
    if not force_rebuild and cache_metadata_file.exists():
        try:
            with open(cache_metadata_file) as f:
                existing_metadata = json.load(f)
            
            csv_modified_time = os.path.getmtime(csv_path)
            cached_modified_time = existing_metadata.get('source_csv_modified', 0)
            
            if csv_modified_time <= cached_modified_time:
                logger.info("✅ Cache is up to date, no rebuild needed")
                return True
        except Exception as e:
            logger.warning(f"Could not read existing cache metadata: {e}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load CSV data
    logger.info(f"Loading data from {csv_path}")
    try:
        df = pd.read_csv(csv_path)
        df = df.fillna('')  # Handle missing values
        
        # Ensure required columns
        if 'query' not in df.columns:
            logger.error("CSV must contain a 'query' column")
            return False
        
        # Remove rows with empty queries
        initial_count = len(df)
        df = df[df['query'].str.strip() != '']
        final_count = len(df)
        
        if initial_count != final_count:
            logger.info(f"Filtered out {initial_count - final_count} rows with empty queries")
        
        logger.info(f"Processing {final_count} queries")
        
    except Exception as e:
        logger.error(f"Failed to load CSV data: {e}")
        return False
    
    try:
        # 1. Generate join analysis
        logger.info("Step 1/4: Analyzing joins and relationships...")
        join_analysis = analyze_joins_optimized(df)
        
        # Save join analysis
        with open(output_dir / "join_analysis.json", 'w') as f:
            json.dump(join_analysis, f, indent=2)
        logger.info("✅ Join analysis saved")
        
        # 2. Save table usage statistics
        logger.info("Step 2/4: Saving table usage statistics...")
        table_usage_stats = {
            'table_usage': join_analysis['table_usage'],
            'join_types': join_analysis['join_types'],
            'join_count_distribution': join_analysis['join_count_distribution']
        }
        
        with open(output_dir / "table_usage_stats.json", 'w') as f:
            json.dump(table_usage_stats, f, indent=2)
        logger.info("✅ Table usage statistics saved")
        
        # 3. Generate graph visualizations
        logger.info("Step 3/4: Generating graph visualizations...")
        graph_files = generate_relationship_graph(join_analysis, output_dir)
        logger.info(f"✅ Generated {len(graph_files)} graph files")
        
        # 4. Create optimized DataFrame
        logger.info("Step 4/4: Creating optimized DataFrame...")
        optimized_df_file = create_optimized_dataframe(df, output_dir)
        logger.info("✅ Optimized DataFrame created")
        
        # 5. Save cache metadata
        total_processing_time = time.time() - start_time
        metadata = create_cache_metadata(
            csv_path, output_dir, join_analysis,
            graph_files, optimized_df_file, total_processing_time
        )
        
        with open(cache_metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"🎉 Analytics cache generation completed in {total_processing_time:.2f}s")
        logger.info(f"📁 Cache saved to: {output_dir}")
        
        # Display summary
        print("\n" + "="*60)
        print("📊 ANALYTICS CACHE GENERATION SUMMARY")
        print("="*60)
        print(f"📁 Cache Directory: {output_dir}")
        print(f"📈 Total Queries Processed: {join_analysis['total_queries']:,}")
        print(f"🔗 Queries with Joins: {join_analysis['queries_with_joins']:,}")
        print(f"📝 Queries with Descriptions: {join_analysis['queries_with_descriptions']:,}")
        print(f"🏷️  Unique Tables Found: {len(join_analysis['table_usage']):,}")
        print(f"⚡ Processing Time: {total_processing_time:.2f}s")
        print(f"📄 Files Generated: {3 + len(graph_files)} files")
        print("\n✅ Ready for fast Streamlit app loading!")
        
        return True
        
    except Exception as e:
        logger.error(f"Analytics generation failed: {e}", exc_info=True)
        return False


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Pre-compute Query Catalog analytics for fast Streamlit loading"
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the CSV file containing queries"
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for analytics cache (default: same directory as CSV)"
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild even if cache is up to date"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return 1
    
    if args.output_dir:
        output_dir = Path(args.output_dir) / CACHE_DIR_NAME
    else:
        output_dir = csv_path.parent / CACHE_DIR_NAME
    
    print("🔥 Query Catalog Analytics Generator")
    print("="*50)
    print(f"📄 Source CSV: {csv_path}")
    print(f"📁 Output Directory: {output_dir}")
    print(f"🔄 Force Rebuild: {args.force_rebuild}")
    print("")
    
    # Generate analytics cache
    success = save_analytics_cache(csv_path, output_dir, args.force_rebuild)
    
    if success:
        print(f"\n🎯 Next Steps:")
        print(f"   1. Run: streamlit run app_simple_gemini.py")
        print(f"   2. The Query Catalog page will now load 10x faster!")
        print(f"   3. Re-run this script when your CSV data changes")
        return 0
    else:
        print("\n❌ Analytics generation failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    exit(main())