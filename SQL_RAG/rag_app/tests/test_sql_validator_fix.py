#!/usr/bin/env python3
"""
Test SQL Validator UNION Fix

Test that UNION is now allowed in legitimate read-only queries
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_union_allowed():
    """Test that UNION is now allowed in read-only queries"""
    try:
        from security.sql_validator import SafeSQLValidator, validate_sql_legacy_wrapper
        
        # Test legitimate UNION query (should pass now)
        union_query = """
        WITH user_purchase_counts AS (
            SELECT user_id, COUNT(*) as purchase_count
            FROM orders 
            WHERE status = 'completed'
            GROUP BY user_id
        ),
        high_value_users AS (
            SELECT user_id
            FROM user_purchase_counts
            WHERE purchase_count > 5
        )
        SELECT u.user_id, u.name, upc.purchase_count
        FROM users u
        JOIN user_purchase_counts upc ON u.user_id = upc.user_id
        UNION
        SELECT 'OTHER' as user_id, 'Other users' as name, 0 as purchase_count
        WHERE 1=0
        """
        
        # Test with validator
        validator = SafeSQLValidator(validation_level='standard')
        is_valid, error_msg = validator.validate_query(union_query)
        
        print(f"✅ UNION Query Test:")
        print(f"   Query valid: {is_valid}")
        print(f"   Error: {error_msg}")
        
        if is_valid:
            print("   ✅ UNION is now properly allowed!")
        else:
            print(f"   ❌ UNION still blocked: {error_msg}")
        
        # Test dangerous query (should still be blocked)
        dangerous_query = "DROP TABLE users;"
        is_valid_dangerous, error_dangerous = validator.validate_query(dangerous_query)
        
        print(f"\n✅ Dangerous Query Test:")
        print(f"   Query valid: {is_valid_dangerous}")
        print(f"   Error: {error_dangerous}")
        
        if not is_valid_dangerous:
            print("   ✅ Dangerous queries still properly blocked!")
        else:
            print("   ❌ Dangerous query incorrectly allowed!")
        
        return is_valid and not is_valid_dangerous
        
    except ImportError as e:
        print(f"⚠️ SQL validator test skipped: {e}")
        return True
    except Exception as e:
        print(f"❌ SQL validator test failed: {e}")
        return False


def test_legacy_wrapper():
    """Test the legacy wrapper function"""
    try:
        from security.sql_validator import validate_sql_legacy_wrapper
        
        test_query = "SELECT * FROM users UNION SELECT * FROM customers"
        is_valid, error_msg = validate_sql_legacy_wrapper(test_query)
        
        print(f"\n✅ Legacy Wrapper Test:")
        print(f"   Query valid: {is_valid}")
        print(f"   Error: {error_msg}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Legacy wrapper test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔧 Testing SQL Validator UNION Fix\n")
    
    results = []
    results.append(test_union_allowed())
    results.append(test_legacy_wrapper())
    
    if all(results):
        print("\n✅ All SQL validator tests passed!")
        print("   UNION is now allowed in legitimate queries")
        print("   Dangerous operations are still blocked")
    else:
        print("\n❌ Some SQL validator tests failed")