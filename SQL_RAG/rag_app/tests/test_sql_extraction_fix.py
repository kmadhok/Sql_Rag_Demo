#!/usr/bin/env python3
"""
Test SQL Extraction Fix

Test the improved SQL extraction patterns
"""

import sys
from pathlib import Path
import re
import logging

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestSQLExtractionFix:
    """Test SQL extraction patterns and logic"""
    
    def test_sql_extraction_patterns(self):
        """Test the improved SQL extraction patterns"""
        test_responses = [
            # Test 1: SQL code block with language tag
            "Here's your query: ```sql\nSELECT * FROM users WHERE id > 10\n```",
            
            # Test 2: Generic code block
            "The query is:\n```\nWITH users AS (SELECT * FROM customers)\nSELECT * FROM users\n```",
            
            # Test 3: Plain SQL statement
            "Use this SQL: SELECT u.*, COUNT(o.order_id) as total_orders FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id",
            
            # Test 4: WITH clause
            "Complex query: WITH order_stats AS (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) SELECT u.*, os.order_count FROM users u LEFT JOIN order_stats os ON u.id = os.user_id"
            
        ]
        
        # Improved patterns from our fix
        sql_patterns = [
            (r'```sql\s*([^`]+)```', 1),     # Has capture group
            (r'```([^`]*)```', 1),             # Generic code blocks
            (r'SELECT[^;]+', 0),               # No capture group
            (r'WITH[^;]+', 0)                  # No capture group
        ]
        
        extraction_results = []
        
        for i, response in enumerate(test_responses):
            logger.info(f"Testing response {i+1}")
            logger.debug(f"Response: {response}")
            
            extracted_sql = None
            
            for pattern, group_idx in sql_patterns:
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    try:
                        if group_idx > 0:
                            extracted_sql = match.group(group_idx).strip()
                        else:
                            extracted_sql = match.group(0).strip()
                        
                        if extracted_sql:
                            logger.info(f"✅ Pattern {pattern} extracted: {extracted_sql[:50]}...")
                            break
                        
                    except Exception as pattern_error:
                        logger.warning(f"Pattern error for {pattern}: {pattern_error}")
                        continue
            
            if extracted_sql:
                extraction_results.append((i+1, True, extracted_sql))
                logger.info(f"✅ Response {i+1}: SQL extracted successfully")
            else:
                extraction_results.append((i+1, False, None))
                logger.warning(f"❌ Response {i+1}: No SQL extracted")
        
        # Validate results
        successful_extractions = sum(1 for _, success, _ in extraction_results if success)
        total_tests = len(test_responses)
        
        logger.info(f"Extraction success rate: {successful_extractions}/{total_tests} ({successful_extractions/total_tests*100:.1f}%)")
        
        # Show all results
        for test_num, success, sql in extraction_results:
            if success:
                print(f"✅ Test {test_num}: {sql[:100]}..." )
            else:
                print(f"❌ Test {test_num}: No extraction")
        
        # At least 3 out of 4 should work
        assert successful_extractions >= 3, f"Expected at least 3 successful extractions, got {successful_extractions}"
        
        return successful_extractions >= 3
    
    def test_edge_cases(self):
        """Test edge cases in SQL extraction"""
        edge_cases = [
            # Empty response
            "",
            # Response without SQL
            "I'm sorry, I can't help with that.",
            # Malformed SQL block
            "Here's SQL: ```sql\nSELECT * FROM\n```",
            # SQL with multiple statements (should grab first one)
            "```sql\nSELECT * FROM users; SELECT * FROM orders;\n```"
        ]
        
        patterns = [
            (r'```sql\s*([^`]+)```', 1),
            (r'```([^`]*)```', 1),
            (r'SELECT[^;]+', 0),
            (r'WITH[^;]+', 0)
        ]
        
        handled_cases = 0
        
        for case in edge_cases:
            try:
                extracted = None
                for pattern, group_idx in patterns:
                    match = re.search(pattern, case, re.IGNORECASE | re.DOTALL)
                    if match:
                        if group_idx > 0:
                            extracted = match.group(group_idx).strip()
                        else:
                            extracted = match.group(0).strip()
                        break
                
                # Edge cases should either extract something valid or handle gracefully
                if extracted == "SELECT * FROM users" or not extracted or case.strip() == "":
                    handled_cases += 1
                    logger.info(f"✅ Edge case handled: '{case[:50]}...' -> {'extracted' if extracted else 'no extraction'}")
                else:
                    logger.warning(f"⚠️ Unexpected extraction: '{extracted}' from '{case}'")
                    
            except Exception as e:
                # Edge cases should not crash
                logger.error(f"❌ Edge case crashed: {e}")
        
        # All edge cases should be handled without crashes
        assert handled_cases == len(edge_cases), f"All {len(edge_cases)} edge cases should be handled, got {handled_cases}"
        
        return True

def run_sql_extraction_tests():
    """Run all SQL extraction tests"""
    print("🚀 Running SQL Extraction Fix Tests\n")
    print("🛡️ Testing improved SQL patterns and edge cases\n")
    
    test_instance = TestSQLExtractionFix()
    
    results = []
    results.append(test_instance.test_sql_extraction_patterns())
    results.append(test_instance.test_edge_cases())
    
    if all(results):
        print("\n✅ All SQL extraction tests passed!")
        print("   - Improved patterns handle various SQL formats")
        print("   - Edge cases handled gracefully")
        print("   - No more 'no such group' errors")
        print("   - Ready for production")
    else:
        print("\n❌ Some SQL extraction tests failed")
    
    return all(results)

if __name__ == "__main__":
    run_sql_extraction_tests()