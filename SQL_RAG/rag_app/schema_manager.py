#!/usr/bin/env python3
"""
Smart Schema Manager for SQL RAG System

Provides intelligent schema filtering to inject only relevant table schemas
into LLM prompts, reducing noise from 39K+ schema rows to 100-500 relevant ones.

Key Features:
- Fast O(1) table lookup from 39K row schema CSV
- SQL query parsing to extract table names
- Smart schema filtering based on retrieved documents
- Optimized formatting for LLM consumption

Usage:
    schema_manager = SchemaManager("path/to/schema.csv")
    relevant_schema = schema_manager.get_relevant_schema(table_names)
"""

import os
import re
import logging
import time
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaManager:
    """
    Intelligent schema management for SQL RAG systems.
    
    Loads large schema datasets and provides fast filtering capabilities
    to inject only relevant schema information into LLM prompts.
    """
    
    def __init__(self, schema_csv_path: str, verbose: bool = False):
        """
        Initialize SchemaManager with schema CSV file.
        
        Args:
            schema_csv_path: Path to CSV file with columns (table_id, column, datatype)
            verbose: Enable detailed logging
        """
        self.schema_csv_path = Path(schema_csv_path)
        self.verbose = verbose
        self.schema_lookup = {}  # Dict[table_name, List[Tuple[column, datatype]]]
        self.table_count = 0
        self.column_count = 0
        self.unique_datatypes = set()
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        # Load and index schema
        self._load_schema()
        
        if verbose:
            logger.info(f"✅ SchemaManager initialized with {self.table_count} tables, {self.column_count} columns")
    
    def _load_schema(self):
        """Load and index schema CSV for fast table lookups."""
        try:
            if not self.schema_csv_path.exists():
                raise FileNotFoundError(f"Schema file not found: {self.schema_csv_path}")
            
            if self.verbose:
                logger.info(f"Loading schema from {self.schema_csv_path}")
            
            start_time = time.time()
            
            # Load CSV file
            df = pd.read_csv(self.schema_csv_path)
            initial_rows = len(df)
            
            # Validate required columns
            required_cols = ['table_id', 'column', 'datatype']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Schema CSV missing required columns: {missing_cols}")
            
            # Clean data - remove rows with empty values
            df = df.dropna()
            df = df[
                (df['table_id'].str.strip() != '') &
                (df['column'].str.strip() != '') &
                (df['datatype'].str.strip() != '')
            ]
            
            filtered_rows = len(df)
            if initial_rows != filtered_rows:
                skipped = initial_rows - filtered_rows
                logger.info(f"Filtered out {skipped} rows with empty values")
            
            # Build lookup dictionary indexed by table name
            schema_lookup = defaultdict(list)
            processed_tables = set()
            
            for _, row in df.iterrows():
                try:
                    table_id = str(row['table_id']).strip()
                    column = str(row['column']).strip()
                    datatype = str(row['datatype']).strip()
                    
                    # Normalize table name (extract from project.dataset.table format)
                    table_name = self._normalize_table_name(table_id)
                    
                    # Add to lookup
                    schema_lookup[table_name].append((column, datatype))
                    processed_tables.add(table_name)
                    self.unique_datatypes.add(datatype)
                    self.column_count += 1
                    
                except Exception as row_error:
                    logger.warning(f"Skipping invalid schema row: {row_error}")
                    continue
            
            # Convert to regular dict and store stats
            self.schema_lookup = dict(schema_lookup)
            self.table_count = len(self.schema_lookup)
            
            load_time = time.time() - start_time
            
            logger.info(f"✅ Schema loaded in {load_time:.2f}s: {self.table_count} tables, {self.column_count} columns, {len(self.unique_datatypes)} data types")
            
            if self.verbose:
                logger.debug(f"Sample tables: {list(self.schema_lookup.keys())[:5]}")
                logger.debug(f"Data types: {', '.join(sorted(list(self.unique_datatypes))[:10])}")
                
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            raise
    
    def _normalize_table_name(self, table_id: str) -> str:
        """
        Extract table name from BigQuery format (project.dataset.table).
        
        Args:
            table_id: Full table identifier (e.g., "project.dataset.customers")
            
        Returns:
            Normalized table name (e.g., "customers")
        """
        # Remove backticks and quotes
        clean_id = table_id.strip('`"\' ')
        
        # Extract table name (last part after dots)
        if '.' in clean_id:
            return clean_id.split('.')[-1].strip().lower()
        
        return clean_id.strip().lower()
    
    def extract_tables_from_content(self, content: str) -> List[str]:
        """
        Extract table names from SQL queries and metadata.
        
        Args:
            content: SQL query text or document content
            
        Returns:
            List of normalized table names found in the content
        """
        if not content or not isinstance(content, str):
            return []
        
        tables = set()
        content_lower = content.lower()
        
        # SQL parsing patterns for different query types
        sql_patterns = [
            # FROM clauses
            r'\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            # JOIN clauses (various types)
            r'\b(?:inner\s+|left\s+|right\s+|full\s+|cross\s+)?join\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            # UPDATE statements
            r'\bupdate\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            # INSERT INTO statements
            r'\binsert\s+into\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            # DELETE FROM statements
            r'\bdelete\s+from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            # WITH clauses (CTEs)
            r'\bwith\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+as'
        ]
        
        # Extract table names using patterns
        for pattern in sql_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                normalized_table = self._normalize_table_name(match)
                if normalized_table:
                    tables.add(normalized_table)
        
        # Also check for metadata patterns (from document metadata)
        metadata_patterns = [
            # "Tables: table1, table2" format
            r'tables?:\s*([^,\n]+(?:,\s*[^,\n]+)*)',
            # "Table: table1" format
            r'table:\s*([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        
        for pattern in metadata_patterns:
            matches = re.findall(pattern, content_lower)
            for match in matches:
                # Split by commas and clean up
                table_names = [name.strip() for name in match.split(',')]
                for table_name in table_names:
                    if table_name:
                        normalized_table = self._normalize_table_name(table_name)
                        if normalized_table:
                            tables.add(normalized_table)
        
        result = list(tables)
        
        if self.verbose and result:
            logger.debug(f"Extracted tables from content: {result}")
        
        return result
    
    def extract_tables_from_documents(self, documents) -> List[str]:
        """
        Extract table names from multiple documents (from vector search results).
        
        Args:
            documents: List of Document objects or similar with page_content and metadata
            
        Returns:
            List of unique table names found across all documents
        """
        all_tables = set()
        
        for doc in documents:
            # Extract from document content
            content = getattr(doc, 'page_content', str(doc))
            tables_from_content = self.extract_tables_from_content(content)
            all_tables.update(tables_from_content)
            
            # Extract from metadata if available
            if hasattr(doc, 'metadata') and doc.metadata:
                metadata = doc.metadata
                
                # Check specific metadata fields
                for field in ['table', 'tables', 'joins']:
                    if field in metadata and metadata[field]:
                        metadata_tables = self.extract_tables_from_content(str(metadata[field]))
                        all_tables.update(metadata_tables)
        
        result = list(all_tables)
        
        if self.verbose:
            logger.debug(f"Extracted {len(result)} unique tables from {len(documents)} documents: {result}")
        
        return result
    
    def get_schema_for_table(self, table_name: str) -> List[Tuple[str, str]]:
        """
        Get schema information for a specific table.
        
        Args:
            table_name: Name of the table to look up
            
        Returns:
            List of (column, datatype) tuples for the table
        """
        normalized_name = self._normalize_table_name(table_name)
        return self.schema_lookup.get(normalized_name, [])
    
    def get_relevant_schema(self, table_names: List[str], max_tables: int = 50) -> str:
        """
        Get filtered schema for relevant tables, formatted for LLM consumption.
        
        Args:
            table_names: List of table names to include
            max_tables: Maximum number of tables to include (prevents overwhelming context)
            
        Returns:
            Formatted schema string ready for LLM prompt injection
        """
        if not table_names:
            return ""
        
        # Remove duplicates and limit to max_tables
        unique_tables = list(dict.fromkeys(table_names))[:max_tables]
        
        schema_parts = []
        tables_found = []
        tables_not_found = []
        total_columns = 0
        
        for table_name in unique_tables:
            schema = self.get_schema_for_table(table_name)
            
            if schema:
                tables_found.append(table_name)
                
                # Format table schema
                schema_parts.append(f"\n{table_name}:")
                for column, datatype in schema:
                    schema_parts.append(f"  - {column} ({datatype})")
                    total_columns += 1
            else:
                tables_not_found.append(table_name)
        
        if not tables_found:
            return ""
        
        # Build final schema string
        header = f"RELEVANT DATABASE SCHEMA ({len(tables_found)} tables, {total_columns} columns):"
        schema_text = header + "\n" + "\n".join(schema_parts)
        
        # Add coverage info if some tables weren't found
        if tables_not_found and self.verbose:
            coverage_info = f"\n\nNote: Schema not available for: {', '.join(tables_not_found)}"
            schema_text += coverage_info
        
        if self.verbose:
            logger.debug(f"Generated schema for {len(tables_found)} tables ({total_columns} columns)")
            if tables_not_found:
                logger.debug(f"Tables not found in schema: {tables_not_found}")
        
        return schema_text
    
    def get_schema_stats(self) -> Dict[str, any]:
        """
        Get statistics about the loaded schema.
        
        Returns:
            Dictionary with schema statistics
        """
        return {
            'total_tables': self.table_count,
            'total_columns': self.column_count,
            'unique_datatypes': len(self.unique_datatypes),
            'datatypes': sorted(list(self.unique_datatypes)),
            'avg_columns_per_table': self.column_count / self.table_count if self.table_count > 0 else 0,
            'schema_file': str(self.schema_csv_path)
        }
    
    def search_tables(self, search_term: str) -> List[str]:
        """
        Search for tables by name pattern.
        
        Args:
            search_term: Search term to match against table names
            
        Returns:
            List of matching table names
        """
        search_lower = search_term.lower()
        matching_tables = []
        
        for table_name in self.schema_lookup.keys():
            if search_lower in table_name.lower():
                matching_tables.append(table_name)
        
        return sorted(matching_tables)
    
    def get_table_sample(self, limit: int = 10) -> List[str]:
        """
        Get a sample of table names for testing/debugging.
        
        Args:
            limit: Maximum number of tables to return
            
        Returns:
            List of sample table names
        """
        return list(self.schema_lookup.keys())[:limit]
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """
        Get table information for SQL validator compatibility.
        
        Args:
            table_name: Name of the table to look up
            
        Returns:
            Dictionary with table info if table exists, None otherwise
        """
        normalized_name = self._normalize_table_name(table_name)
        schema = self.schema_lookup.get(normalized_name)
        
        if schema:
            return {
                'table_name': normalized_name,
                'columns': [col for col, _ in schema],
                'datatypes': [dtype for _, dtype in schema],
                'column_count': len(schema)
            }
        return None
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get list of column names for a specific table (SQL validator compatibility).
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names for the table
        """
        normalized_name = self._normalize_table_name(table_name)
        schema = self.schema_lookup.get(normalized_name, [])
        return [col for col, _ in schema]
    
    @property
    def schema_df(self) -> Optional[object]:
        """
        Provide schema DataFrame access for SQL validator fallback logic.
        Creates a pandas DataFrame from the schema_lookup for compatibility.
        
        Returns:
            DataFrame with table_id, column, datatype columns
        """
        try:
            import pandas as pd
            
            rows = []
            for table_name, columns in self.schema_lookup.items():
                for column, datatype in columns:
                    rows.append({
                        'table_id': table_name,
                        'column': column,
                        'datatype': datatype
                    })
            
            if rows:
                return pd.DataFrame(rows)
            else:
                return pd.DataFrame(columns=['table_id', 'column', 'datatype'])
                
        except ImportError:
            # If pandas is not available, return None
            return None


def create_schema_manager(schema_csv_path: str, verbose: bool = False) -> Optional[SchemaManager]:
    """
    Factory function to create SchemaManager with error handling.
    
    Args:
        schema_csv_path: Path to schema CSV file
        verbose: Enable detailed logging
        
    Returns:
        SchemaManager instance or None if creation fails
    """
    try:
        return SchemaManager(schema_csv_path, verbose=verbose)
    except Exception as e:
        logger.error(f"Failed to create SchemaManager: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    print("🔧 Testing SchemaManager")
    print("=" * 50)
    
    # Example usage (adjust path as needed)
    schema_path = "schema.csv"  # Replace with your actual schema file path
    
    if Path(schema_path).exists():
        try:
            # Create schema manager
            manager = SchemaManager(schema_path, verbose=True)
            
            # Test table extraction
            test_query = """
            SELECT c.customer_id, c.name, o.order_total
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.order_date > '2023-01-01'
            """
            
            tables = manager.extract_tables_from_content(test_query)
            print(f"\n🔍 Extracted tables: {tables}")
            
            # Test schema filtering
            if tables:
                schema = manager.get_relevant_schema(tables)
                print(f"\n📊 Relevant schema:\n{schema}")
            
            # Show stats
            stats = manager.get_schema_stats()
            print(f"\n📈 Schema stats: {stats}")
            
        except Exception as e:
            print(f"❌ Error testing SchemaManager: {e}")
    else:
        print(f"❌ Schema file not found: {schema_path}")
        print("💡 This is normal if you haven't set up the schema file yet")
        print("   The SchemaManager will be used when you have a schema CSV file")