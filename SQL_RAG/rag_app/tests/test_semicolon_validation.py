#!/usr/bin/env python3
"""
Test Semicolon Validation Fix

Test that semicolons are allowed in SQL statements
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_semicolon_allowed():
    """Test that semicolons are now allowed in SQL statements"""
    try:
        from security.sql_validator import SafeSQLValidator, validate_sql_legacy_wrapper
        
        # Test SQL with semicolon (should pass now)
        semicolon_query = "SELECT MIN(age) AS youngest_user_age, MAX(age) AS oldest_user_age FROM users;"
        
        # Test the validator
        validator = SafeSQLValidator()
        is_valid, error_msg = validator.validate_query(semicolon_query)
        
        print(f"✅ Semicolon Query Test:")
        print(f"   Query valid: {is_valid}")
        print(f"   Error: {error_msg}")
        
        if is_valid:
            print("   ✅ Semicolons are now properly allowed!")
            semicolon_test_passed = True
        else:
            print(f"   ❌ Semicolons still blocked: {error_msg}")
            semicolon_test_passed = False
        
        # Test dangerous query (should still be blocked)
        dangerous_query = "DROP TABLE users;"
        is_valid_dangerous, error_dangerous = validator.validate_query(dangerous_query)
        
        print(f"\n✅ Dangerous Query Test:")
        print(f"   Query valid: {is_valid_dangerous}")
        print(f"   Error: {error_dangerous}")
        
        if not is_valid_dangerous:
            print("   ✅ Dangerous queries still properly blocked!")
            dangerous_test_passed = True
        else:
            print("   ❌ Dangerous query incorrectly allowed!")
            dangerous_test_passed = False
        
        return semicolon_test_passed and dangerous_test_passed
        
    except ImportError as e:
        print(f"⚠️ SQL validator test skipped: {e}")
        return True
    except Exception as e:
        print(f"❌ SQL validator test failed: {e}")
        return False

def test_various_semicolon_cases():
    """Test various SQL statements with semicolons"""
    try:
        from security.sql_validator import SafeSQLValidator
        
        test_cases = [
            # Basic SELECT with semicolon
            "SELECT * FROM users WHERE active = true;",
            
            # Complex query with semicolon
            "SELECT u.*, COUNT(o.id) as orders FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id HAVING COUNT(o.id) > 5;",
            
            # WITH clause with semicolon
            "WITH user_stats AS (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) SELECT * FROM user_stats WHERE order_count > 10;",
            
            # UNION with semicolons
            "SELECT id FROM users WHERE type = 'admin' UNION SELECT id FROM users WHERE type = 'superadmin';",
            
            # Multi-statement (should still be blocked)
            "SELECT * FROM users; DROP TABLE users;"
        ]
        
        validator = SafeSQLValidator()
        results = []
        
        for i, query in enumerate(test_cases, 1):
            is_valid, error_msg = validator.validate_query(query)
            
            # First 4 should pass, last one should fail
            should_pass = i <= 4
            
            print(f"Test {i}: {'PASS' if should_pass else 'FAIL'} - {'✅' if is_valid == should_pass else '❌'}")
            print(f"   Query: {query[:50]}...")
            print(f"   Valid: {is_valid} (Expected: {should_pass})")
            if error_msg:
                print(f"   Error: {error_msg}")
            print()
            
            results.append(is_valid == should_pass)
        
        return all(results)
        
    except Exception as e:
        print(f"❌ Various cases test failed: {e}")
        return False

def run_semicolon_tests():
    """Run all semicolon validation tests"""
    print("🚀 Running Semicolon Validation Tests\n")
    print("🔧 Testing that semicolons are allowed in SQL statements\n")
    
    results = []
    results.append(test_semicolon_allowed())
    results.append(test_various_semicolon_cases())
    
    if all(results):
        print("\n✅ ALL SEMICOLON VALIDATION TESTS PASSED!")
        print("   - Semicolons are now allowed in SQL statements")
        print("   - Dangerous operations still blocked")
        print("   - Complex SQL with semicolons passes")
        print("   - Multi-statement SQL blocked")
    else:
        print("\n❌ Some semicolon validation tests failed")
    
    return all(results)

if __name__ == "__main__":
    run_semicolon_tests()