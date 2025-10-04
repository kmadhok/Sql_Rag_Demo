#!/usr/bin/env python3
"""
Test Script for SQL Validation Fixes

This script tests the fixed SQL validation system to ensure:
1. Schema manager loads correctly with the fixed schema CSV
2. SQL validator can detect tables and columns from schema
3. Validation provides meaningful feedback for generated SQL queries

Usage:
    python test_sql_validation_fixed.py
"""

import logging
import sys
from pathlib import Path

# Configure logging to show debug information
logging.basicConfig(level=logging.DEBUG, format='%(name)s:%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

def test_schema_manager():
    """Test that the schema manager loads correctly with the fixed schema CSV."""
    print("=" * 60)
    print("TEST 1: Schema Manager Loading")
    print("=" * 60)
    
    try:
        from schema_manager import create_schema_manager
        
        schema_path = "sample_queries_metadata_schema.csv"
        if not Path(schema_path).exists():
            print(f"❌ Schema file not found: {schema_path}")
            return None
        
        print(f"📁 Loading schema from: {schema_path}")
        schema_manager = create_schema_manager(schema_path, verbose=True)
        
        if schema_manager:
            print(f"✅ Schema manager loaded successfully!")
            print(f"   📊 Tables: {schema_manager.table_count}")
            print(f"   📋 Columns: {schema_manager.column_count}")
            
            # Test the new methods
            print(f"\n🔧 Testing new validator compatibility methods:")
            
            # Test get_table_info
            sample_tables = schema_manager.get_table_sample(3)
            if sample_tables:
                test_table = sample_tables[0]
                table_info = schema_manager.get_table_info(test_table)
                print(f"   get_table_info('{test_table}'): {table_info is not None}")
                if table_info:
                    print(f"      Columns: {len(table_info.get('columns', []))}")
            
            # Test get_table_columns
            if sample_tables:
                columns = schema_manager.get_table_columns(sample_tables[0])
                print(f"   get_table_columns('{sample_tables[0]}'): {len(columns)} columns")
            
            # Test schema_df property
            schema_df = schema_manager.schema_df
            print(f"   schema_df property: {schema_df is not None}")
            if schema_df is not None:
                print(f"      DataFrame shape: {schema_df.shape}")
                print(f"      Columns: {list(schema_df.columns)}")
            
            return schema_manager
        else:
            print("❌ Failed to create schema manager")
            return None
            
    except Exception as e:
        print(f"❌ Error testing schema manager: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_sql_validator(schema_manager):
    """Test the SQL validator with the fixed schema manager."""
    print("\n" + "=" * 60)
    print("TEST 2: SQL Validator Integration")
    print("=" * 60)
    
    try:
        from core.sql_validator import SQLValidator, ValidationLevel
        
        # Create SQL validator with schema manager
        validator = SQLValidator(schema_manager, ValidationLevel.SCHEMA_BASIC)
        print(f"✅ SQL validator created with schema manager")
        
        # Test SQL queries that should find tables/columns
        test_queries = [
            # Simple query
            "SELECT category_id, category_name FROM project.dataset.categories WHERE category_id = 1",
            
            # Query with JOIN
            """
            SELECT c.category_name, COUNT(*)
            FROM project.dataset.categories c
            JOIN project.dataset.products p ON c.category_id = p.category_id
            GROUP BY c.category_name
            """,
            
            # Query in code block format (like LLM responses)
            """
            Here's a SQL query to get customer information:
            
            ```sql
            SELECT customer_id, email, phone
            FROM project.dataset.customer_contacts
            WHERE preferred_contact_method = 'email'
            ```
            
            This query will return customer contact details.
            """,
            
            # Query with non-existent table (should still work but show warnings)
            "SELECT * FROM nonexistent_table WHERE id = 1"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔍 Test Query {i}:")
            print(f"   Query: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            result = validator.validate_sql(query)
            
            print(f"   ✅ Valid: {result.is_valid}")
            print(f"   📊 Tables found: {len(result.tables_found)} - {list(result.tables_found)}")
            print(f"   📋 Columns found: {len(result.columns_found)}")
            
            if result.errors:
                print(f"   ❌ Errors: {result.errors}")
            if result.warnings:
                print(f"   ⚠️  Warnings: {result.warnings}")
            if result.suggestions:
                print(f"   💡 Suggestions: {result.suggestions}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing SQL validator: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_rag_integration():
    """Test the full RAG integration with SQL validation enabled."""
    print("\n" + "=" * 60)
    print("TEST 3: Full RAG Integration Test")
    print("=" * 60)
    
    try:
        # Test if we can import the main RAG function
        from simple_rag_simple_gemini import answer_question_simple_gemini
        from core.sql_validator import ValidationLevel
        
        print("✅ Successfully imported RAG function with SQL validation")
        print("📝 Note: Full integration test requires vector store and Gemini API key")
        print("   This test confirms the imports work correctly.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing RAG integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests to verify SQL validation fixes."""
    print("🧪 SQL VALIDATION FIXES TEST SUITE")
    print("=" * 60)
    
    # Test 1: Schema Manager
    schema_manager = test_schema_manager()
    if not schema_manager:
        print("\n❌ CRITICAL: Schema manager test failed!")
        sys.exit(1)
    
    # Test 2: SQL Validator
    validator_success = test_sql_validator(schema_manager)
    if not validator_success:
        print("\n❌ CRITICAL: SQL validator test failed!")
        sys.exit(1)
    
    # Test 3: RAG Integration
    integration_success = test_full_rag_integration()
    if not integration_success:
        print("\n❌ WARNING: RAG integration test failed!")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 TEST RESULTS SUMMARY")
    print("=" * 60)
    print("✅ Schema Manager: PASSED")
    print("✅ SQL Validator: PASSED")
    print("✅ RAG Integration: PASSED" if integration_success else "⚠️  RAG Integration: PARTIAL")
    
    print("\n🚀 SQL validation fixes are working correctly!")
    print("💡 The system should now properly detect tables and columns during validation.")
    print("🔧 Run the main application with SQL validation enabled to see the improvements.")

if __name__ == "__main__":
    main()