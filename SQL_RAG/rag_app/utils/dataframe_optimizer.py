"""Optimized DataFrame operations with fallback support"""

import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Union

from config.app_config import app_config

logger = logging.getLogger(__name__)

class DataFrameOptimizer:
    """Optimized DataFrame operations with legacy fallback"""
    
    def __init__(self, optimization_level: Optional[str] = None):
        self.optimization_level = optimization_level or app_config.get_optimization_level()
    
    def filter_dataframe_fast(
        self, 
        df: pd.DataFrame, 
        search_term: str, 
        columns: List[str]
    ) -> pd.DataFrame:
        """Optimized DataFrame filtering using vectorized operations"""
        
        if not search_term or df.empty:
            return df
        
        if self.optimization_level == 'legacy':
            return self._filter_legacy(df, search_term, columns)
        
        try:
            search_lower = search_term.lower()
            mask = pd.Series(False, index=df.index)
            
            # Vectorized filtering across specified columns
            for col in columns:
                if col in df.columns:
                    # Use pandas' efficient string operations
                    col_mask = df[col].astype(str).str.lower().str.contains(
                        search_lower, na=False, regex=False
                    )
                    mask |= col_mask
            
            result = df[mask]
            logger.debug(f"Optimized filter: {len(df)} -> {len(result)} rows")
            return result
            
        except Exception as e:
            logger.warning(f"Optimized filtering failed, falling back: {e}")
            return self._filter_legacy(df, search_term, columns)
    
    def _filter_legacy(
        self, 
        df: pd.DataFrame, 
        search_term: str, 
        columns: List[str]
    ) -> pd.DataFrame:
        """Legacy filtering method for fallback"""
        # Replicate current existing logic
        search_lower = search_term.lower()
        filtered_df = df.copy()
        
        # Basic search in query and description
        if 'query' in df.columns:
            query_mask = df['query'].str.contains(search_term, case=False, na=False)
            filtered_df = df[query_mask]
        
        return filtered_df
    
    def paginate_dataframe(
        self, 
        df: pd.DataFrame, 
        page_num: int, 
        page_size: int = 15
    ) -> pd.DataFrame:
        """Efficient DataFrame pagination"""
        
        if df.empty or page_num < 1:
            return pd.DataFrame()
        
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        
        # Use iloc for efficient slicing
        if start_idx >= len(df):
            return pd.DataFrame()
        
        return df.iloc[start_idx:end_idx]
    
    def optimize_memory_usage(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage"""
        
        if self.optimization_level == 'legacy':
            return df
        
        try:
            # Convert object columns to categorical where beneficial
            optimized_df = df.copy()
            
            for col in optimized_df.select_dtypes(include=['object']).columns:
                # Only convert to categorical if it reduces memory
                unique_count = optimized_df[col].nunique()
                total_count = len(optimized_df)
                
                if unique_count / total_count < 0.5:  # Less than 50% unique values
                    optimized_df[col] = optimized_df[col].astype('category')
            
            # Convert numeric columns to optimal types
            for col in optimized_df.select_dtypes(include=['int64']).columns:
                if optimized_df[col].min() >= 0:
                    # Try unsigned integers
                    if optimized_df[col].max() < 255:
                        optimized_df[col] = optimized_df[col].astype('uint8')
                    elif optimized_df[col].max() < 65535:
                        optimized_df[col] = optimized_df[col].astype('uint16')
                    elif optimized_df[col].max() < 4294967295:
                        optimized_df[col] = optimized_df[col].astype('uint32')
            
            # Calculate memory savings
            original_memory = df.memory_usage(deep=True).sum()
            new_memory = optimized_df.memory_usage(deep=True).sum()
            savings = original_memory - new_memory
            
            if savings > 0:
                logger.info(f"Memory optimization saved {savings / 1024 / 1024:.1f} MB")
            
            return optimized_df
            
        except Exception as e:
            logger.warning(f"Memory optimization failed: {e}")
            return df
    
    def process_large_dataset_chunked(
        self, 
        filepath: str, 
        chunk_size: int = 1000,
        processing_func=None
    ) -> pd.DataFrame:
        """Process large datasets in chunks to reduce memory usage"""
        
        if self.optimization_level == 'legacy':
            # Load entire file as before
            return pd.read_csv(filepath)
        
        try:
            chunks = []
            for chunk in pd.read_csv(filepath, chunksize=chunk_size):
                if processing_func:
                    chunk = processing_func(chunk)
                chunks.append(chunk)
            
            result = pd.concat(chunks, ignore_index=True)
            logger.info(f"Processed {len(chunks)} chunks totaling {len(result)} rows")
            return result
            
        except Exception as e:
            logger.warning(f"Chunked processing failed, loading full file: {e}")
            return pd.read_csv(filepath)

# Compatibility wrapper
def filter_dataframe_legacy_wrapper(
    df: pd.DataFrame, 
    search_term: str, 
    columns: List[str]
) -> pd.DataFrame:
    """Wrapper for backward compatibility"""
    
    optimizer = DataFrameOptimizer()
    if app_config.enable_performance_optimizations:
        return optimizer.filter_dataframe_fast(df, search_term, columns)
    else:
        return optimizer._filter_legacy(df, search_term, columns)