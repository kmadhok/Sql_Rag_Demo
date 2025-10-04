#!/usr/bin/env python3
"""
Data loading functionality for SQL RAG Streamlit application.
Extracted from app_simple_gemini.py for better modularity.
"""

import streamlit as st
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Optional
from langchain_community.vectorstores import FAISS
from utils.embedding_provider import get_embedding_function

from .config import (
    FAISS_INDICES_DIR, DEFAULT_VECTOR_STORE, CSV_PATH, 
    CATALOG_ANALYTICS_DIR, SCHEMA_CSV_PATH, SCHEMA_MANAGER_AVAILABLE,
    ERROR_MESSAGES, INFO_MESSAGES
)
from .utils import parse_json_safely

# Configure logging
logger = logging.getLogger(__name__)

# Import schema manager conditionally
if SCHEMA_MANAGER_AVAILABLE:
    try:
        from schema_manager import SchemaManager, create_schema_manager
    except ImportError:
        SCHEMA_MANAGER_AVAILABLE = False


def load_vector_store(index_name: str = DEFAULT_VECTOR_STORE) -> Optional[FAISS]:
    """
    Load pre-built vector store from faiss_indices directory
    
    Args:
        index_name: Name of the index directory to load
        
    Returns:
        FAISS vector store or None if loading fails
    """
    index_path = FAISS_INDICES_DIR / index_name
    
    if not index_path.exists():
        st.error(ERROR_MESSAGES['vector_store_not_found'].format(path=index_path))
        st.info(INFO_MESSAGES['first_run_instruction'])
        return None
    
    try:
        # Initialize embeddings based on provider (Ollama or OpenAI)
        embeddings = get_embedding_function()
        
        # Load the pre-built vector store
        vector_store = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        logger.info(INFO_MESSAGES['vector_store_loaded'].format(path=index_path))
        return vector_store
        
    except Exception as e:
        st.error(ERROR_MESSAGES['vector_store_load_error'].format(error=e))
        logger.error(f"Vector store loading error: {e}")
        return None


@st.cache_resource
def load_schema_manager() -> Optional['SchemaManager']:
    """
    Load and cache SchemaManager for smart schema injection.
    
    Returns:
        SchemaManager instance or None if loading fails or schema not available
    """
    if not SCHEMA_MANAGER_AVAILABLE:
        return None
    
    if not SCHEMA_CSV_PATH.exists():
        logger.info(f"Schema file not found at {SCHEMA_CSV_PATH} - schema injection disabled")
        return None
    
    try:
        # Create schema manager with the schema CSV file
        schema_manager = create_schema_manager(str(SCHEMA_CSV_PATH), verbose=True)
        
        if schema_manager:
            logger.info(INFO_MESSAGES['schema_manager_loaded'])
            logger.info(f"Schema manager loaded: {schema_manager.table_count} tables, {schema_manager.column_count} columns")
            return schema_manager
        else:
            logger.warning("Failed to create schema manager")
            return None
            
    except Exception as e:
        logger.error(f"Error loading schema manager: {e}")
        return None


def load_csv_data() -> Optional[pd.DataFrame]:
    """
    Load optimized CSV data with pre-parsed columns from analytics cache
    
    Returns:
        DataFrame with queries and pre-parsed metadata or None if loading fails
    """
    # PRIORITY 1: Load optimized Parquet file (fastest)
    if CATALOG_ANALYTICS_DIR.exists():
        parquet_path = CATALOG_ANALYTICS_DIR / "optimized_queries.parquet"
        if parquet_path.exists():
            try:
                df = pd.read_parquet(parquet_path)
                # Convert numpy arrays to Python lists for consistency
                if 'tables_parsed' in df.columns:
                    df['tables_parsed'] = df['tables_parsed'].apply(
                        lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([] if pd.isna(x) else x)
                    )
                if 'joins_parsed' in df.columns:
                    df['joins_parsed'] = df['joins_parsed'].apply(
                        lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([] if pd.isna(x) else x)
                    )
                logger.info(f"⚡ Loaded {len(df)} queries from optimized Parquet (pre-parsed)")
                return df
            except ImportError:
                logger.warning("PyArrow not available for Parquet loading")
            except Exception as e:
                logger.warning(f"Failed to load Parquet cache: {e}")
        
        # PRIORITY 2: Load optimized CSV file  
        csv_cache_path = CATALOG_ANALYTICS_DIR / "optimized_queries.csv"
        if csv_cache_path.exists():
            try:
                df = pd.read_csv(csv_cache_path)
                # Parse JSON strings back to lists for cached DataFrame
                if 'tables_parsed' in df.columns:
                    df['tables_parsed'] = df['tables_parsed'].apply(
                        lambda x: parse_json_safely(x, [])
                    )
                if 'joins_parsed' in df.columns:
                    df['joins_parsed'] = df['joins_parsed'].apply(
                        lambda x: parse_json_safely(x, [])
                    )
                logger.info(f"✅ Loaded {len(df)} queries from optimized CSV cache (pre-parsed)")
                return df
            except Exception as e:
                logger.warning(f"Failed to load optimized CSV cache: {e}")
    
    # FALLBACK: Original CSV (requires manual parsing - slower)
    try:
        if not CSV_PATH.exists():
            st.error(ERROR_MESSAGES['csv_not_found'].format(path=CSV_PATH))
            st.error("💡 Please run: python catalog_analytics_generator.py --csv 'your_file.csv'")
            return None
        
        df = pd.read_csv(CSV_PATH)
        df = df.fillna('')
        
        # Ensure required columns exist
        if 'query' not in df.columns:
            st.error(f"❌ Missing required 'query' column in {CSV_PATH}")
            return None
        
        # Remove rows with empty queries
        df = df[df['query'].str.strip() != '']
        
        # Warning: No pre-parsed columns available
        st.warning("⚠️ Using original CSV without pre-parsed data - performance may be slower")
        st.info("💡 Run `python catalog_analytics_generator.py --csv 'your_file.csv'` for better performance")
        
        logger.info(f"📄 Loaded {len(df)} queries from original CSV (no cache)")
        return df
        
    except Exception as e:
        st.error(ERROR_MESSAGES['no_data_found'])
        logger.error(f"Data loading error: {e}")
        return None


def load_join_analysis() -> dict:
    """
    Load pre-computed join analysis from cache
    
    Returns:
        Dictionary with join analysis data or empty dict if not found
    """
    if not CATALOG_ANALYTICS_DIR.exists():
        return {}
    
    analysis_path = CATALOG_ANALYTICS_DIR / "join_analysis.json"
    if not analysis_path.exists():
        return {}
    
    try:
        with open(analysis_path, 'r') as f:
            analysis = json.load(f)
        logger.info("✅ Loaded pre-computed join analysis")
        return analysis
    except Exception as e:
        logger.warning(f"Failed to load join analysis: {e}")
        return {}


def load_table_relationships() -> dict:
    """
    Load pre-computed table relationships from cache
    
    Returns:
        Dictionary with table relationship data or empty dict if not found
    """
    if not CATALOG_ANALYTICS_DIR.exists():
        return {}
    
    relationships_path = CATALOG_ANALYTICS_DIR / "table_relationships.json"
    if not relationships_path.exists():
        return {}
    
    try:
        with open(relationships_path, 'r') as f:
            relationships = json.load(f)
        logger.info("✅ Loaded pre-computed table relationships")
        return relationships
    except Exception as e:
        logger.warning(f"Failed to load table relationships: {e}")
        return {}


def validate_data_files() -> dict:
    """
    Validate that required data files exist and return status
    
    Returns:
        Dictionary with validation status for each required file
    """
    validation_status = {}
    
    # Check vector store
    index_path = FAISS_INDICES_DIR / DEFAULT_VECTOR_STORE
    validation_status['vector_store'] = {
        'exists': index_path.exists(),
        'path': str(index_path),
        'required': True
    }
    
    # Check CSV data
    validation_status['csv_data'] = {
        'exists': CSV_PATH.exists(),
        'path': str(CSV_PATH),
        'required': True
    }
    
    # Check optimized cache
    parquet_path = CATALOG_ANALYTICS_DIR / "optimized_queries.parquet"
    csv_cache_path = CATALOG_ANALYTICS_DIR / "optimized_queries.csv"
    
    validation_status['optimized_cache'] = {
        'parquet_exists': parquet_path.exists(),
        'csv_exists': csv_cache_path.exists(),
        'parquet_path': str(parquet_path),
        'csv_path': str(csv_cache_path),
        'required': False
    }
    
    # Check schema file
    validation_status['schema'] = {
        'exists': SCHEMA_CSV_PATH.exists(),
        'path': str(SCHEMA_CSV_PATH),
        'required': False
    }
    
    # Check analytics files
    analysis_path = CATALOG_ANALYTICS_DIR / "join_analysis.json"
    relationships_path = CATALOG_ANALYTICS_DIR / "table_relationships.json"
    
    validation_status['analytics'] = {
        'join_analysis_exists': analysis_path.exists(),
        'relationships_exists': relationships_path.exists(),
        'analysis_path': str(analysis_path),
        'relationships_path': str(relationships_path),
        'required': False
    }
    
    return validation_status


def get_data_loading_recommendations(validation_status: dict) -> list:
    """
    Get recommendations based on data validation status
    
    Args:
        validation_status: Result from validate_data_files()
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    if not validation_status['vector_store']['exists']:
        recommendations.append(
            "🔴 **Critical**: Run `python standalone_embedding_generator.py --csv 'your_data.csv'` to create vector store"
        )
    
    if not validation_status['csv_data']['exists']:
        recommendations.append(
            "🔴 **Critical**: Ensure your CSV data file exists at the configured path"
        )
    
    if not (validation_status['optimized_cache']['parquet_exists'] or validation_status['optimized_cache']['csv_exists']):
        recommendations.append(
            "🟡 **Performance**: Run `python catalog_analytics_generator.py --csv 'your_file.csv'` for faster loading"
        )
    
    if not validation_status['schema']['exists'] and SCHEMA_MANAGER_AVAILABLE:
        recommendations.append(
            "🟡 **Feature**: Add schema.csv file to enable smart schema injection"
        )
    
    if not (validation_status['analytics']['join_analysis_exists'] and validation_status['analytics']['relationships_exists']):
        recommendations.append(
            "🟡 **Feature**: Analytics files missing - some catalog features may be limited"
        )
    
    if not recommendations:
        recommendations.append("✅ All data files are properly configured!")
    
    return recommendations
