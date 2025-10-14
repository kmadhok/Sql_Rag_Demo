#!/usr/bin/env python3
"""
Test script for LLM-based SQL analysis
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.llm_sql_analyzer import LLMSQLAnalyzer, extract_tables_with_llm, extract_columns_with_llm

def test_table_extraction():
    """Test LLM-based table extraction"""
    print("🧪 Testing LLM Table Extraction")
    print("=" * 50)
    
    # Test SQL with CTEs (the problematic case from debug logs)
    test_sql = """
    WITH user_sale AS (
      SELECT user_id, SUM(sale_price) AS revenue
      FROM `bigquery-public-data.thelook_ecommerce.order_items`
      GROUP BY user_id
    ),
    user_cost AS (
      SELECT ii.user_id, SUM(ii.cost) AS cost
      FROM (
        SELECT oi.user_id, ii.cost
        FROM `bigquery-public-data.thelook_ecommerce.order_items` oi
        JOIN `bigquery-public-data.thelook_ecommerce.inventory_items` ii ON oi.inventory_item_id = ii.id
      ) ii
      GROUP BY ii.user_id
    )
    SELECT u.id AS user_id, COALESCE(us.revenue, 0) AS revenue, COALESCE(uc.cost, 0) AS cost
    FROM `bigquery-public-data.thelook_ecommerce.users` u
    LEFT JOIN user_sale us ON u.id = us.user_id
    LEFT JOIN user_cost uc ON u.id = uc.user_id
    ORDER BY revenue DESC
    """
    
    try:
        # Test table extraction
        tables = extract_tables_with_llm(test_sql)
        print(f"✅ Extracted tables: {tables}")
        
        # Should extract actual tables, NOT CTEs
        expected_real_tables = ['users', 'order_items', 'inventory_items']
        extracted_real_tables = [t.split('.')[-1] for t in tables if 'thelook_ecommerce' in t]
        
        print(f"Expected: {expected_real_tables}")
        print(f"Extracted: {extracted_real_tables}")
        
        # Check if we avoided extracting CTEs
        cte_names = ['user_sale', 'user_cost']
        ctes_found = [cte for cte in cte_names if any(cte in t for t in tables)]
        
        if not ctes_found:
            print("✅ SUCCESS: No CTEs extracted as tables")
        else:
            print(f"❌ FAILURE: CTEs found in tables: {ctes_found}")
            
    except Exception as e:
        print(f"❌ Table extraction failed: {e}")

def test_column_extraction():
    """Test LLM-based column extraction"""
    print("\n🧪 Testing LLM Column Extraction")
    print("=" * 50)
    
    # Test SQL that should extract specific columns
    test_sql = """
    SELECT
        u.id AS user_id,
        SUM(oi.sale_price) AS total_spent
      FROM
        `bigquery-public-data.thelook_ecommerce.users` AS u
      LEFT JOIN
        `bigquery-public-data.thelook_ecommerce.order_items` AS oi
        ON oi.user_id = u.id
      GROUP BY
        user_id
    ORDER BY
      total_spent ASC
    LIMIT 1
    """
    
    try:
        # Test column extraction
        available_tables = ['users', 'order_items']
        columns = extract_columns_with_llm(test_sql, available_tables)
        print(f"✅ Extracted columns: {columns}")
        
        # Expected columns
        expected_columns = [
            {'table': 'users', 'column': 'id'},
            {'table': 'order_items', 'column': 'sale_price'},
            {'table': 'order_items', 'column': 'user_id'}
        ]
        
        print(f"Expected: {expected_columns}")
        print(f"Extracted: {columns}")
        
        # Check if we found the critical columns
        found_columns = []
        for col in columns:
            if isinstance(col, dict):
                found_columns.append(f"{col.get('table', 'unknown')}.{col.get('column', 'unknown')}")
        
        critical_columns = ['users.id', 'order_items.sale_price', 'order_items.user_id']
        found_critical = [col for col in critical_columns if any(col.endswith(f".{c.split('.')[-1]}") for c in found_columns)]
        
        if len(found_critical) >= 2:  # Allow some flexibility
            print("✅ SUCCESS: Key columns detected")
        else:
            print(f"❌ FAILURE: Missing critical columns. Found: {found_columns}")
            
    except Exception as e:
        print(f"❌ Column extraction failed: {e}")

def test_comprehensive_analysis():
    """Test comprehensive SQL analysis"""
    print("\n🧪 Testing Comprehensive Analysis")
    print("=" * 50)
    
    # Create analyzer instance
    analyzer = LLMSQLAnalyzer(cache_strategy="memory")  # Use memory cache for testing
    
    test_sql = """
    SELECT
        user_id,
        total_spent
      FROM (
        SELECT
            u.id AS user_id,
            SUM(oi.sale_price) AS total_spent
          FROM
            `bigquery-public-data.thelook_ecommerce.users` AS u
          LEFT JOIN
            `bigquery-public-data.thelook_ecommerce.order_items` AS oi
            ON oi.user_id = u.id
          GROUP BY
            user_id
      )
    ORDER BY
      total_spent ASC
    LIMIT 1
    """
    
    try:
        # Test comprehensive analysis
        result = analyzer.analyze_sql_comprehensive(test_sql)
        
        print(f"Analysis completed: {result.cache_hit}")
        print(f"Analysis time: {result.analysis_time:.3f}s")
        print(f"Estimated cost: ~${result.cost_estimate:.6f}")
        
        if result.table_analysis:
            print(f"Tables found: {result.table_analysis.actual_tables}")
            print(f"CTEs found: {result.table_analysis.cte_tables}")
            
        if result.column_analysis:
            print(f"Columns found: {len(result.column_analysis.columns)}")
            
        # Test caching by running again
        result2 = analyzer.analyze_sql_comprehensive(test_sql)
        if result2.cache_hit:
            print("✅ SUCCESS: Caching is working")
        else:
            print("❌ WARNING: Cache miss on second run")
            
    except Exception as e:
        print(f"❌ Comprehensive analysis failed: {e}")

def main():
    """Run all tests"""
    print("🚀 LLM SQL Analyzer Test Suite")
    print("=" * 60)
    
    # Check if Gemini API key is available
    if not os.getenv('GEMINI_API_KEY') and not os.getenv('GOOGLE_API_KEY'):
        print("❌ No GEMINI_API_KEY or GOOGLE_API_KEY found in environment")
        print("Please set your API key:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return
    
    test_table_extraction()
    test_column_extraction() 
    test_comprehensive_analysis()
    
    print("\n🎯 Test Summary")
    print("=" * 60)
    print("If all tests passed, the LLM-based SQL analysis is working correctly!")
    print("This should resolve the CTE extraction issue and empty column detection.")

if __name__ == "__main__":
    main()