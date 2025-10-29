"""
SQL Service for safe SQL execution and validation
"""
import logging
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPICallError
from .rag_service import rag_service

logger = logging.getLogger(__name__)

class SQLService:
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize BigQuery client"""
        try:
            self.client = bigquery.Client()
            logger.info("BigQuery client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    async def execute_query(
        self, 
        sql: str, 
        dry_run: bool = False,
        max_bytes_billed: int = 100000000
    ) -> Dict[str, Any]:
        """
        Execute SQL query with safety checks
        
        Args:
            sql: SQL query to execute
            dry_run: If True, only validate without executing
            max_bytes_billed: Maximum bytes to process
        
        Returns:
            Dictionary with execution results
        """
        try:
            # Validate SQL
            validation_result = await self._validate_sql(sql)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error_message': validation_result['error'],
                    'total_rows': 0,
                    'cost': 0.0,
                    'bytes_processed': 0,
                    'execution_time': 0.0,
                    'data': None,
                    'column_types': None
                }
            
            # Configure job
            job_config = bigquery.QueryJobConfig(
                dry_run=dry_run,
                use_query_cache=not dry_run,
                maximum_bytes_billed=max_bytes_billed
            )
            
            # Start query
            logger.info(f"Executing SQL (dry_run={dry_run}): {sql[:100]}...")
            
            query_job = self.client.query(sql, job_config=job_config)
            
            if dry_run:
                return {
                    'success': True,
                    'dry_run': True,
                    'total_rows': query_job.num_dml_affected_rows if hasattr(query_job, 'num_dml_affected_rows') else 0,
                    'cost': 0.0,
                    'bytes_processed': query_job.total_bytes_processed,
                    'execution_time': 0.0,
                    'data': None,
                    'column_types': None,
                    'message': 'Query validated successfully'
                }
            
            # Execute query and get results
            results = query_job.result()
            
            # Convert to list of dictionaries
            data = []
            column_types = {}
            
            if results:
                # Get schema information
                for field in results.schema:
                    column_types[field.name] = field.field_type
                
                # Convert rows to dictionaries
                for row in results:
                    row_dict = {}
                    for i, field in enumerate(results.schema):
                        row_dict[field.name] = row[i]
                    data.append(row_dict)
            
            # Calculate estimated cost (simplified)
            cost = (query_job.total_bytes_processed / 1024 / 1024 / 1024) * 6.0  # $6 per TB
            
            return {
                'success': True,
                'total_rows': len(data),
                'cost': cost,
                'bytes_processed': query_job.total_bytes_processed,
                'execution_time': 0.0,  # Would need to measure this properly
                'data': data,
                'column_types': column_types
            }
            
        except GoogleAPICallError as e:
            logger.error(f"BigQuery error: {e}")
            return {
                'success': False,
                'error_message': f"BigQuery error: {str(e)}",
                'total_rows': 0,
                'cost': 0.0,
                'bytes_processed': 0,
                'execution_time': 0.0,
                'data': None,
                'column_types': None
            }
        except Exception as e:
            logger.error(f"Unexpected error executing SQL: {e}")
            return {
                'success': False,
                'error_message': f"Unexpected error: {str(e)}",
                'total_rows': 0,
                'cost': 0.0,
                'bytes_processed': 0,
                'execution_time': 0.0,
                'data': None,
                'column_types': None
            }
    
    async def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL for safety
        
        Args:
            sql: SQL query to validate
        
        Returns:
            Dictionary with validation result
        """
        sql_upper = sql.upper().strip()
        
        # Check for dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE'
        ]
        
        for keyword in dangerous_keywords:
            if f' {keyword} ' in f' {sql_upper} ' or sql_upper.startswith(keyword):
                return {
                    'valid': False,
                    'error': f'Dangerous operation {keyword} is not allowed'
                }
        
        # Basic SQL syntax validation
        if not sql_upper.startswith(('SELECT', 'WITH', 'SHOW', 'DESCRIBE')):
            return {
                'valid': False,
                'error': 'Only SELECT queries are allowed'
            }
        
        # Check for proper termination
        if not sql.rstrip().endswith(';'):
            return {
                'valid': False,
                'error': 'SQL query must end with semicolon (;)'
            }
        
        return {
            'valid': True,
            'error': None
        }

# Global instance
sql_service = SQLService()