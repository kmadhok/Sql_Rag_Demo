"""
Standalone SQL Validation Test

This demonstrates the SQL service concepts without requiring
external dependencies or complex imports.
"""

class SQLValidator:
    """Standalone SQL validator demonstrating the concepts"""
    
    @staticmethod
    def validate_sql(sql: str) -> dict:
        """Validates SQL for safety - simplified version of our SQL service"""
        
        if not sql or not sql.strip():
            return {
                'valid': False,
                'error': 'SQL query cannot be empty'
            }
        
        # Convert to uppercase for validation
        sql_upper = sql.strip().upper()
        
        # Check for dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'MERGE', 'REPLACE', 'CALL'
        ]
        
        for keyword in dangerous_keywords:
            if f' {keyword} ' in f' {sql_upper} ' or sql_upper.startswith(keyword):
                return {
                    'valid': False,
                    'error': f'Dangerous operation {keyword} is not allowed'
                }
        
        # Only allow SELECT, WITH, SHOW, DESCRIBE queries
        allowed_starters = ['SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'EXPLAIN']
        
        if not any(sql_upper.startswith(starter) for starter in allowed_starters):
            return {
                'valid': False,
                'error': 'Only SELECT queries are allowed for security reasons'
            }
        
        # Require semicolon ending
        if not sql.rstrip().endswith(';'):
            return {
                'valid': False,
                'error': 'SQL query must end with semicolon (;)'
            }
        
        return {
            'valid': True,
            'error': None
        }


class TestSQLValidation:
    """Test the SQL validation logic"""
    
    def __init__(self):
        self.validator = SQLValidator()
    
    def run_test(self, test_name, queries, should_be_valid=True):
        """Run a group of tests and report results"""
        print(f"\n{'='*50}")
        print(f"{test_name}")
        print(f"{'='*50}")
        
        passed = 0
        failed = 0
        
        for i, query in enumerate(queries, 1):
            result = self.validator.validate_sql(query)
            is_valid = result['valid']
            
            if is_valid == should_be_valid:
                passed += 1
                status = "✅ PASS"
            else:
                failed += 1 
                status = "❌ FAIL"
            
            print(f"{status:6} Test {i}: {query[:50]}...")
            if not is_valid:
                print(f"       Error: {result['error']}")
        
        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🧪 SQL Validation Test Suite")
        print("Testing the security logic from our SQL Service")
        
        all_passed = True
        
        # Test 1: Safe SELECT queries
        safe_queries = [
            "SELECT * FROM users LIMIT 10;",
            "SELECT name, email FROM users WHERE id > 100;",
            "SELECT COUNT(*) FROM orders;",
            "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id;",
            "SELECT * FROM users WHERE created_at > '2024-01-01';",
            "WITH user_stats AS (SELECT id, name FROM users) SELECT * FROM user_stats;",
            "select * from users limit 5;",  # lowercase
            "Select * From Users LIMIT 5;",  # mixed case
        ]
        
        result1 = self.run_test("SAFE SELECT QUERIES", safe_queries, should_be_valid=True)
        all_passed &= result1
        
        # Test 2: Dangerous queries
        dangerous_queries = [
            "DROP TABLE users;",
            "DELETE FROM users WHERE id = 1;",
            "UPDATE users SET role = 'admin';",
            "INSERT INTO users VALUES (1, 'test');",
            "CREATE TABLE test (id INT);",
            "ALTER TABLE users ADD COLUMN test INT;",
            "TRUNCATE TABLE users;",
            "EXEC xp_cmdshell 'dir';",
            "SELECT * FROM users; DROP TABLE users;",  # SQL injection
            "MERGE INTO users USING backup ON users.id = backup.id WHEN MATCHED THEN UPDATE;"
        ]
        
        result2 = self.run_test("DANGEROUS QUERIES", dangerous_queries, should_be_valid=False)
        all_passed &= result2
        
        # Test 3: Invalid commands
        invalid_commands = [
            "SHOW TABLES;",
            "DESCRIBE users;",
            "EXPLAIN SELECT * FROM users;",
            "BEGIN TRANSACTION;",
            "COMMIT;",
            "ROLLBACK;",
            "USE database_name;",
            "SET @variable = 'value';"
        ]
        
        result3 = self.run_test("INVALID COMMANDS", invalid_commands, should_be_valid=False)
        all_passed &= result3
        
        # Test 4: Syntax errors
        syntax_errors = [
            "SELECT * FROM users",  # Missing semicolon
            "SELECT * FROM users  ",  # Only spaces
            "SELECT * FROM users\n\n",  # Only newline
            "SELECT * FROM users\t\t",  # Only tabs
            "",  # Empty
            "   ",  # Only whitespace
        ]
        
        result4 = self.run_test("SYNTAX ERRORS", syntax_errors, should_be_valid=False)
        all_passed &= result4
        
        # Test 5: Complex but safe queries
        complex_queries = [
            "SELECT * FROM (SELECT id, name FROM users) AS subquery;",
            "SELECT COUNT(*) FROM (SELECT id FROM orders GROUP BY user_id) as grouped;",
            "SELECT u.name FROM users u WHERE u.id IN (SELECT user_id FROM orders WHERE amount > 100);",
            "SELECT MAX(created_at) FROM users WHERE id IN (SELECT user_id FROM orders GROUP BY user_id HAVING COUNT(*) > 3);",
            "       SELECT     *    FROM    users   LIMIT    5     ;    "  # Extra spaces
        ]
        
        result5 = self.run_test("COMPLEX BUT SAFE QUERIES", complex_queries, should_be_valid=True)
        all_passed &= result5
        
        # Final results
        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}")
        
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print("\n✅ The SQL validation logic is working correctly:")
            print("  • Safe SELECT queries are allowed")
            print("  • Dangerous operations are blocked")
            print("  • SQL injection attempts are rejected")
            print("  • Basic syntax is enforced")
            print("\n🔒 Your SQL Service security is ROCK SOLID!")
        else:
            print("❌ Some tests failed - review the output above")
        
        print(f"{'='*60}")
        return all_passed


if __name__ == "__main__":
    tester = TestSQLValidation()
    tester.run_all_tests()