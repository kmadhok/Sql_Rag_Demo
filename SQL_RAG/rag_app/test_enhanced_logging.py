#!/usr/bin/env python3
"""
Test script to demonstrate enhanced logging in app_simple_gemini.py

This script helps you see the logging output when running the application.
Run this to test the logging without needing to start the full Streamlit app.
"""

import logging
import sys
from pathlib import Path

# Setup logging to console for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_logging_setup():
    """Test that our logging setup works correctly"""
    print("\n" + "="*80)
    print("TESTING ENHANCED LOGGING SETUP")
    print("="*80)
    
    # Test basic logging
    logger.info("🧪 Testing basic logger functionality")
    print("[TEST] Print statement also working")
    
    # Test schema manager logging simulation
    print("\n--- Schema Injection Logging Test ---")
    logger.info("🗃️ SCHEMA INJECTION ENABLED")
    logger.info("📊 Schema Manager Stats:")
    logger.info("   - Total tables available: 42")
    logger.info("   - Total columns available: 156")
    logger.info("   - Schema file source: /path/to/schema.csv")
    print("[SCHEMA DEBUG] Schema injection ENABLED with 42 tables and 156 columns")
    
    # Test vector database logging simulation
    print("\n--- Vector Database Logging Test ---")
    logger.info("🗂️ VECTOR DATABASE LOADING")
    logger.info("📂 Selected index: index_sample_queries")
    logger.info("📁 Index path: /path/to/faiss_indices/index_sample_queries")
    print("[VECTOR DEBUG] Loading vector database: index_sample_queries")
    logger.info("✅ VECTOR DATABASE LOADED SUCCESSFULLY")
    logger.info("📊 Vector Store Stats:")
    logger.info("   - Total documents: 1,234")
    logger.info("   - Index name: index_sample_queries")
    logger.info("   - Embedding provider: Ollama (nomic-embed-text)")
    print("[VECTOR DEBUG] Vector database loaded successfully with 1,234 documents")
    
    # Test SQL validation logging simulation
    print("\n--- SQL Validation Logging Test ---")
    logger.info("✅ SQL VALIDATION ENABLED")
    logger.info("📊 Validation Settings:")
    logger.info("   - Validation level: SCHEMA_BASIC")
    print("[SQL VALIDATION DEBUG] SQL validation ENABLED with level: SCHEMA_BASIC")
    
    logger.info("🔍 SQL VALIDATION RESULTS")
    logger.info("📊 Validation Summary:")
    logger.info("   - Validation enabled: True")
    logger.info("   - Validation level: SCHEMA_BASIC")
    logger.info("   - Is valid: True")
    logger.info("   - Validation time: 0.045s")
    print("[SQL VALIDATION DEBUG] SQL Validation ENABLED")
    print("[SQL VALIDATION DEBUG] Validation level: SCHEMA_BASIC")
    print("[SQL VALIDATION DEBUG] Query is valid: True")
    
    # Sample validation data
    tables_found = ['customers', 'orders', 'order_items']
    columns_found = ['customer_id', 'order_id', 'product_id', 'quantity']
    
    logger.info(f"📋 Tables Found ({len(tables_found)}): {', '.join(tables_found)}")
    print(f"[SQL VALIDATION DEBUG] Tables found ({len(tables_found)}): {', '.join(tables_found)}")
    
    logger.info(f"📊 Columns Found ({len(columns_found)}): {', '.join(columns_found)}")
    print(f"[SQL VALIDATION DEBUG] Columns found ({len(columns_found)}): {', '.join(columns_found)}")
    
    # Test query processing logging
    print("\n--- Query Processing Logging Test ---")
    test_query = "Show me customer spending patterns with joins"
    logger.info("🔎 PROCESSING NEW QUERY")
    logger.info(f"📝 User Query: '{test_query}'")
    logger.info("⚙️ Settings: Gemini=True, Hybrid=True, Schema=True, SQL_Val=True")
    print(f"[QUERY DEBUG] Processing query: '{test_query}'")
    print("[QUERY DEBUG] Settings - Gemini: True, Hybrid: True, Schema: True, SQL Validation: True")
    
    print("\n" + "="*80)
    print("LOGGING TEST COMPLETE")
    print("="*80)
    print("\nWhat you'll see when running the app:")
    print("✅ Console output with [DEBUG] tags for immediate visibility")
    print("✅ Structured logging to application logs")
    print("✅ Detailed data about schema injection, vector stores, and SQL validation")
    print("✅ Real-time insight into what data is being used")

def show_usage_instructions():
    """Show instructions for using the enhanced logging"""
    print("\n" + "="*80)
    print("HOW TO USE ENHANCED LOGGING")
    print("="*80)
    print("""
1. Run the Streamlit app as usual:
   streamlit run app_simple_gemini.py

2. Watch your console/terminal for debug output:
   - [SCHEMA DEBUG] messages show schema injection data
   - [VECTOR DEBUG] messages show vector database usage
   - [SQL VALIDATION DEBUG] messages show validation results
   - [QUERY DEBUG] messages show query processing

3. Check application logs for structured logging:
   - Logger messages provide detailed information
   - Timestamps and levels for better tracking

4. The debug output shows:
   ✅ Which vector database is loaded and how many documents
   ✅ Whether schema injection is enabled and how many tables/columns
   ✅ SQL validation settings and results
   ✅ User queries being processed and system settings

5. Example console output when you search:
   [QUERY DEBUG] Processing query: 'Show customer analysis'
   [SCHEMA DEBUG] Schema injection ENABLED with 42 tables and 156 columns
   [VECTOR DEBUG] Vector database loaded successfully with 1,234 documents
   [SQL VALIDATION DEBUG] SQL validation ENABLED with level: SCHEMA_BASIC
   [SQL VALIDATION DEBUG] Query is valid: True
   [SQL VALIDATION DEBUG] Tables found (3): customers, orders, payments
    """)

if __name__ == "__main__":
    print("Enhanced Logging Test for SQL RAG Application")
    test_logging_setup()
    show_usage_instructions()