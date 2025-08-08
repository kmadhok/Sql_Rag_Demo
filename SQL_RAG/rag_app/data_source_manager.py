#!/usr/bin/env python3
"""
Data Source Manager - Abstract interface for different data sources

Supports:
- CSV files (local testing)
- BigQuery tables (production)
- Automatic source detection
- Unified DataFrame interface
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
from abc import ABC, abstractmethod

import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    def load_data(self) -> pd.DataFrame:
        """Load data and return as DataFrame"""
        pass
    
    @abstractmethod
    def get_source_info(self) -> str:
        """Get string representation of data source for tracking"""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Get short name identifier for this source"""
        pass

class CSVDataSource(DataSource):
    """CSV file data source"""
    
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    def load_data(self) -> pd.DataFrame:
        """Load CSV file as DataFrame"""
        try:
            df = pd.read_csv(self.file_path)
            logger.info(f"Loaded CSV: {len(df)} rows from {self.file_path.name}")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV {self.file_path}: {e}")
            raise
    
    def get_source_info(self) -> str:
        """Get CSV file info for tracking"""
        stat = self.file_path.stat()
        return f"csv:{self.file_path}:size={stat.st_size}:mtime={stat.st_mtime}"
    
    def get_source_name(self) -> str:
        """Get CSV file name as source identifier"""
        return f"csv_{self.file_path.stem}"

class BigQueryDataSource(DataSource):
    """BigQuery table data source"""
    
    def __init__(self, project_id: str, query: Optional[str] = None, 
                 table_id: Optional[str] = None, client=None):
        """
        Initialize BigQuery data source
        
        Args:
            project_id: Google Cloud project ID
            query: SQL query to execute (if provided, table_id ignored)
            table_id: Full table ID (project.dataset.table)
            client: BigQuery client instance (if None, creates new)
        """
        self.project_id = project_id
        self.query = query
        self.table_id = table_id
        self.client = client
        
        if not query and not table_id:
            raise ValueError("Either query or table_id must be provided")
        
        # Import BigQuery here to avoid import errors in CSV-only environments
        try:
            from google.cloud import bigquery
            if not self.client:
                self.client = bigquery.Client(project=project_id)
        except ImportError:
            raise ImportError("google-cloud-bigquery is required for BigQuery data sources")
    
    def load_data(self) -> pd.DataFrame:
        """Load data from BigQuery as DataFrame"""
        try:
            if self.query:
                logger.info(f"Executing BigQuery query: {self.query[:100]}...")
                df = self.client.query(self.query).to_dataframe()
            else:
                logger.info(f"Loading BigQuery table: {self.table_id}")
                df = self.client.query(f"SELECT * FROM `{self.table_id}`").to_dataframe()
            
            logger.info(f"Loaded BigQuery data: {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error loading BigQuery data: {e}")
            raise
    
    def get_source_info(self) -> str:
        """Get BigQuery source info for tracking"""
        if self.query:
            # Use query hash for tracking
            import hashlib
            query_hash = hashlib.md5(self.query.encode()).hexdigest()[:8]
            return f"bigquery:{self.project_id}:query_hash={query_hash}"
        else:
            return f"bigquery:{self.table_id}"
    
    def get_source_name(self) -> str:
        """Get BigQuery source name"""
        if self.query:
            return f"bq_query"
        else:
            # Extract table name from table_id
            table_name = self.table_id.split('.')[-1] if self.table_id else "unknown"
            return f"bq_{table_name}"

class DataSourceManager:
    """Manager for different data sources with automatic detection"""
    
    @staticmethod
    def create_csv_source(file_path: Union[str, Path]) -> CSVDataSource:
        """Create CSV data source"""
        return CSVDataSource(file_path)
    
    @staticmethod
    def create_bigquery_source(project_id: str, query: Optional[str] = None,
                              table_id: Optional[str] = None, client=None) -> BigQueryDataSource:
        """Create BigQuery data source"""
        return BigQueryDataSource(project_id, query, table_id, client)
    
    @staticmethod
    def auto_detect_source(csv_path: Optional[Union[str, Path]] = None,
                          bigquery_project: Optional[str] = None,
                          bigquery_query: Optional[str] = None,
                          bigquery_table: Optional[str] = None,
                          prefer_bigquery: bool = True) -> DataSource:
        """
        Automatically detect and create appropriate data source
        
        Args:
            csv_path: Path to CSV file
            bigquery_project: BigQuery project ID
            bigquery_query: BigQuery SQL query
            bigquery_table: BigQuery table ID
            prefer_bigquery: Prefer BigQuery if both sources available
            
        Returns:
            Appropriate DataSource instance
        """
        has_csv = csv_path and Path(csv_path).exists()
        has_bigquery = bigquery_project and (bigquery_query or bigquery_table)
        
        if has_bigquery and (prefer_bigquery or not has_csv):
            logger.info("Using BigQuery data source")
            return DataSourceManager.create_bigquery_source(
                bigquery_project, bigquery_query, bigquery_table
            )
        elif has_csv:
            logger.info(f"Using CSV data source: {csv_path}")
            return DataSourceManager.create_csv_source(csv_path)
        else:
            raise ValueError("No valid data source found (CSV file or BigQuery config)")
    
    @staticmethod
    def load_from_environment() -> DataSource:
        """
        Load data source from environment variables
        
        Environment variables:
        - CSV_FILE_PATH: Path to CSV file
        - BIGQUERY_PROJECT: BigQuery project ID
        - BIGQUERY_QUERY: BigQuery SQL query
        - BIGQUERY_TABLE: BigQuery table ID
        - PREFER_BIGQUERY: "true" to prefer BigQuery (default: true)
        """
        csv_path = os.getenv('CSV_FILE_PATH')
        bq_project = os.getenv('BIGQUERY_PROJECT')
        bq_query = os.getenv('BIGQUERY_QUERY')
        bq_table = os.getenv('BIGQUERY_TABLE')
        prefer_bq = os.getenv('PREFER_BIGQUERY', 'true').lower() == 'true'
        
        return DataSourceManager.auto_detect_source(
            csv_path=csv_path,
            bigquery_project=bq_project,
            bigquery_query=bq_query,
            bigquery_table=bq_table,
            prefer_bigquery=prefer_bq
        )

def load_data_with_fallback(primary_source: DataSource, 
                           fallback_csv_path: Optional[Union[str, Path]] = None) -> Tuple[pd.DataFrame, str]:
    """
    Load data with automatic fallback to CSV if primary source fails
    
    Args:
        primary_source: Primary data source to try first
        fallback_csv_path: CSV file to use as fallback
        
    Returns:
        Tuple of (DataFrame, source_description)
    """
    try:
        df = primary_source.load_data()
        return df, primary_source.get_source_info()
    except Exception as e:
        logger.warning(f"Primary source failed: {e}")
        
        if fallback_csv_path and Path(fallback_csv_path).exists():
            logger.info(f"Falling back to CSV: {fallback_csv_path}")
            fallback_source = CSVDataSource(fallback_csv_path)
            df = fallback_source.load_data()
            return df, f"fallback_{fallback_source.get_source_info()}"
        else:
            raise Exception(f"Primary source failed and no valid fallback available: {e}")