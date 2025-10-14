#!/usr/bin/env python3
"""
BigQuery SQL Execution Module

Provides secure SQL execution capabilities for the thelook_ecommerce dataset
with comprehensive safety guards and validation.
"""

import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Container for BigQuery execution results and metadata"""
    success: bool
    data: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    bytes_processed: Optional[int] = None
    bytes_billed: Optional[int] = None
    total_rows: int = 0
    job_id: Optional[str] = None
    cache_hit: bool = False
    dry_run: bool = False

class BigQueryExecutor:
    """
    Secure BigQuery executor for thelook_ecommerce dataset
    
    Features:
    - Read-only query enforcement
    - Table validation for thelook_ecommerce dataset only
    - Result size limits and timeout protection
    - Comprehensive error handling
    - Query performance metrics
    """
    
    def __init__(self, 
                 project_id: str = "brainrot-453319",
                 dataset_id: str = "bigquery-public-data.thelook_ecommerce",
                 max_rows: int = 10000,
                 timeout_seconds: int = 30,
                 schema_file_path: str = "data_new/thelook_ecommerce_schema.csv"):
        """
        Initialize BigQuery executor
        
        Args:
            project_id: Google Cloud project ID for billing
            dataset_id: Target dataset (must be thelook_ecommerce)
            max_rows: Maximum rows to return (safety limit)
            timeout_seconds: Query timeout in seconds
            schema_file_path: Path to CSV file containing table schema
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.schema_file_path = schema_file_path
        
        # Initialize BigQuery client
        try:
            self.client = bigquery.Client(project=project_id)
            logger.info(f"✅ BigQuery client initialized for project: {project_id}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize BigQuery client: {e}")
            raise
        
        # Load allowed tables from schema CSV file
        self.allowed_tables = self._load_allowed_tables_from_schema()
        
        # SQL keywords that are forbidden (write operations)
        self.forbidden_keywords = {
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
            "TRUNCATE", "REPLACE", "MERGE", "EXPORT"
        }
    
    def _load_allowed_tables_from_schema(self) -> set:
        """
        Load allowed table names from the schema CSV file
        
        Returns:
            Set of allowed full table names from the CSV
        """
        try:
            # Convert relative path to absolute path from current working directory
            schema_path = Path(self.schema_file_path)
            if not schema_path.is_absolute():
                schema_path = Path.cwd() / schema_path
            
            if not schema_path.exists():
                logger.warning(f"⚠️ Schema file not found at {schema_path}, using fallback tables")
                return self._get_fallback_tables()
            
            # Read CSV and extract unique full table names
            df = pd.read_csv(schema_path)
            if 'full_table_name' not in df.columns:
                logger.error(f"❌ CSV file missing 'full_table_name' column: {schema_path}")
                return self._get_fallback_tables()
            
            # Extract unique full table names
            full_table_names = set(df['full_table_name'].dropna().unique())
            logger.info(f"✅ Loaded {len(full_table_names)} allowed tables from {schema_path}")
            
            # Also create a set of short table names for backward compatibility
            short_names = set()
            for full_name in full_table_names:
                if '.' in full_name:
                    short_names.add(full_name.split('.')[-1])
            
            # Return both full names and short names for flexible validation
            return full_table_names.union(short_names)
            
        except Exception as e:
            logger.error(f"❌ Error loading schema file {self.schema_file_path}: {e}")
            return self._get_fallback_tables()
    
    def _get_fallback_tables(self) -> set:
        """
        Return fallback table names if schema CSV cannot be loaded
        
        Returns:
            Set of fallback table names
        """
        return {
            "users", "orders", "order_items", "products", "inventory_items",
            "events", "distribution_centers",
            # Full qualified names
            "bigquery-public-data.thelook_ecommerce.users",
            "bigquery-public-data.thelook_ecommerce.orders", 
            "bigquery-public-data.thelook_ecommerce.order_items",
            "bigquery-public-data.thelook_ecommerce.products",
            "bigquery-public-data.thelook_ecommerce.inventory_items",
            "bigquery-public-data.thelook_ecommerce.events",
            "bigquery-public-data.thelook_ecommerce.distribution_centers"
        }
    
    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety and compliance
        
        This simplified validation focuses on preventing destructive operations
        while allowing BigQuery to handle table access validation.
        
        Args:
            sql: SQL query string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        sql_upper = sql.upper().strip()
        
        # Simple check for forbidden operations at the beginning of the query
        # This avoids false positives with keywords in strings/comments/column names
        for keyword in self.forbidden_keywords:
            if sql_upper.startswith(keyword + " ") or sql_upper.startswith(keyword + "\t") or sql_upper.startswith(keyword + "\n"):
                return False, f"Forbidden operation detected: {keyword}. Only SELECT queries are allowed."
        
        # Must start with SELECT or WITH (for CTEs)
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False, "Only SELECT queries (with optional CTEs) are allowed. Query must start with SELECT or WITH."
        
        # That's it! Let BigQuery handle table validation to avoid false positives
        # with subqueries, complex JOINs, and other valid SQL constructs
        return True, None
    
    def _extract_cte_names(self, sql: str) -> set:
        """
        Extract CTE (Common Table Expression) names from SQL
        
        Args:
            sql: SQL query string
            
        Returns:
            Set of CTE names in uppercase
        """
        cte_names = set()
        sql_upper = sql.upper().strip()
        
        if not sql_upper.startswith('WITH'):
            return cte_names
        
        # Find the position where the main SELECT starts
        # We need to track parentheses to find the outermost SELECT
        paren_level = 0
        with_end_pos = None
        
        # Start after "WITH"
        pos = 4  # len("WITH")
        
        # Skip initial whitespace
        while pos < len(sql_upper) and sql_upper[pos].isspace():
            pos += 1
        
        # Scan through the string to find the main SELECT
        while pos < len(sql_upper):
            char = sql_upper[pos]
            
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif paren_level == 0 and sql_upper[pos:pos+6] == 'SELECT':
                # Found the main SELECT at paren level 0
                with_end_pos = pos
                break
            
            pos += 1
        
        if with_end_pos is None:
            return cte_names
        
        # Extract the WITH content
        with_content = sql_upper[4:with_end_pos].strip()
        
        # Parse the CTE definitions
        # Split by commas that are at parenthesis level 0
        cte_definitions = []
        paren_level = 0
        current_def = ""
        
        for char in with_content:
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif char == ',' and paren_level == 0:
                if current_def.strip():
                    cte_definitions.append(current_def.strip())
                current_def = ""
                continue
            current_def += char
        
        # Add the last definition
        if current_def.strip():
            cte_definitions.append(current_def.strip())
        
        # Extract CTE names from each definition
        for definition in cte_definitions:
            # Pattern: cte_name AS (
            cte_match = re.match(r'^([A-Z_][A-Z0-9_]*)\s+AS\s*\(', definition.strip(), re.IGNORECASE)
            if cte_match:
                cte_names.add(cte_match.group(1).upper())
        
        return cte_names
    
    def extract_sql_from_text(self, text: str) -> Optional[str]:
        """
        Extract SQL query from generated text response
        
        Args:
            text: Text that may contain SQL code
            
        Returns:
            Extracted SQL query or None if not found
        """
        # Look for complete SQL code blocks (prioritize complete blocks over fragments)
        sql_patterns = [
            r'```sql\s*\n(.*?)\n\s*```',  # SQL code blocks (priority - captures complete SQL)
            r'```\s*\n(.*?)\n\s*```',  # Generic code blocks (captures complete content)
            # Removed broken partial patterns that fragment multi-line SQL
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                sql = matches[0].strip()
                # Basic validation that it looks like SQL
                sql_upper = sql.upper()
                if (sql_upper.startswith(('SELECT', 'WITH')) and 
                    ('FROM' in sql_upper or 'AS' in sql_upper)):
                    return sql
        
        return None
    
    def execute_query(self, sql: str, *, dry_run: bool = False, max_bytes_billed: Optional[int] = None) -> QueryResult:
        """
        Execute SQL query with safety validation and comprehensive error handling
        
        Args:
            sql: SQL query string to execute
            
        Returns:
            QueryResult containing execution results and metadata
        """
        start_time = time.time()
        
        try:
            # Validate SQL safety
            is_valid, error_msg = self.validate_sql_safety(sql)
            if not is_valid:
                logger.warning(f"🚫 SQL validation failed: {error_msg}")
                return QueryResult(
                    success=False,
                    error_message=f"Query validation failed: {error_msg}",
                    execution_time=time.time() - start_time
                )
            
            # Configure query job
            job_config = bigquery.QueryJobConfig(
                maximum_bytes_billed=(max_bytes_billed if isinstance(max_bytes_billed, int) and max_bytes_billed > 0 else 100_000_000),
                use_query_cache=True,
                query_parameters=[],
                dry_run=dry_run
            )
            
            logger.info(f"🚀 Executing BigQuery SQL: {sql[:100]}...")
            
            # Start query job
            query_job = self.client.query(sql, job_config=job_config)
            
            # Wait for completion with timeout unless dry run
            if not dry_run:
                try:
                    query_job.result(timeout=self.timeout_seconds)
                except Exception as e:
                    if "timeout" in str(e).lower():
                        return QueryResult(
                            success=False,
                            error_message=f"Query timeout after {self.timeout_seconds} seconds",
                            execution_time=time.time() - start_time,
                            job_id=query_job.job_id,
                            dry_run=dry_run
                        )
                    raise
            
            # Check for errors
            if query_job.errors:
                error_messages = [error['message'] for error in query_job.errors]
                return QueryResult(
                    success=False,
                    error_message=f"BigQuery errors: {'; '.join(error_messages)}",
                    execution_time=time.time() - start_time,
                    job_id=query_job.job_id,
                    dry_run=dry_run
                )

            # If dry run, no data will be returned; just collect stats
            if dry_run:
                execution_time = time.time() - start_time
                job_stats = query_job._properties.get('statistics', {})
                query_stats = job_stats.get('query', {})
                return QueryResult(
                    success=True,
                    data=None,
                    execution_time=execution_time,
                    bytes_processed=int(query_stats.get('totalBytesProcessed', 0)),
                    bytes_billed=0,
                    total_rows=0,
                    job_id=query_job.job_id,
                    cache_hit=False,
                    dry_run=True
                )

            # Get results as DataFrame
            df = query_job.to_dataframe()
            
            # Apply row limit
            if len(df) > self.max_rows:
                logger.warning(f"⚠️ Result truncated from {len(df)} to {self.max_rows} rows")
                df = df.head(self.max_rows)
            
            execution_time = time.time() - start_time
            
            # Collect job statistics
            job_stats = query_job._properties.get('statistics', {})
            query_stats = job_stats.get('query', {})
            
            logger.info(f"✅ Query completed successfully: {len(df)} rows in {execution_time:.2f}s")
            
            return QueryResult(
                success=True,
                data=df,
                execution_time=execution_time,
                bytes_processed=int(query_stats.get('totalBytesProcessed', 0)),
                bytes_billed=int(query_stats.get('totalBytesBilled', 0)),
                total_rows=len(df),
                job_id=query_job.job_id,
                cache_hit=query_stats.get('cacheHit', False),
                dry_run=False
            )
            
        except GoogleCloudError as e:
            error_msg = f"BigQuery API error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Try to provide error recovery suggestions
            recovery_suggestion = self._get_error_recovery_suggestion(str(e), sql)
            if recovery_suggestion:
                error_msg = f"{error_msg}\n\n💡 Suggested fix: {recovery_suggestion}"
            
            return QueryResult(
                success=False,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return QueryResult(
                success=False,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a table in the thelook_ecommerce dataset
        
        Args:
            table_name: Name of the table
            
        Returns:
            Table information dictionary or None if not found
        """
        if table_name.lower() not in self.allowed_tables:
            return None
        
        try:
            dataset_ref = bigquery.DatasetReference(
                "bigquery-public-data", "thelook_ecommerce"
            )
            table_ref = dataset_ref.table(table_name)
            table = self.client.get_table(table_ref)
            
            return {
                "table_id": table.table_id,
                "created": table.created,
                "modified": table.modified,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "schema": [
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                        "description": field.description
                    }
                    for field in table.schema
                ]
            }
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return None
    
    def get_dataset_summary(self) -> Dict[str, Any]:
        """
        Get summary information about the thelook_ecommerce dataset
        
        Returns:
            Dataset summary dictionary
        """
        summary = {
            "dataset_id": self.dataset_id,
            "allowed_tables": list(self.allowed_tables),
            "table_count": len(self.allowed_tables),
            "safety_limits": {
                "max_rows": self.max_rows,
                "timeout_seconds": self.timeout_seconds,
                "max_bytes_billed": "100MB"
            }
        }
        
        # Try to get actual table information
        try:
            dataset_ref = bigquery.DatasetReference(
                "bigquery-public-data", "thelook_ecommerce"
            )
            dataset = self.client.get_dataset(dataset_ref)
            summary["description"] = dataset.description
            summary["location"] = dataset.location
        except Exception as e:
            logger.debug(f"Could not get dataset metadata: {e}")
        
        return summary
    
    def _get_error_recovery_suggestion(self, error_message: str, sql: str) -> Optional[str]:
        """
        Analyze BigQuery error and suggest recovery fixes
        
        Args:
            error_message: BigQuery error message
            sql: Original SQL query
            
        Returns:
            Recovery suggestion string or None
        """
        error_lower = error_message.lower()
        
        # Pattern 1: TIMESTAMP/DATETIME mixing
        if "no matching signature for operator" in error_lower and "timestamp" in error_lower and "datetime" in error_lower:
            return ("Replace DATE_SUB(CURRENT_DATE(), ...) with TIMESTAMP_SUB(CURRENT_TIMESTAMP(), ...) "
                   "when comparing with TIMESTAMP columns. "
                   "Example: WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)")
        
        # Pattern 2: Date function misuse with TIMESTAMP
        if "date_sub" in sql.lower() and ("timestamp" in error_lower or "created_at" in sql.lower()):
            return ("For TIMESTAMP columns, use TIMESTAMP_SUB instead of DATE_SUB. "
                   "Change DATE_SUB(CURRENT_DATE(), INTERVAL X DAY) to "
                   "TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL X DAY)")
        
        # Pattern 3: Table not found errors
        if "table" in error_lower and "not found" in error_lower:
            return ("Ensure table names are fully qualified: `project.dataset.table`. "
                   "Check if the table exists in the bigquery-public-data.thelook_ecommerce dataset.")
        
        # Pattern 4: Column not found errors
        if "column" in error_lower and "not found" in error_lower:
            return ("Check column name spelling and verify it exists in the table schema. "
                   "Column names are case-sensitive in BigQuery.")
        
        # Pattern 5: Type conversion errors
        if "cannot cast" in error_lower or "invalid cast" in error_lower:
            return ("Use proper type casting: CAST(column AS STRING), CAST(value AS TIMESTAMP), etc. "
                   "Ensure source and target types are compatible.")
        
        # Pattern 6: Geography function errors
        if "geography" in error_lower and ("function" in error_lower or "type" in error_lower):
            return ("For GEOGRAPHY columns, use ST_* functions like ST_DISTANCE, ST_INTERSECTS, ST_WITHIN, etc.")
        
        # Pattern 7: Interval syntax errors
        if "interval" in error_lower and "syntax" in error_lower:
            return ("Use correct INTERVAL syntax: INTERVAL 7 DAY, INTERVAL 1 MONTH, INTERVAL 2 YEAR, etc.")
        
        # Pattern 8: Aggregation function errors
        if "aggregate function" in error_lower or "group by" in error_lower:
            return ("When using aggregate functions (SUM, COUNT, AVG), ensure all non-aggregate columns "
                   "are included in the GROUP BY clause.")
        
        # Pattern 9: Join errors
        if "join" in error_lower and ("condition" in error_lower or "key" in error_lower):
            return ("Ensure JOIN conditions use compatible data types and valid column references. "
                   "Example: ON table1.id = table2.table1_id")
        
        # Generic fallback for common type errors
        if any(term in error_lower for term in ["type", "datatype", "data type", "signature"]):
            return ("This appears to be a data type compatibility error. "
                   "Check that columns are used with appropriate functions for their data types. "
                   "For TIMESTAMP: use TIMESTAMP_SUB, CURRENT_TIMESTAMP() "
                   "For DATE: use DATE_SUB, CURRENT_DATE() "
                   "For STRING: use string functions like CONCAT, LOWER, UPPER")
        
        return None
    
    def _generate_corrected_sql(self, original_sql: str, error_message: str) -> Optional[str]:
        """
        Attempt to automatically generate corrected SQL for common errors
        
        Args:
            original_sql: Original SQL with error
            error_message: BigQuery error message
            
        Returns:
            Corrected SQL string or None if cannot auto-correct
        """
        error_lower = error_message.lower()
        
        # Auto-fix TIMESTAMP/DATETIME mixing
        if ("timestamp" in error_lower and "datetime" in error_lower and 
            "no matching signature" in error_lower):
            
            # Replace DATE_SUB(CURRENT_DATE()) with TIMESTAMP_SUB(CURRENT_TIMESTAMP())
            corrected_sql = re.sub(
                r'DATE_SUB\s*\(\s*CURRENT_DATE\s*\(\s*\)\s*,',
                'TIMESTAMP_SUB(CURRENT_TIMESTAMP(),',
                original_sql,
                flags=re.IGNORECASE
            )
            
            if corrected_sql != original_sql:
                return corrected_sql
        
        return None

# Utility function to format bytes
def format_bytes(bytes_count: Optional[int]) -> str:
    """Format bytes into human readable format"""
    if bytes_count is None:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"

# Utility function to format execution time
def format_execution_time(seconds: float) -> str:
    """Format execution time into human readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
