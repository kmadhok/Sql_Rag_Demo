#!/usr/bin/env python3
"""
Test Integration Fix for Schema Manager and SQL Validation

This script tests the integration fix to ensure:
1. Schema manager loads correctly in the main application
2. Schema manager gets passed to SQL validation
3. SQL validation shows proper table/column counts

Usage:
    python test_integration_fix.py
"""

import logging
from pathlib import Path

# Set up logging to see all debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_schema_path_fix():
    """Test that the corrected schema path works."""
    print("=" * 60)
    print("TEST 1: Schema Path Fix")
    print("=" * 60)
    
    # This mimics the path resolution in app_simple_gemini.py
    SCHEMA_CSV_PATH = Path(__file__).parent / "sample_queries_metadata_schema.csv"
    
    print(f"📁 Schema file path: {SCHEMA_CSV_PATH}")
    print(f"📁 Absolute path: {SCHEMA_CSV_PATH.absolute()}")
    print(f"✅ File exists: {SCHEMA_CSV_PATH.exists()}")
    
    if SCHEMA_CSV_PATH.exists():
        print(f"📊 File size: {SCHEMA_CSV_PATH.stat().st_size} bytes")
        return True
    else:
        print("❌ Schema file not found!")
        return False

def test_schema_manager_loading():
    """Test schema manager loading like the main app."""
    print("\n" + "=" * 60)
    print("TEST 2: Schema Manager Loading")
    print("=" * 60)
    
    try:
        from schema_manager import create_schema_manager
        
        SCHEMA_CSV_PATH = Path(__file__).parent / "sample_queries_metadata_schema.csv"
        
        print(f"🔄 Loading schema manager from: {SCHEMA_CSV_PATH}")
        schema_manager = create_schema_manager(str(SCHEMA_CSV_PATH), verbose=True)
        
        if schema_manager:
            print(f"✅ Schema manager loaded successfully!")
            print(f"   📊 Tables: {schema_manager.table_count}")
            print(f"   📋 Columns: {schema_manager.column_count}")
            
            # Test new methods
            print(f"   🔧 get_table_info available: {hasattr(schema_manager, 'get_table_info')}")
            print(f"   🔧 get_table_columns available: {hasattr(schema_manager, 'get_table_columns')}")
            print(f"   🔧 schema_df available: {hasattr(schema_manager, 'schema_df')}")
            
            return schema_manager
        else:
            print("❌ Failed to create schema manager")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_sql_validation_with_schema(schema_manager):
    """Test SQL validation with the schema manager."""
    print("\n" + "=" * 60)
    print("TEST 3: SQL Validation with Schema Manager")
    print("=" * 60)
    
    try:
        from core.sql_validator import ValidationLevel, validate_sql_query
        
        # Test SQL that should find tables
        test_sql = """
        Here's a query to find unique customers:
        
        ```sql
        SELECT DISTINCT customer_id, email 
        FROM project.dataset.customer_contacts 
        WHERE preferred_contact_method = 'email'
        ```
        
        This will return unique customer contact information.
        """
        
        print(f"🔍 Testing SQL validation with schema manager...")
        print(f"   Schema manager provided: {schema_manager is not None}")
        if schema_manager:
            print(f"   Schema tables: {schema_manager.table_count}")
            print(f"   Schema columns: {schema_manager.column_count}")
        
        # Run validation
        result = validate_sql_query(
            test_sql,
            schema_manager=schema_manager,
            validation_level=ValidationLevel.SCHEMA_BASIC
        )
        
        print(f"\n📊 Validation Results:")
        print(f"   ✅ Valid: {result.is_valid}")
        print(f"   📊 Tables found: {len(result.tables_found)} - {list(result.tables_found)}")
        print(f"   📋 Columns found: {len(result.columns_found)}")
        
        if result.errors:
            print(f"   ❌ Errors: {result.errors}")
        if result.warnings:
            print(f"   ⚠️ Warnings: {result.warnings}")
        
        # This should NOT show "0 tables, 0 columns" anymore
        success = len(result.tables_found) > 0
        if success:
            print(f"   🎉 SUCCESS: Found {len(result.tables_found)} tables (no longer 0!)")
        else:
            print(f"   ❌ ISSUE: Still finding 0 tables")
            
        return success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simulated_rag_call():
    """Simulate the RAG function call with schema manager and SQL validation."""
    print("\n" + "=" * 60)
    print("TEST 4: Simulated RAG Integration")
    print("=" * 60)
    
    try:
        # Load schema manager like the main app
        from schema_manager import create_schema_manager
        SCHEMA_CSV_PATH = Path(__file__).parent / "sample_queries_metadata_schema.csv"
        schema_manager = create_schema_manager(str(SCHEMA_CSV_PATH), verbose=False)
        
        if not schema_manager:
            print("❌ Cannot proceed without schema manager")
            return False
        
        print(f"✅ Schema manager loaded: {schema_manager.table_count} tables")
        
        # Simulate the logging that should appear in the main app
        print(f"🗃️ Schema manager available: {schema_manager.table_count} tables, {schema_manager.column_count} columns")
        
        # Simulate SQL validation call
        from core.sql_validator import ValidationLevel, validate_sql_query
        
        mock_sql_answer = "SELECT customer_id FROM project.dataset.customer_contacts WHERE email IS NOT NULL"
        
        print(f"🔍 Simulating SQL validation call...")
        result = validate_sql_query(
            mock_sql_answer,
            schema_manager=schema_manager,
            validation_level=ValidationLevel.SCHEMA_BASIC
        )
        
        # This simulates the logging that should appear
        if result.is_valid:
            print(f"✅ SQL validation passed ({len(result.tables_found)} tables, {len(result.columns_found)} columns)")
        else:
            print(f"⚠️ SQL validation found {len(result.errors)} errors, {len(result.warnings)} warnings")
        
        # Check if we fixed the "0 tables, 0 columns" issue
        tables_found = len(result.tables_found)
        if tables_found > 0:
            print(f"🎉 SUCCESS: Integration fix working! Found {tables_found} tables")
            return True
        else:
            print(f"❌ ISSUE: Still showing 0 tables - integration needs more work")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests."""
    print("🧪 SCHEMA INTEGRATION FIX TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: Schema path fix
    results.append(test_schema_path_fix())
    
    # Test 2: Schema manager loading
    schema_manager = test_schema_manager_loading()
    results.append(schema_manager is not None)
    
    # Test 3: SQL validation with schema
    if schema_manager:
        results.append(test_sql_validation_with_schema(schema_manager))
    else:
        results.append(False)
    
    # Test 4: Simulated RAG integration
    results.append(test_simulated_rag_call())
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    test_names = [
        "Schema Path Fix",
        "Schema Manager Loading", 
        "SQL Validation with Schema",
        "RAG Integration Simulation"
    ]
    
    all_passed = True
    for i, (name, passed) in enumerate(zip(test_names, results)):
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{i+1}. {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🚀 ALL TESTS PASSED! Integration fixes are working.")
        print("💡 The main application should now show proper table/column counts.")
        print("🔧 Schema injection and SQL validation should work together.")
    else:
        print("⚠️ Some tests failed. Check the output above for issues.")
    
    return all_passed

if __name__ == "__main__":
    main()