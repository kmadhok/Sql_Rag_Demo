#!/usr/bin/env python3
"""
Schema Agent for SQL RAG Application

Provides database schema exploration functionality that can be accessed through
@schema commands in the chat interface. Supports queries like:
- @schema what tables have customer_id column
- @schema what columns are in the customers table
- @schema show tables with INTEGER columns
- @schema describe project.dataset.orders

Works with the sample_queries_metadata_schema.csv file format:
tableid,columnnames,datatype
project.dataset.customers,customer_id,INTEGER
project.dataset.customers,email,STRING
...
"""

import pandas as pd
import logging
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ColumnInfo:
    """Information about a database column"""
    table_id: str
    column_name: str
    data_type: str
    
    def __str__(self):
        return f"{self.table_id}.{self.column_name} ({self.data_type})"

@dataclass
class TableInfo:
    """Information about a database table"""
    table_id: str
    columns: List[ColumnInfo]
    
    @property
    def column_count(self) -> int:
        return len(self.columns)
    
    @property
    def column_names(self) -> List[str]:
        return [col.column_name for col in self.columns]
    
    @property
    def data_types(self) -> Set[str]:
        return {col.data_type for col in self.columns}


class SchemaAgent:
    """
    Database schema exploration agent for SQL RAG chat interface.
    
    Provides natural language interface to database schema information
    loaded from CSV metadata files.
    """
    
    def __init__(self, schema_csv_path: str):
        """
        Initialize schema agent with CSV schema file
        
        Args:
            schema_csv_path: Path to CSV file with schema metadata
        """
        self.schema_csv_path = Path(schema_csv_path)
        self.schema_df = None
        self.tables_cache = {}
        self._load_schema()
    
    def _load_schema(self):
        """Load schema data from CSV file"""
        try:
            if not self.schema_csv_path.exists():
                logger.warning(f"Schema file not found: {self.schema_csv_path}")
                return
            
            self.schema_df = pd.read_csv(self.schema_csv_path)
            logger.info(f"✅ Schema loaded: {len(self.schema_df)} rows from {self.schema_csv_path}")
            
            # Validate required columns
            required_cols = ['tableid', 'columnnames', 'datatype']
            missing_cols = [col for col in required_cols if col not in self.schema_df.columns]
            if missing_cols:
                logger.error(f"Missing required columns in schema CSV: {missing_cols}")
                self.schema_df = None
                return
            
            # Build tables cache for faster queries
            self._build_tables_cache()
            
        except Exception as e:
            logger.error(f"Failed to load schema from {self.schema_csv_path}: {e}")
            self.schema_df = None
    
    def _build_tables_cache(self):
        """Build cache of table information for faster queries"""
        if self.schema_df is None:
            return
        
        self.tables_cache = {}
        
        for _, row in self.schema_df.iterrows():
            table_id = row['tableid']
            column_info = ColumnInfo(
                table_id=table_id,
                column_name=row['columnnames'],
                data_type=row['datatype']
            )
            
            if table_id not in self.tables_cache:
                self.tables_cache[table_id] = TableInfo(table_id=table_id, columns=[])
            
            self.tables_cache[table_id].columns.append(column_info)
        
        logger.info(f"📊 Schema cache built: {len(self.tables_cache)} tables")
    
    def is_available(self) -> bool:
        """Check if schema agent is available (schema data loaded)"""
        return self.schema_df is not None and not self.schema_df.empty
    
    def get_table_count(self) -> int:
        """Get total number of tables in schema"""
        return len(self.tables_cache) if self.tables_cache else 0
    
    def get_column_count(self) -> int:
        """Get total number of columns across all tables"""
        return len(self.schema_df) if self.schema_df is not None else 0
    
    def find_tables_with_column(self, column_name: str, case_sensitive: bool = False) -> List[TableInfo]:
        """
        Find all tables that contain a specific column
        
        Args:
            column_name: Name of column to search for
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            List of TableInfo objects for tables containing the column
        """
        if not self.is_available():
            return []
        
        matching_tables = []
        search_column = column_name if case_sensitive else column_name.lower()
        
        for table_info in self.tables_cache.values():
            table_columns = table_info.column_names if case_sensitive else [col.lower() for col in table_info.column_names]
            
            if search_column in table_columns:
                matching_tables.append(table_info)
        
        return sorted(matching_tables, key=lambda t: t.table_id)
    
    def get_table_columns(self, table_name: str, case_sensitive: bool = False) -> Optional[TableInfo]:
        """
        Get all columns for a specific table
        
        Args:
            table_name: Name of table (can be partial, e.g., 'customers' or 'project.dataset.customers')
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            TableInfo object if table found, None otherwise
        """
        if not self.is_available():
            return None
        
        search_table = table_name if case_sensitive else table_name.lower()
        
        # Try exact match first
        for table_id, table_info in self.tables_cache.items():
            check_table = table_id if case_sensitive else table_id.lower()
            if check_table == search_table:
                return table_info
        
        # Try partial match (contains)
        for table_id, table_info in self.tables_cache.items():
            check_table = table_id if case_sensitive else table_id.lower()
            if search_table in check_table or check_table.endswith(f".{search_table}"):
                return table_info
        
        return None
    
    def find_tables_by_datatype(self, data_type: str, case_sensitive: bool = False) -> List[Tuple[TableInfo, List[ColumnInfo]]]:
        """
        Find tables that have columns of a specific data type
        
        Args:
            data_type: Data type to search for (e.g., 'INTEGER', 'STRING', 'DATE')
            case_sensitive: Whether to perform case-sensitive search
            
        Returns:
            List of tuples (TableInfo, List[ColumnInfo]) for matching columns
        """
        if not self.is_available():
            return []
        
        search_type = data_type if case_sensitive else data_type.upper()
        results = []
        
        for table_info in self.tables_cache.values():
            matching_columns = []
            for column in table_info.columns:
                check_type = column.data_type if case_sensitive else column.data_type.upper()
                if check_type == search_type:
                    matching_columns.append(column)
            
            if matching_columns:
                results.append((table_info, matching_columns))
        
        return sorted(results, key=lambda x: x[0].table_id)
    
    def get_all_tables(self) -> List[TableInfo]:
        """Get information about all tables in the schema"""
        if not self.is_available():
            return []
        
        return sorted(self.tables_cache.values(), key=lambda t: t.table_id)
    
    def search_schema(self, query_text: str) -> str:
        """
        Search schema based on natural language query
        
        Args:
            query_text: Natural language query about schema
            
        Returns:
            Formatted response string
        """
        if not self.is_available():
            return "❌ Schema information is not available. Please ensure the schema CSV file is loaded."
        
        query_lower = query_text.lower().strip()
        
        # Parse different types of schema queries
        if "tables" in query_lower and ("column" in query_lower or "field" in query_lower):
            # Find tables with specific column
            # Extract column name from query
            column_name = self._extract_column_name_from_query(query_text)
            if column_name:
                return self._format_tables_with_column_response(column_name)
            else:
                return "❓ Could not identify the column name in your query. Try: '@schema what tables have customer_id column'"
        
        elif "columns" in query_lower and ("table" in query_lower or "in" in query_lower):
            # Get columns for specific table
            table_name = self._extract_table_name_from_query(query_text)
            if table_name:
                return self._format_table_columns_response(table_name)
            else:
                return "❓ Could not identify the table name in your query. Try: '@schema what columns are in customers table'"
        
        elif "describe" in query_lower or "show" in query_lower:
            # Describe table or show schema
            table_name = self._extract_table_name_from_query(query_text)
            if table_name:
                return self._format_table_description_response(table_name)
            else:
                return self._format_schema_overview()
        
        elif any(dtype in query_lower for dtype in ["integer", "string", "date", "numeric", "boolean"]):
            # Find tables by data type
            data_type = self._extract_datatype_from_query(query_text)
            if data_type:
                return self._format_tables_by_datatype_response(data_type)
        
        else:
            # Default: provide schema overview
            return self._format_schema_overview()
    
    def _extract_column_name_from_query(self, query: str) -> Optional[str]:
        """Extract column name from natural language query"""
        # Simple extraction - look for common patterns
        query_lower = query.lower()
        
        # Pattern: "tables have [column_name] column"
        import re
        patterns = [
            r"tables?\s+(?:have|with|containing?)\s+(\w+)\s+column",
            r"(\w+)\s+column",
            r"column\s+(\w+)",
            r"field\s+(\w+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_table_name_from_query(self, query: str) -> Optional[str]:
        """Extract table name from natural language query"""
        query_lower = query.lower()
        
        # Pattern: "columns in [table_name] table" or "describe [table_name]"
        import re
        patterns = [
            r"(?:columns?\s+(?:in|from|of)\s+|describe\s+|show\s+)(\w+(?:\.\w+\.\w+)?)",
            r"(?:in\s+(?:the\s+)?|from\s+(?:the\s+)?)(\w+)\s+table",
            r"table\s+(\w+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_datatype_from_query(self, query: str) -> Optional[str]:
        """Extract data type from natural language query"""
        query_lower = query.lower()
        
        # Map common terms to data types
        type_mapping = {
            "integer": "INTEGER",
            "int": "INTEGER",
            "string": "STRING",
            "text": "STRING",
            "varchar": "STRING",
            "date": "DATE",
            "datetime": "DATE",
            "numeric": "NUMERIC",
            "decimal": "NUMERIC",
            "float": "NUMERIC",
            "boolean": "BOOLEAN",
            "bool": "BOOLEAN"
        }
        
        for term, data_type in type_mapping.items():
            if term in query_lower:
                return data_type
        
        return None
    
    def _format_tables_with_column_response(self, column_name: str) -> str:
        """Format response for tables containing a specific column"""
        tables = self.find_tables_with_column(column_name)
        
        if not tables:
            return f"🔍 No tables found with column '{column_name}'"
        
        response = f"📋 **Tables with '{column_name}' column:**\n\n"
        for table in tables:
            # Find the specific column info
            matching_columns = [col for col in table.columns if col.column_name.lower() == column_name.lower()]
            if matching_columns:
                col_info = matching_columns[0]
                response += f"• **{table.table_id}** - `{col_info.column_name}` ({col_info.data_type})\n"
        
        response += f"\n💡 Found in {len(tables)} table{'s' if len(tables) != 1 else ''}"
        return response
    
    def _format_table_columns_response(self, table_name: str) -> str:
        """Format response for columns in a specific table"""
        table_info = self.get_table_columns(table_name)
        
        if not table_info:
            return f"🔍 Table '{table_name}' not found. Available tables: {', '.join(list(self.tables_cache.keys())[:5])}..."
        
        response = f"📋 **Columns in {table_info.table_id}:**\n\n"
        
        # Group by data type for better organization
        type_groups = {}
        for column in table_info.columns:
            if column.data_type not in type_groups:
                type_groups[column.data_type] = []
            type_groups[column.data_type].append(column.column_name)
        
        for data_type, columns in sorted(type_groups.items()):
            response += f"**{data_type}:**\n"
            for column in sorted(columns):
                response += f"  • `{column}`\n"
            response += "\n"
        
        response += f"💡 Total: {table_info.column_count} columns, {len(type_groups)} data types"
        return response
    
    def _format_table_description_response(self, table_name: str) -> str:
        """Format detailed description response for a table"""
        table_info = self.get_table_columns(table_name)
        
        if not table_info:
            return f"🔍 Table '{table_name}' not found"
        
        response = f"📊 **Table Description: {table_info.table_id}**\n\n"
        response += f"**Column Count:** {table_info.column_count}\n"
        response += f"**Data Types:** {', '.join(sorted(table_info.data_types))}\n\n"
        response += "**Schema:**\n"
        response += "```\n"
        
        # Format as table-like structure
        max_name_len = max(len(col.column_name) for col in table_info.columns)
        max_type_len = max(len(col.data_type) for col in table_info.columns)
        
        for column in table_info.columns:
            response += f"{column.column_name:<{max_name_len}} | {column.data_type:<{max_type_len}}\n"
        
        response += "```"
        return response
    
    def _format_tables_by_datatype_response(self, data_type: str) -> str:
        """Format response for tables with specific data type"""
        results = self.find_tables_by_datatype(data_type)
        
        if not results:
            return f"🔍 No tables found with {data_type} columns"
        
        response = f"📋 **Tables with {data_type} columns:**\n\n"
        
        for table_info, columns in results:
            column_names = [col.column_name for col in columns]
            response += f"• **{table_info.table_id}** ({len(columns)} {data_type} column{'s' if len(columns) != 1 else ''})\n"
            response += f"  Columns: {', '.join(f'`{name}`' for name in column_names)}\n\n"
        
        total_columns = sum(len(columns) for _, columns in results)
        response += f"💡 Found {total_columns} {data_type} columns across {len(results)} tables"
        return response
    
    def _format_schema_overview(self) -> str:
        """Format general schema overview"""
        if not self.is_available():
            return "❌ Schema information is not available"
        
        table_count = self.get_table_count()
        column_count = self.get_column_count()
        
        # Get data type distribution
        type_counts = {}
        for table in self.tables_cache.values():
            for column in table.columns:
                type_counts[column.data_type] = type_counts.get(column.data_type, 0) + 1
        
        response = f"📊 **Database Schema Overview**\n\n"
        response += f"**Tables:** {table_count}\n"
        response += f"**Total Columns:** {column_count}\n\n"
        
        response += "**Data Type Distribution:**\n"
        for dtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            response += f"• {dtype}: {count} columns\n"
        
        response += f"\n**Sample Tables:**\n"
        sample_tables = list(self.tables_cache.keys())[:5]
        for table in sample_tables:
            col_count = len(self.tables_cache[table].columns)
            response += f"• `{table}` ({col_count} columns)\n"
        
        if table_count > 5:
            response += f"... and {table_count - 5} more tables\n"
        
        response += "\n💡 **Available Commands:**\n"
        response += "• `@schema what tables have customer_id column`\n"
        response += "• `@schema what columns are in customers table`\n"
        response += "• `@schema describe project.dataset.orders`\n"
        response += "• `@schema show INTEGER columns`"
        
        return response


def detect_schema_command(user_input: str) -> Tuple[bool, str]:
    """
    Detect if user input is a schema command
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Tuple of (is_schema_command, cleaned_query)
    """
    user_input = user_input.strip()
    
    if user_input.startswith("@schema"):
        query = user_input[7:].strip()  # Remove "@schema" prefix
        return True, query
    
    return False, user_input


def handle_schema_query(query: str, schema_agent: SchemaAgent) -> str:
    """
    Handle a schema query using the schema agent
    
    Args:
        query: Schema query text (without @schema prefix)
        schema_agent: Initialized SchemaAgent instance
        
    Returns:
        Formatted response string
    """
    if not schema_agent.is_available():
        return ("❌ **Schema Agent Unavailable**\n\n"
                "The schema information is not available. Please ensure the schema CSV file is loaded.\n\n"
                "Expected file format:\n"
                "```\n"
                "tableid,columnnames,datatype\n"
                "project.dataset.customers,customer_id,INTEGER\n"
                "project.dataset.customers,email,STRING\n"
                "...\n"
                "```")
    
    if not query.strip():
        return schema_agent._format_schema_overview()
    
    return schema_agent.search_schema(query)


# Example usage and testing
if __name__ == "__main__":
    # Test the schema agent
    schema_file = "sample_queries_metadata_schema.csv"
    agent = SchemaAgent(schema_file)
    
    if agent.is_available():
        print("✅ Schema Agent Test")
        print("=" * 40)
        
        # Test queries
        test_queries = [
            "what tables have customer_id column",
            "what columns are in customers table",
            "describe project.dataset.orders",
            "show INTEGER columns",
            ""  # Schema overview
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            response = agent.search_schema(query)
            print(response)
            print("-" * 40)
    else:
        print("❌ Schema agent could not be initialized")