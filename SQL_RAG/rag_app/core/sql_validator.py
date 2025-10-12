#!/usr/bin/env python3
"""
SQL Query Validator

Validates generated SQL queries against database schema to ensure:
1. Syntactic correctness
2. Table names exist in schema
3. Column names exist in specified tables
4. JOIN relationships are valid
5. Data type compatibility

Integrates with schema_manager.py to validate against sample_queries_metadata_schema.csv
"""

import re
import logging
import sqlparse
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation strictness levels"""
    SYNTAX_ONLY = "syntax_only"  # Only check SQL syntax
    SCHEMA_BASIC = "schema_basic"  # Check table/column existence
    SCHEMA_STRICT = "schema_strict"  # Full validation including types and joins

@dataclass
class ValidationResult:
    """Result of SQL validation"""
    is_valid: bool
    validation_level: ValidationLevel
    errors: List[str]
    warnings: List[str]
    tables_found: Set[str]
    columns_found: Set[str]
    joins_found: List[Dict[str, str]]
    suggestions: List[str]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

class SQLValidator:
    """
    SQL Query Validator that checks generated SQL against database schema
    """
    
    def __init__(self, schema_manager=None, validation_level: ValidationLevel = ValidationLevel.SCHEMA_STRICT):
        """
        Initialize SQL validator
        
        Args:
            schema_manager: SchemaManager instance for schema validation
            validation_level: Level of validation strictness
        """
        self.schema_manager = schema_manager
        self.validation_level = validation_level
        
        # Common SQL keywords that shouldn't be validated as tables/columns
        self.sql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'LIKE', 'BETWEEN', 'IS',
            'NULL', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'DISTINCT',
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'AS', 'ASC', 'DESC',
            'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP',
            'WITH', 'OVER', 'PARTITION', 'WINDOW', 'CAST', 'EXTRACT'
        }
        
        logger.info(f"SQL Validator initialized with level: {validation_level.value}")
    
    def validate_sql(self, sql_text: str) -> ValidationResult:
        """
        Validate SQL query at the configured validation level
        
        Args:
            sql_text: SQL query text to validate
            
        Returns:
            ValidationResult with validation details
        """
        try:
            # Initialize result
            result = ValidationResult(
                is_valid=True,
                validation_level=self.validation_level,
                errors=[],
                warnings=[],
                tables_found=set(),
                columns_found=set(),
                joins_found=[],
                suggestions=[]
            )
            
            # Extract SQL from text (may contain explanations)
            sql_queries = self._extract_sql_from_text(sql_text)
            
            if not sql_queries:
                result.warnings.append("No SQL queries found in the provided text")
                return result
            
            # Validate each SQL query found
            for i, sql_query in enumerate(sql_queries):
                query_result = self._validate_single_query(sql_query)
                
                # Merge results
                result.errors.extend([f"Query {i+1}: {error}" for error in query_result.errors])
                result.warnings.extend([f"Query {i+1}: {warning}" for warning in query_result.warnings])
                result.tables_found.update(query_result.tables_found)
                result.columns_found.update(query_result.columns_found)
                result.joins_found.extend(query_result.joins_found)
                result.suggestions.extend([f"Query {i+1}: {suggestion}" for suggestion in query_result.suggestions])
            
            # Overall validity
            result.is_valid = len(result.errors) == 0
            
            logger.info(f"Validated {len(sql_queries)} SQL queries. Valid: {result.is_valid}")
            return result
            
        except Exception as e:
            logger.error(f"Error during SQL validation: {e}")
            return ValidationResult(
                is_valid=False,
                validation_level=self.validation_level,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                tables_found=set(),
                columns_found=set(),
                joins_found=[],
                suggestions=[]
            )
    
    def _extract_sql_from_text(self, text: str) -> List[str]:
        """
        Extract SQL queries from text that may contain explanations
        
        Args:
            text: Text that may contain SQL queries
            
        Returns:
            List of SQL query strings
        """
        sql_queries = []
        
        # Pattern 1: SQL code blocks (```sql ... ```)
        sql_block_pattern = r'```sql\s*(.*?)\s*```'
        sql_blocks = re.findall(sql_block_pattern, text, re.DOTALL | re.IGNORECASE)
        sql_queries.extend(sql_blocks)
        
        # Pattern 2: SQL code blocks without language specification (``` ... ```)
        code_block_pattern = r'```\s*(.*?)\s*```'
        code_blocks = re.findall(code_block_pattern, text, re.DOTALL)
        for block in code_blocks:
            if self._looks_like_sql(block):
                sql_queries.append(block)
        
        # Pattern 3: Lines that start with SELECT, WITH, CREATE, etc.
        lines = text.split('\n')
        current_query = []
        in_query = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts a SQL query
            if re.match(r'^\s*(SELECT|WITH|CREATE|INSERT|UPDATE|DELETE|ALTER|DROP)', line, re.IGNORECASE):
                if current_query:
                    sql_queries.append('\n'.join(current_query))
                current_query = [line]
                in_query = True
            elif in_query:
                # Continue building the query
                current_query.append(line)
                # Check if this looks like end of query (semicolon or common ending words)
                if line.endswith(';') or re.match(r'.*\b(LIMIT|ORDER\s+BY)\b.*', line, re.IGNORECASE):
                    sql_queries.append('\n'.join(current_query))
                    current_query = []
                    in_query = False
        
        # Add any remaining query
        if current_query:
            sql_queries.append('\n'.join(current_query))
        
        # Clean and deduplicate
        cleaned_queries = []
        for query in sql_queries:
            cleaned = query.strip().rstrip(';')
            if cleaned and self._looks_like_sql(cleaned):
                cleaned_queries.append(cleaned)
        
        return list(set(cleaned_queries))  # Remove duplicates
    
    def _looks_like_sql(self, text: str) -> bool:
        """
        Check if text looks like a SQL query
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be SQL
        """
        text_upper = text.upper().strip()
        
        # Must contain SQL keywords
        sql_indicators = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'CREATE', 'INSERT', 'UPDATE', 'DELETE']
        has_sql_keywords = any(keyword in text_upper for keyword in sql_indicators)
        
        # Should not be primarily explanatory text
        words = text_upper.split()
        if len(words) < 3:
            return False
            
        # High ratio of SQL keywords indicates SQL
        sql_word_count = sum(1 for word in words if word in self.sql_keywords)
        sql_ratio = sql_word_count / len(words)
        
        return has_sql_keywords and sql_ratio > 0.1
    
    def _validate_single_query(self, sql_query: str) -> ValidationResult:
        """
        Validate a single SQL query
        
        Args:
            sql_query: SQL query string
            
        Returns:
            ValidationResult for this query
        """
        result = ValidationResult(
            is_valid=True,
            validation_level=self.validation_level,
            errors=[],
            warnings=[],
            tables_found=set(),
            columns_found=set(),
            joins_found=[],
            suggestions=[]
        )
        
        # Step 1: Syntax validation
        syntax_valid = self._validate_syntax(sql_query, result)
        
        if not syntax_valid and self.validation_level == ValidationLevel.SYNTAX_ONLY:
            result.is_valid = False
            return result
        
        # Step 2: Schema validation (if schema manager available and level permits)
        if (self.schema_manager and 
            self.validation_level in [ValidationLevel.SCHEMA_BASIC, ValidationLevel.SCHEMA_STRICT]):
            self._validate_schema(sql_query, result)
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def _validate_syntax(self, sql_query: str, result: ValidationResult) -> bool:
        """
        Validate SQL syntax using sqlparse
        
        Args:
            sql_query: SQL query to validate
            result: ValidationResult to update
            
        Returns:
            True if syntax is valid
        """
        try:
            # Parse the SQL
            parsed = sqlparse.parse(sql_query)
            
            if not parsed:
                result.errors.append("Could not parse SQL query")
                return False
            
            # Check for basic syntax issues
            for statement in parsed:
                if statement.get_type() is None:
                    result.warnings.append("SQL statement type could not be determined")
                
                # Check for common syntax errors with BigQuery tolerance
                tokens = list(statement.flatten())
                for i, token in enumerate(tokens):
                    if token.ttype is sqlparse.tokens.Error:
                        # Allow BigQuery-style backtick quoting without failing syntax
                        if token.value == '`':
                            continue
                        result.errors.append(f"Syntax error near: '{token.value}'")
                        return False
            
            logger.debug("SQL syntax validation passed")
            return True
            
        except Exception as e:
            result.errors.append(f"Syntax validation failed: {str(e)}")
            return False
    
    def _validate_schema(self, sql_query: str, result: ValidationResult) -> None:
        """
        Validate SQL against database schema
        
        Args:
            sql_query: SQL query to validate
            result: ValidationResult to update
        """
        try:
            # Extract tables and columns from SQL
            tables, columns, joins = self._extract_sql_elements(sql_query)
            
            result.tables_found.update(tables)
            result.columns_found.update(columns)
            result.joins_found.extend(joins)
            
            # Validate tables exist in schema
            for table_name in tables:
                if not self._validate_table_exists(table_name):
                    result.errors.append(f"Table '{table_name}' not found in schema")
                    # Suggest similar table names
                    suggestions = self._suggest_similar_tables(table_name)
                    if suggestions:
                        result.suggestions.append(f"Did you mean: {', '.join(suggestions)}?")
            
            # Validate columns exist in their tables
            for column_info in columns:
                # Handle frozenset of items or dict format
                if isinstance(column_info, frozenset):
                    column_dict = dict(column_info)
                elif isinstance(column_info, dict):
                    column_dict = column_info
                else:
                    continue
                
                if 'table' in column_dict and 'column' in column_dict:
                    table_name = column_dict['table']
                    column_name = column_dict['column']
                    
                    if not self._validate_column_exists(table_name, column_name):
                        result.errors.append(f"Column '{column_name}' not found in table '{table_name}'")
                        # Suggest similar column names
                        suggestions = self._suggest_similar_columns(table_name, column_name)
                        if suggestions:
                            result.suggestions.append(f"Did you mean: {', '.join(suggestions)}?")
            
            # Validate JOIN relationships
            for join_info in joins:
                self._validate_join(join_info, result)
            
            # Validate BigQuery-specific data type usage
            if self.validation_level == ValidationLevel.SCHEMA_STRICT:
                self._validate_bigquery_data_types(sql_query, result)
                
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            result.warnings.append(f"Schema validation error: {str(e)}")
    
    def _extract_sql_elements(self, sql_query: str) -> Tuple[Set[str], Set[Dict], List[Dict]]:
        """
        Extract tables, columns, and joins from SQL query
        
        Args:
            sql_query: SQL query to analyze
            
        Returns:
            Tuple of (tables, columns, joins)
        """
        tables = set()
        columns = set()
        joins = []
        
        try:
            parsed = sqlparse.parse(sql_query)[0]
            
            # More targeted approach: only extract identifiers from specific contexts
            # Don't just grab all identifiers as they might be column names
            
            # More sophisticated parsing for tables and columns
            sql_upper = sql_query.upper()
            
            # Extract FROM clause tables - more precise patterns
            from_patterns = [
                r'FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*(?:\.[a-zA-Z_][a-zA-Z0-9_.]*)*)',  # Qualified table names
                r'FROM\s+`([^`]+)`',  # Backtick quoted table names
                r'FROM\s+([a-zA-Z_]\w*)',  # Simple table names
            ]
            
            for pattern in from_patterns:
                from_matches = re.findall(pattern, sql_query, re.IGNORECASE)  # Use original case
                for match in from_matches:
                    clean_table = self._clean_identifier(match)
                    if clean_table and not self._is_likely_column_name(clean_table, sql_query):
                        tables.add(clean_table)
            
            # Extract JOIN clause tables - more precise patterns
            join_patterns = [
                r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_.]*(?:\.[a-zA-Z_][a-zA-Z0-9_.]*)*)',  # Qualified table names  
                r'JOIN\s+`([^`]+)`',  # Backtick quoted table names
                r'JOIN\s+([a-zA-Z_]\w*)',  # Simple table names
            ]
            
            for pattern in join_patterns:
                join_matches = re.findall(pattern, sql_query, re.IGNORECASE)  # Use original case
                for match in join_matches:
                    clean_table = self._clean_identifier(match)
                    if clean_table and not self._is_likely_column_name(clean_table, sql_query):
                        tables.add(clean_table)
            
            # Also try to extract table names from WITH clauses, subqueries, etc.
            # Extract table names after WITH keyword
            with_matches = re.findall(r'WITH\s+(\w+)\s+AS', sql_upper)
            for match in with_matches:
                clean_table = self._clean_identifier(match)
                if clean_table:
                    tables.add(clean_table.lower())
            
            # Extract columns with table context
            columns = self._extract_columns_with_tables(sql_query, tables)
            
            logger.debug(f"Extracted {len(tables)} tables from SQL: {list(tables)}")
            logger.debug(f"Extracted {len(columns)} columns from SQL: {list(columns)}")
            
        except Exception as e:
            logger.error(f"Error extracting SQL elements: {e}")
        
        return tables, columns, joins
    
    def _clean_identifier(self, identifier: str) -> Optional[str]:
        """
        Clean SQL identifier (remove quotes, aliases, etc.)
        
        Args:
            identifier: Raw identifier string
            
        Returns:
            Cleaned identifier or None if invalid
        """
        if not identifier:
            return None
        
        # Remove quotes and brackets
        cleaned = identifier.strip().strip('"').strip("'").strip('`').strip('[]')
        
        # Handle aliases (take first part before AS or space)
        cleaned = re.split(r'\s+(?:AS\s+)?', cleaned, flags=re.IGNORECASE)[0]
        
        # For BigQuery-style table names (project.dataset.table), preserve the full path
        # But also check if it looks like a fully qualified table name
        if '.' in cleaned:
            parts = cleaned.split('.')
            # If it looks like project.dataset.table format, keep the full path
            if len(parts) == 3:
                # Keep full BigQuery table identifier
                pass  
            elif len(parts) == 2:
                # Could be dataset.table, keep full path
                pass
            else:
                # More than 3 parts, take the last part as table name
                cleaned = parts[-1]
        
        # Validate it's not a SQL keyword
        if cleaned.upper() in self.sql_keywords:
            return None
        
        return cleaned if cleaned else None
    
    def _is_likely_column_name(self, identifier: str, sql_query: str) -> bool:
        """
        Check if an identifier is likely a column name rather than a table name.
        
        Args:
            identifier: The identifier to check
            sql_query: The full SQL query for context
            
        Returns:
            True if this looks like a column name
        """
        if not identifier:
            return True
        
        # Skip the SELECT clause check - it's too broad and catches table names
        # Tables can appear in SELECT with dot notation (e.g., table.column)
        
        # If it contains common column suffixes (but not if it has dots - likely a table)
        if '.' not in identifier:
            column_suffixes = ['_id', '_name', '_date', '_time', '_count', '_amount', '_total']
            if any(identifier.endswith(suffix) for suffix in column_suffixes):
                return True
        
        # If it's a common aggregate function result
        if identifier.lower() in ['count(*)', 'sum(*)', 'avg(*)', 'min(*)', 'max(*)', 'count', 'sum', 'avg', 'min', 'max']:
            return True
        
        # If it has 3 dots, it's definitely a BigQuery table name
        if identifier.count('.') >= 2:
            return False
        
        return False
    
    def _extract_columns_with_tables(self, sql_query: str, tables: Set[str]) -> Set[Dict]:
        """
        Extract columns with their table context from SQL query
        
        Args:
            sql_query: SQL query to analyze
            tables: Set of tables found in the query
            
        Returns:
            Set of dictionaries with table and column information
        """
        columns = set()
        
        try:
            # Parse SQL into tokens
            parsed = sqlparse.parse(sql_query)[0]
            
            # Convert to string for pattern matching
            sql_upper = sql_query.upper()
            sql_original = sql_query
            
            # Extract SELECT clause columns
            select_patterns = [
                # Pattern for table.column references
                r'([a-zA-Z_][a-zA-Z0-9_.]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)',
                # Pattern for standalone columns in SELECT (more careful)
                r'SELECT\\s+(?:[^,]*, *)*([a-zA-Z_][a-zA-Z0-9_]*)',
                # Pattern for columns in WHERE clause
                r'WHERE\\s+(?:[^,]*, *)*([a-zA-Z_][a-zA-Z0-9_]*)',
                # Pattern for columns in GROUP BY
                r'GROUP\\s+BY\\s+(?:[^,]*, *)*([a-zA-Z_][a-zA-Z0-9_]*)',
                # Pattern for columns in ORDER BY  
                r'ORDER\\s+BY\\s+(?:[^,]*, *)*([a-zA-Z_][a-zA-Z0-9_]*)',
                # Pattern for columns in ON clause (JOINs)
                r'ON\\s+(?:[^,]*, *)*([a-zA-Z_][a-zA-Z0-9_]*)',
            ]
            
            # Extract table.column references (most reliable)
            table_column_pattern = r'([a-zA-Z_][a-zA-Z0-9_.]*)\\.([a-zA-Z_][a-zA-Z0-9_]*)'
            table_column_matches = re.findall(table_column_pattern, sql_original, re.IGNORECASE)
            
            for table_ref, column_name in table_column_matches:
                clean_table = self._clean_identifier(table_ref)
                clean_column = self._clean_identifier(column_name)
                
                if clean_table and clean_column:
                    # Map table aliases to actual table names if possible
                    actual_table = self._resolve_table_alias(clean_table, tables, sql_query)
                    columns.add(frozenset([('table', actual_table), ('column', clean_column)]))
            
            # Extract standalone column references (more challenging, needs context)
            # Look for patterns that are likely column references in known contexts
            standalone_patterns = [
                # Columns after SELECT keyword (basic pattern)
                r'SELECT\\s+(?:DISTINCT\\s+)?([a-zA-Z_][a-zA-Z0-9_]*)',
                # Columns after commas in SELECT
                r',\\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                # Columns in WHERE conditions
                r'WHERE\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*[=<>!]',
                # Columns in HAVING conditions  
                r'HAVING\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*[=<>!]',
                # Columns in GROUP BY
                r'GROUP\\s+BY\\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                # Columns in ORDER BY
                r'ORDER\\s+BY\\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                # Columns in aggregate functions
                r'(?:COUNT|SUM|AVG|MIN|MAX|DISTINCT)\\s*\\(\\s*([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\)',
            ]
            
            for pattern in standalone_patterns:
                matches = re.findall(pattern, sql_original, re.IGNORECASE)
                for match in matches:
                    clean_column = self._clean_identifier(match)
                    if clean_column and not self._is_sql_keyword(clean_column):
                        # Try to infer table from context or default to first table
                        inferred_table = self._infer_table_for_column(clean_column, tables, sql_query)
                        if inferred_table:
                            columns.add(frozenset([('table', inferred_table), ('column', clean_column)]))
            
            # Convert frozenset back to dict for easier handling
            result_columns = set()
            for col_set in columns:
                col_dict = dict(col_set)
                result_columns.add(frozenset(col_dict.items()))
            
        except Exception as e:
            logger.error(f"Error extracting columns: {e}")
        
        return result_columns
    
    def _resolve_table_alias(self, table_ref: str, tables: Set[str], sql_query: str) -> str:
        """
        Resolve table alias to actual table name
        
        Args:
            table_ref: Table reference (could be alias)
            tables: Set of actual table names
            sql_query: Full SQL query for context
            
        Returns:
            Actual table name
        """
        # If table_ref is already in tables, return it
        if table_ref.lower() in [t.lower() for t in tables]:
            return table_ref
        
        # Look for alias patterns like "FROM actual_table alias" or "FROM actual_table AS alias"
        alias_patterns = [
            rf'FROM\\s+([a-zA-Z_][a-zA-Z0-9_.]*(?:\\.[a-zA-Z_][a-zA-Z0-9_.]*)*)`?\\s+(?:AS\\s+)?{re.escape(table_ref)}\\b',
            rf'JOIN\\s+([a-zA-Z_][a-zA-Z0-9_.]*(?:\\.[a-zA-Z_][a-zA-Z0-9_.]*)*)`?\\s+(?:AS\\s+)?{re.escape(table_ref)}\\b'
        ]
        
        for pattern in alias_patterns:
            matches = re.findall(pattern, sql_query, re.IGNORECASE)
            for match in matches:
                clean_match = self._clean_identifier(match)
                if clean_match and clean_match.lower() in [t.lower() for t in tables]:
                    return clean_match
        
        # Default: return the table_ref as-is or first table if only one
        if len(tables) == 1:
            return list(tables)[0]
        
        return table_ref
    
    def _infer_table_for_column(self, column_name: str, tables: Set[str], sql_query: str) -> Optional[str]:
        """
        Infer which table a standalone column belongs to
        
        Args:
            column_name: Column name
            tables: Available tables
            sql_query: SQL query for context
            
        Returns:
            Inferred table name or None
        """
        # If only one table, assume it belongs to that table
        if len(tables) == 1:
            return list(tables)[0]
        
        # Try to find the column in schema if available
        if self.schema_manager and hasattr(self.schema_manager, 'get_table_columns'):
            for table in tables:
                table_columns = self.schema_manager.get_table_columns(table)
                if column_name.lower() in [col.lower() for col in table_columns]:
                    return table
        
        # Default to first table (not ideal but better than nothing)
        return list(tables)[0] if tables else None
    
    def _is_sql_keyword(self, word: str) -> bool:
        """
        Check if word is a SQL keyword
        
        Args:
            word: Word to check
            
        Returns:
            True if word is a SQL keyword
        """
        return word.upper() in self.sql_keywords
    
    def _validate_table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in schema
        
        Args:
            table_name: Table name to validate
            
        Returns:
            True if table exists
        """
        if not self.schema_manager:
            return True  # Cannot validate without schema manager
        
        try:
            # Check if table exists in schema manager
            # The schema manager should have a method to check table existence
            if hasattr(self.schema_manager, 'get_table_info'):
                table_info = self.schema_manager.get_table_info(table_name)
                return table_info is not None
            
            # Fallback: check if table name appears in any schema table IDs
            if hasattr(self.schema_manager, 'schema_df') and self.schema_manager.schema_df is not None:
                schema_df = self.schema_manager.schema_df
                if len(schema_df) > 0:
                    # Handle both possible column names: 'tableid' or 'table_id'
                    table_col = 'tableid' if 'tableid' in schema_df.columns else 'table_id'
                    table_matches = schema_df[table_col].str.contains(table_name, case=False, na=False)
                    logger.debug(f"Checking table '{table_name}' against {len(schema_df)} schema rows using column '{table_col}'")
                    return table_matches.any()
                else:
                    logger.warning("Schema DataFrame is empty")
            
            return True  # Default to valid if cannot check
            
        except Exception as e:
            logger.error(f"Error validating table existence: {e}")
            return True  # Default to valid on error
    
    def _validate_column_exists(self, table_name: str, column_name: str) -> bool:
        """
        Check if column exists in specified table
        
        Args:
            table_name: Table name
            column_name: Column name
            
        Returns:
            True if column exists in table
        """
        if not self.schema_manager:
            return True  # Cannot validate without schema manager
        
        try:
            # Check column existence through schema manager
            if hasattr(self.schema_manager, 'get_table_columns'):
                columns = self.schema_manager.get_table_columns(table_name)
                return column_name.lower() in [col.lower() for col in columns]
            
            # Fallback: check schema DataFrame directly
            if hasattr(self.schema_manager, 'schema_df') and self.schema_manager.schema_df is not None:
                schema_df = self.schema_manager.schema_df
                if len(schema_df) > 0:
                    # Handle both possible column names
                    table_col = 'tableid' if 'tableid' in schema_df.columns else 'table_id'
                    column_col = 'columnnames' if 'columnnames' in schema_df.columns else 'column'
                    
                    table_mask = schema_df[table_col].str.contains(table_name, case=False, na=False)
                    column_mask = schema_df[column_col].str.contains(column_name, case=False, na=False)
                    logger.debug(f"Checking column '{column_name}' in table '{table_name}' against {len(schema_df)} schema rows")
                    return (table_mask & column_mask).any()
                else:
                    logger.warning("Schema DataFrame is empty for column validation")
            
            return True  # Default to valid
            
        except Exception as e:
            logger.error(f"Error validating column existence: {e}")
            return True
    
    def _validate_join(self, join_info: Dict, result: ValidationResult) -> None:
        """
        Validate JOIN relationship
        
        Args:
            join_info: JOIN information dictionary
            result: ValidationResult to update
        """
        # Basic JOIN validation - can be extended
        pass
    
    def _suggest_similar_tables(self, table_name: str) -> List[str]:
        """
        Suggest similar table names from schema
        
        Args:
            table_name: Table name that wasn't found
            
        Returns:
            List of similar table names
        """
        suggestions = []
        
        try:
            if self.schema_manager and hasattr(self.schema_manager, 'schema_df'):
                schema_df = self.schema_manager.schema_df
                # Handle both possible column names
                table_col = 'tableid' if 'tableid' in schema_df.columns else 'table_id'
                all_tables = schema_df[table_col].unique()
                
                # Simple similarity based on substring matching
                for existing_table in all_tables:
                    if table_name.lower() in existing_table.lower() or existing_table.lower() in table_name.lower():
                        # Extract just the table name from full identifier
                        simple_name = existing_table.split('.')[-1] if '.' in existing_table else existing_table
                        suggestions.append(simple_name)
                
                # Limit suggestions
                return suggestions[:3]
                
        except Exception as e:
            logger.error(f"Error generating table suggestions: {e}")
        
        return suggestions
    
    def _suggest_similar_columns(self, table_name: str, column_name: str) -> List[str]:
        """
        Suggest similar column names for the specified table
        
        Args:
            table_name: Table name
            column_name: Column name that wasn't found
            
        Returns:
            List of similar column names
        """
        suggestions = []
        
        try:
            if self.schema_manager and hasattr(self.schema_manager, 'schema_df'):
                schema_df = self.schema_manager.schema_df
                
                # Handle both possible column names
                table_col = 'tableid' if 'tableid' in schema_df.columns else 'table_id'
                column_col = 'columnnames' if 'columnnames' in schema_df.columns else 'column'
                
                # Get columns for tables that match the table name
                table_mask = schema_df[table_col].str.contains(table_name, case=False, na=False)
                table_columns = schema_df[table_mask][column_col].unique()
                
                # Find similar column names
                for existing_column in table_columns:
                    if (column_name.lower() in existing_column.lower() or 
                        existing_column.lower() in column_name.lower()):
                        suggestions.append(existing_column)
                
                return suggestions[:3]
                
        except Exception as e:
            logger.error(f"Error generating column suggestions: {e}")
        
        return suggestions
    
    def _validate_bigquery_data_types(self, sql_query: str, result: ValidationResult) -> None:
        """
        Validate BigQuery-specific data type usage patterns
        
        Args:
            sql_query: SQL query to validate
            result: ValidationResult to update
        """
        sql_upper = sql_query.upper()
        
        # Check for common BigQuery data type errors
        
        # 1. TIMESTAMP/DATETIME mixing errors
        timestamp_patterns = [
            (r'DATE_SUB\s*\(\s*CURRENT_DATE\s*\(\s*\)\s*,', 
             "Use TIMESTAMP_SUB(CURRENT_TIMESTAMP(), ...) for TIMESTAMP columns, not DATE_SUB(CURRENT_DATE(), ...)"),
            (r'>=\s*DATE_SUB\s*\(\s*CURRENT_DATE', 
             "When comparing with TIMESTAMP columns, use TIMESTAMP_SUB(CURRENT_TIMESTAMP(), ...) instead of DATE_SUB"),
            (r'<=\s*DATE_SUB\s*\(\s*CURRENT_DATE', 
             "When comparing with TIMESTAMP columns, use TIMESTAMP_SUB(CURRENT_TIMESTAMP(), ...) instead of DATE_SUB"),
        ]
        
        for pattern, error_msg in timestamp_patterns:
            if re.search(pattern, sql_upper):
                # Check if query involves TIMESTAMP columns
                if self._query_uses_timestamp_columns(sql_query):
                    result.errors.append(f"BigQuery data type error: {error_msg}")
                    result.suggestions.append("Example: WHERE timestamp_col >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)")
        
        # 2. Common casting issues
        if 'CAST(' in sql_upper:
            # Look for potentially problematic casts
            cast_patterns = [
                (r'CAST\s*\(\s*[^)]+\s+AS\s+DATETIME\s*\)', 
                 "Be careful when casting to DATETIME - ensure compatibility with column types"),
                (r'CAST\s*\(\s*[^)]+\s+AS\s+TIMESTAMP\s*\)', 
                 "When casting to TIMESTAMP, ensure the source format is compatible")
            ]
            
            for pattern, warning_msg in cast_patterns:
                if re.search(pattern, sql_upper):
                    result.warnings.append(f"BigQuery casting: {warning_msg}")
        
        # 3. Check for missing fully qualified table names
        if not re.search(r'`[^`]+\.[^`]+\.[^`]+`', sql_query):
            if any(table in sql_query for table in ['FROM ', 'JOIN ']):
                result.warnings.append("Consider using fully qualified table names: `project.dataset.table`")
        
        # 4. Geography function usage
        if 'GEOGRAPHY' in sql_upper and not re.search(r'ST_[A-Z]+\s*\(', sql_upper):
            result.warnings.append("When working with GEOGRAPHY columns, use ST_* functions (e.g., ST_DISTANCE, ST_INTERSECTS)")
    
    def _query_uses_timestamp_columns(self, sql_query: str) -> bool:
        """
        Check if the query uses columns that are TIMESTAMP type
        
        Args:
            sql_query: SQL query to check
            
        Returns:
            True if query uses TIMESTAMP columns
        """
        if not self.schema_manager:
            return True  # Assume yes if we can't check
        
        # Extract table and column references from query
        tables, columns, _ = self._extract_sql_elements(sql_query)
        
        for table_name in tables:
            table_schema = self.schema_manager.get_schema_for_table(table_name)
            if table_schema:
                for column_name, data_type in table_schema:
                    if data_type.upper() == 'TIMESTAMP':
                        # Check if this TIMESTAMP column is referenced in WHERE clauses or comparisons
                        column_pattern = rf'\b{re.escape(column_name)}\b'
                        if re.search(column_pattern, sql_query, re.IGNORECASE):
                            return True
        
        return False
    
    def _get_column_data_type(self, table_name: str, column_name: str) -> Optional[str]:
        """
        Get the data type of a specific column
        
        Args:
            table_name: Table name
            column_name: Column name
            
        Returns:
            Data type string or None if not found
        """
        if not self.schema_manager:
            return None
        
        table_schema = self.schema_manager.get_schema_for_table(table_name)
        if table_schema:
            for col_name, data_type in table_schema:
                if col_name.lower() == column_name.lower():
                    return data_type
        
        return None

def validate_sql_query(sql_text: str, schema_manager=None, 
                      validation_level: ValidationLevel = ValidationLevel.SCHEMA_STRICT) -> ValidationResult:
    """
    Convenience function to validate SQL query
    
    Args:
        sql_text: SQL text to validate
        schema_manager: Optional SchemaManager instance
        validation_level: Validation strictness level
        
    Returns:
        ValidationResult
    """
    validator = SQLValidator(schema_manager, validation_level)
    return validator.validate_sql(sql_text)

# Export main classes and functions
__all__ = ['SQLValidator', 'ValidationResult', 'ValidationLevel', 'validate_sql_query']
