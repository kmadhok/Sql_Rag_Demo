#!/usr/bin/env python3
"""
App Data Loading Functions
Data loading functions extracted from app_simple_gemini.py for better organization
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
import pandas as pd

# Import application configuration
try:
    from config.app_config import app_config
    FAISS_INDICES_DIR = app_config.FAISS_INDICES_DIR
    DEFAULT_VECTOR_STORE = app_config.DEFAULT_VECTOR_STORE
    CSV_PATH = app_config.CSV_PATH
    CATALOG_ANALYTICS_DIR = app_config.CATALOG_ANALYTICS_DIR
    SCHEMA_CSV_PATH = app_config.SCHEMA_CSV_PATH
    LOOKML_SAFE_JOIN_MAP_PATH = FAISS_INDICES_DIR / "lookml_safe_join_map.json"
    SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH = Path(__file__).parent.parent / "lookml_safe_join_map.json"
    LOOKML_DIR = Path(__file__).parent.parent / "lookml_data"
except ImportError:
    # Fallback configuration
    FAISS_INDICES_DIR = Path(__file__).parent.parent / "faiss_indices"
    DEFAULT_VECTOR_STORE = "index_sample_queries_with_metadata_recovered"
    CSV_PATH = Path(__file__).parent.parent / "sample_queries_with_metadata.csv"
    CATALOG_ANALYTICS_DIR = Path(__file__).parent.parent / "catalog_analytics"
    SCHEMA_CSV_PATH = Path(__file__).parent.parent / "data_new" / "thelook_ecommerce_schema.csv"
    LOOKML_SAFE_JOIN_MAP_PATH = FAISS_INDICES_DIR / "lookml_safe_join_map.json"
    SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH = Path(__file__).parent.parent / "lookml_safe_join_map.json"
    LOOKML_DIR = Path(__file__).parent.parent / "lookml_data"

logger = logging.getLogger(__name__)


def load_vector_store(index_name: str = DEFAULT_VECTOR_STORE):
    """
    Load pre-built vector store from faiss_indices directory
    
    Args:
        index_name: Name of the index directory to load
        
    Returns:
        FAISS vector store or None if loading fails
    """
    from langchain_community.vectorstores import FAISS
    
    index_path = FAISS_INDICES_DIR / index_name
    
    if not index_path.exists():
        logger.error(f"Vector store not found at: {index_path}")
        logger.info("First run: python standalone_embedding_generator.py --csv 'your_data.csv'")
        return None
    
    try:
        # Initialize embeddings using provider factory (Ollama or OpenAI)
        from utils.embedding_provider import get_embedding_function
        embeddings = get_embedding_function()
        
        # Import our safe configuration system
        try:
            from config.safe_config import safe_config
            from utils.safe_loader import SafeLoader
        except ImportError:
            # Fallback if new modules not available
            safe_config = None
            SafeLoader = None
        
        # Load the vector store with security improvements
        if SafeLoader and safe_config and safe_config.use_safe_deserialization:
            logger.info(f"Loading FAISS index with SAFE deserialization (security level: {safe_config.get_security_level()})")
            vector_store = SafeLoader.safe_load_vector_store_fallback(
                index_path, embeddings, fallback_to_legacy=safe_config.fallback_legacy_mode
            )
        else:
            # Legacy mode with existing logic (safe fallback)
            allow_dangerous = os.getenv("FAISS_SAFE_DESERIALIZATION", "0").lower() not in ("1", "true", "yes")
            if allow_dangerous:
                logger.warning("Loading FAISS index with allow_dangerous_deserialization=True (legacy mode)")
            else:
                logger.info("Loading FAISS index with safe deserialization (legacy mode)")
            vector_store = FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=allow_dangerous
            )
        
        logger.info(f"Loaded vector store from {index_path}")
        return vector_store
        
    except Exception as e:
        logger.error(f"Vector store loading error: {e}")
        return None


def get_available_indices() -> List[str]:
    """Get list of available vector store indices"""
    if not FAISS_INDICES_DIR.exists():
        return []
    
    indices = []
    for path in FAISS_INDICES_DIR.iterdir():
        if path.is_dir() and path.name.startswith("index_"):
            indices.append(path.name)
    
    return sorted(indices)


def load_lookml_safe_join_map() -> Optional[Dict[str, Any]]:
    """
    Load LookML safe-join map for enhanced SQL generation.
    
    Returns:
        Dictionary containing LookML join relationships or None if loading fails
    """
    # 1) Primary: load from faiss_indices (created by standalone_embedding_generator --lookml-dir)
    if LOOKML_SAFE_JOIN_MAP_PATH.exists():
        try:
            with open(LOOKML_SAFE_JOIN_MAP_PATH, 'r') as f:
                safe_join_map = json.load(f)
            logger.info(
                f"Loaded LookML safe-join map from {LOOKML_SAFE_JOIN_MAP_PATH} with "
                f"{safe_join_map.get('metadata', {}).get('total_explores', 0)} explores"
            )
            return safe_join_map
        except Exception as e:
            logger.warning(f"Failed to load safe-join map from {LOOKML_SAFE_JOIN_MAP_PATH}: {e}")

    # 2) Secondary: load from project root if present
    if SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH.exists():
        try:
            with open(SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH, 'r') as f:
                safe_join_map = json.load(f)
            logger.info(
                f"Loaded LookML safe-join map from {SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH} with "
                f"{safe_join_map.get('metadata', {}).get('total_explores', 0)} explores"
            )
            return safe_join_map
        except Exception as e:
            logger.warning(f"Failed to load safe-join map from {SECONDARY_LOOKML_SAFE_JOIN_MAP_PATH}: {e}")

    # 3) Fallback: parse LookML files on the fly if available
    try:
        if LOOKML_DIR.exists():
            logger.info(f"LookML safe-join map not found; attempting to parse LookML from {LOOKML_DIR}")
            try:
                from simple_lookml_parser import SimpleLookMLParser
            except Exception as ie:
                logger.warning(f"SimpleLookMLParser import failed: {ie}")
                return None

            parser = SimpleLookMLParser(verbose=False)
            models = parser.parse_directory(LOOKML_DIR)
            if not models:
                logger.info("No LookML models parsed; LookML features disabled")
                return None

            safe_join_map = parser.generate_safe_join_map(models)

            # Attempt to cache to faiss_indices for reuse
            try:
                LOOKML_SAFE_JOIN_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(LOOKML_SAFE_JOIN_MAP_PATH, 'w') as f:
                    json.dump(safe_join_map, f, indent=2)
                logger.info(f"Cached LookML safe-join map to {LOOKML_SAFE_JOIN_MAP_PATH}")
            except Exception as we:
                logger.debug(f"Could not cache safe-join map: {we}")

            logger.info(
                f"Generated LookML safe-join map with {safe_join_map.get('metadata', {}).get('total_explores', 0)} explores"
            )
            return safe_join_map
        else:
            logger.info(f"LookML directory not found at {LOOKML_DIR}; LookML features disabled")
            return None
    except Exception as e:
        logger.error(f"Error generating LookML safe-join map on the fly: {e}")
        return None


def load_schema_manager() -> Optional['SchemaManager']:
    """
    Load and cache SchemaManager for smart schema injection.
    
    Returns:
        SchemaManager instance or None if loading fails or schema not available
    """
    SCHEMA_MANAGER_AVAILABLE = True
    
    try:
        from schema_manager import SchemaManager, create_schema_manager
    except ImportError:
        SCHEMA_MANAGER_AVAILABLE = False
        logger.info("Schema manager not available - checking if import was moved")
        return None
    
    if not SCHEMA_MANAGER_AVAILABLE:
        return None
    
    if not SCHEMA_CSV_PATH.exists():
        logger.info(f"Schema file not found at {SCHEMA_CSV_PATH} - schema injection disabled")
        logger.debug(f"Expected schema file path: {SCHEMA_CSV_PATH.absolute()}")
        return None
    
    try:
        # Create schema manager with the schema CSV file
        schema_manager = create_schema_manager(str(SCHEMA_CSV_PATH), verbose=True)
        
        if schema_manager:
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
                    df['tables_parsed'] = df['tables_parsed'].apply(lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([] if pd.isna(x) else x))
                if 'joins_parsed' in df.columns:
                    df['joins_parsed'] = df['joins_parsed'].apply(lambda x: list(x) if hasattr(x, '__iter__') and not isinstance(x, str) else ([] if pd.isna(x) else x))
                logger.info(f"Loaded {len(df)} queries from optimized Parquet (pre-parsed)")
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
                    df['tables_parsed'] = df['tables_parsed'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '' else [])
                if 'joins_parsed' in df.columns:
                    df['joins_parsed'] = df['joins_parsed'].apply(lambda x: json.loads(x) if pd.notna(x) and x != '' else [])
                logger.info(f"Loaded {len(df)} queries from optimized CSV cache (pre-parsed)")
                return df
            except Exception as e:
                logger.warning(f"Failed to load optimized CSV cache: {e}")
    
    # FALLBACK: Original CSV (requires manual parsing - slower)
    try:
        if not CSV_PATH.exists():
            logger.error(f"CSV file not found: {CSV_PATH}")
            logger.info("Please run: python catalog_analytics_generator.py --csv 'your_file.csv'")
            return None
        
        df = pd.read_csv(CSV_PATH)
        df = df.fillna('')
        
        # Ensure required columns exist
        if 'query' not in df.columns:
            logger.error(f"Missing required 'query' column in {CSV_PATH}")
            return None
        
        # Remove rows with empty queries
        df = df[df['query'].str.strip() != '']
        
        # Warning: No pre-parsed columns available
        logger.warning("Using original CSV without pre-parsed data - performance may be slower")
        logger.info("Run `python catalog_analytics_generator.py --csv 'your_file.csv'` for better performance")
        
        logger.info(f"Loaded {len(df)} queries from original CSV (no cache)")
        return df
        
    except Exception as e:
        logger.error(f"Data loading error: {e}")
        return None


def load_cached_analytics() -> Optional[Dict[str, Any]]:
    """
    Load pre-computed analytics from cache.
    
    Returns:
        Dictionary with analytics data or None if not available
    """
    cache_file = CATALOG_ANALYTICS_DIR / "join_analysis.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                analytics = json.load(f)
            
            logger.info(f"Loaded {len(analytics.get('join_stats', {}))} join statistics from cache")
            return analytics
            
        except Exception as e:
            logger.warning(f"Failed to load cached analytics: {e}")
            return None
    else:
        logger.info("No cached analytics found - run analytics generator first")
        return None


def load_cached_graph_files() -> List[str]:
    """
    Load cached graph visualization files.
    
    Returns:
        List of available graph file paths
    """
    graph_files = []
    
    if CATALOG_ANALYTICS_DIR.exists():
        for ext in ['.png', '.svg', '.pdf']:
            for file_path in CATALOG_ANALYTICS_DIR.glob(f"relationships_graph{ext}"):
                graph_files.append(str(file_path))
    
    return sorted(graph_files)
