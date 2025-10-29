"""
Simple SQL Validation Tests

This file tests the SQL validation logic without requiring
BigQuery or complex mocking setup.
"""

import asyncio
from services.sql_service import SQLService

class TestSQLValidation:
    """Simple tests for SQL validation logic"""
    
    def setup_method(self):
        """Create fresh SQL service for each test"""
        self.sql_service = SQLService()
    
    # ==================== VALID QUERIES ====================
    
    async def test_safe_select_queries(self):
        """Test that safe SELECT queries pass validation"""
        safe_queries = [
            "SELECT * FROM users LIMIT 10;",
            "SELECT name, email FROM users WHERE id > 100;",
            "SELECT COUNT(*) FROM orders;",
            "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id;",
            "SELECT * FROM users WHERE created_at > '2024-01-01';",
            "WITH user_stats AS (SELECT id, name FROM users) SELECT * FROM user_stats;"
        ]
        
        print("\n=== Testing Safe SELECT Queries ===")
        for query in safe_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == True, f"Should be valid: {query}"
            assert result['error'] is None
            print(f"✅ Safe: {query[:50]}...")
    
    # ==================== DANGEROUS QUERIES ====================
    
    async def test_dangerous_sql_queries(self):
        """Test that dangerous SQL queries are rejected"""
        dangerous_queries = [
            "DROP TABLE users;",
            "DELETE FROM users WHERE id = 1;",
            "UPDATE users SET role = 'admin';",
            "INSERT INTO users VALUES (1, 'test');",
            "CREATE TABLE test (id INT);",
            "ALTER TABLE users ADD COLUMN test INT;",
            "TRUNCATE TABLE users;",
            "EXEC xp_cmdshell 'dir';",
            "SELECT * FROM users; DROP TABLE users;"  # SQL injection attempt
        ]
        
        print("\n=== Testing Dangerous Queries ===")
        for query in dangerous_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == False, f"Should be invalid: {query}"
            assert result['error'] is not None
            print(f"🚫 Dangerous: {query[:50]}... -> {result['error']}")
    
    # ==================== INVALID QUERIES ====================
    
    async def test_invalid_non_select_queries(self):
        """Test that non-SELECT queries are rejected"""
        invalid_queries = [
            "SHOW TABLES;",
            "DESCRIBE users;",
            "EXPLAIN SELECT * FROM users;",
            "BEGIN TRANSACTION;",
            "COMMIT;",
            "ROLLBACK;",
            "USE database_name;",
            "SET @variable = 'value';"
        ]
        
        print("\n=== Testing Invalid Non-SELECT Queries ===")
        for query in invalid_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == False, f"Should be invalid: {query}"
            print(f"❌ Invalid: {query[:50]}... -> {result['error']}")
    
    # ==================== SYNTAX TESTS ====================
    
    async def test_missing_semicolon(self):
        """Test that SQL queries must end with semicolon"""
        invalid_queries = [
            "SELECT * FROM users",
            "SELECT * FROM users  ",  # trailing spaces but no semicolon
            "SELECT * FROM users\n\n",  # newlines but no semicolon
            "SELECT * FROM users\t\t",  # tabs but no semicolon
        ]
        
        print("\n=== Testing Missing Semicolon ===")
        for query in invalid_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == False
            assert "semicolon" in result['error']
            print(f"❌ Missing semicolon: '{query.strip()}'")
    
    async def test_mixed_case_queries(self):
        """Test that SQL validation works with different cases"""
        mixed_case_queries = [
            "select * from users limit 5;",
            "Select * From Users LIMIT 5;",
            "SELECT * FROM useRs lImiT 5;",
            "     SELECT * FROM USERS LIMIT 5     ",  # with leading/trailing spaces
        ]
        
        print("\n=== Testing Mixed Case Queries ===")
        for query in mixed_case_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == True
            print(f"✅ Mixed case OK: '{query.strip()}'")
    
    # ==================== EDGE CASES ====================
    
    async def test_empty_query(self):
        """Test empty query handling"""
        result = await self.sql_service._validate_sql("")
        assert result['valid'] == False
        print(f"✅ Empty query correctly rejected: {result['error']}")
    
    async def test_whitespaces(self):
        """Test queries with various whitespace patterns"""
        whitespace_queries = [
            "    SELECT *   FROM   users  ;    ",  # Lots of spaces
            "\n\nSELECT * FROM\nusers;\n\n",  # Newlines
            "SELECT\t*\tFROM\tusers\t;\n",  # Tabs
        ]
        
        print("\n=== Testing Whitespace Handling ===")
        for query in whitespace_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == True
            print(f"✅ Whitespace handled: Query parsed successfully")
    
    async def test_subquery_validation(self):
        """Test validation of complex queries with subqueries"""
        complex_queries = [
            "SELECT * FROM (SELECT id, name FROM users) AS subquery;",
            "SELECT COUNT(*) FROM (SELECT id FROM orders GROUP BY user_id) as grouped;",
            "SELECT u.name FROM users u WHERE u.id IN (SELECT user_id FROM orders WHERE amount > 100);",
            "SELECT MAX(created_at) FROM users WHERE id IN (SELECT user_id FROM orders GROUP BY user_id HAVING COUNT(*) > 3);"
        ]
        
        print("\n=== Testing Complex Subqueries ===")
        for query in complex_queries:
            result = await self.sql_service._validate_sql(query)
            assert result['valid'] == True
            print(f"✅ Complex query OK: {query[:60]}...")
    

# ==================== RUN TESTS ====================

async def run_all_tests():
    """Run all SQL validation tests"""
    test_instance = TestSQLValidation()
    
    try:
        test_instance.setup_method()
        await test_instance.test_safe_select_queries()
        await test_instance.test_safe_select_queries()  # Call again to reset instance
        test_instance.setup_method() 
        await test_instance.test_dangerous_sql_queries()
        test_instance.setup_method()
        await test_instance.test_invalid_non_select_queries()
        test_instance.setup_method()
        await test_instance.test_missing_semicolon()
        test_instance.setup_method()
        await test_instance.test_mixed_case_queries()
        test_instance.setup_method()
        await test_instance.test_empty_query()
        test_instance.setup_method()
        await test_instance.test_whitespaces()
        test_instance.setup_method()
        await test_instance.test_subquery_validation()
        
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("🔒 SQL validation is working correctly")
        print("🛡️ Dangerous queries are being rejected")
        print("✅ Safe queries are being approved")
        print("="*50)
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Running SQL Service Validation Tests...")
    asyncio.run(run_all_tests())