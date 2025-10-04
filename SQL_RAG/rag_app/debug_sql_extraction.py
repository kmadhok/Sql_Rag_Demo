#!/usr/bin/env python3
"""
Debug SQL table extraction
"""

import re

def debug_sql_extraction():
    test_query = "SELECT category_id, category_name FROM project.dataset.categories WHERE category_id = 1"
    
    print("Original query:")
    print(test_query)
    print()
    
    # Test different patterns
    patterns = [
        r'FROM\s+([a-zA-Z_][a-zA-Z0-9_.]*(?:\.[a-zA-Z_][a-zA-Z0-9_.]*)*)',  # Qualified table names
        r'FROM\s+`([^`]+)`',  # Backtick quoted table names
        r'FROM\s+([a-zA-Z_]\w*)',  # Simple table names
        r'FROM\s+([^\s\w]+)',  # Any non-whitespace after FROM
        r'FROM\s+(\S+)',  # Any non-space after FROM
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"Pattern {i}: {pattern}")
        matches = re.findall(pattern, test_query, re.IGNORECASE)
        print(f"Matches: {matches}")
        print()

def debug_with_cleaning():
    from core.sql_validator import SQLValidator
    
    validator = SQLValidator()
    test_query = "SELECT category_id, category_name FROM project.dataset.categories WHERE category_id = 1"
    
    print("Testing with actual validator:")
    print(f"Query: {test_query}")
    
    # Test the column name detection
    print(f"\nTesting _is_likely_column_name:")
    test_identifier = "project.dataset.categories"
    is_column = validator._is_likely_column_name(test_identifier, test_query)
    print(f"Is '{test_identifier}' likely a column? {is_column}")
    
    # Test cleaning
    print(f"\nTesting _clean_identifier:")
    cleaned = validator._clean_identifier(test_identifier)
    print(f"Cleaned '{test_identifier}' -> '{cleaned}'")
    
    # Call the actual extraction method
    tables, columns, joins = validator._extract_sql_elements(test_query)
    print(f"\nFinal results:")
    print(f"Tables found: {tables}")
    print(f"Columns found: {columns}")
    print(f"Joins found: {joins}")

if __name__ == "__main__":
    debug_sql_extraction()
    print("=" * 50)
    debug_with_cleaning()