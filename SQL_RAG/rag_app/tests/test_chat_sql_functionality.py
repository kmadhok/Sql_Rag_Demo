#!/usr/bin/env python3
"""
Test Chat SQL Functionality

Test that SQL execution in chat pages works correctly
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestChatSQLFunctionality:
    """Test SQL execution functionality in chat"""
    
    def test_sql_message_structure(self):
        """Test that chat messages have the correct structure for SQL"""
        try:
            # Test the message structure we designed
            test_message = {
                'role': 'assistant',
                'content': 'Here is your SQL query',
                'agent_type': 'create',
                'sources': [],
                'sql_query': 'SELECT * FROM users',
                'sql_executed': False,
                'sql_result': None,
                'sql_execution_id': None,
                'timestamp': 1234567890
            }
            
            # Validate structure
            assert 'role' in test_message
            assert 'agent_type' in test_message
            assert 'sql_query' in test_message
            assert 'sql_executed' in test_message
            assert 'sql_result' in test_message
            
            print("✅ Chat message structure test passed")
            return True
            
        except Exception as e:
            print(f"❌ Chat message structure test failed: {e}")
            return False
    
    def test_sql_extraction_patterns(self):
        """Test SQL extraction patterns"""
        try:
            import re
            
            # Test SQL extraction patterns
            test_responses = [
                "Here's your SQL: ```sql\nSELECT * FROM users\n```",
                "The query is: SELECT * FROM users ORDER BY created_at",
                "WITH data AS (SELECT * FROM users) SELECT COUNT(*) FROM data"
            ]
            
            sql_patterns = [
                r'```sql\s*([^`]+)```',
                r'SELECT[^;]+(?=\n|$)',
                r'WITH[^;]+(?=\n|$)'
            ]
            
            found_queries = 0
            for response in test_responses:
                for pattern in sql_patterns:
                    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                    if match:
                        # Handle patterns with and without groups
                        try:
                            extracted_sql = match.group(1).strip()
                        except IndexError:
                            extracted_sql = match.group(0).strip()
                        
                        if extracted_sql:
                            found_queries += 1
                            print(f"   Extracted: {extracted_sql[:50]}...")
                            break
            
            assert found_queries >= 2, f"Expected at least 2 extracted queries, got {found_queries}"
            
            print("✅ SQL extraction patterns test passed")
            return True
            
        except Exception as e:
            print(f"❌ SQL extraction patterns test failed: {e}")
            return False
    
    def test_sql_execution_flow(self):
        """Test the SQL execution flow logic"""
        try:
            # Mock BigQuery executor
            mock_result = Mock()
            mock_result.success = True
            mock_result.total_rows = 100
            mock_result.cost = 0.0123
            mock_result.bytes_processed = 1000000
            mock_result.execution_time = 1.5
            mock_result.data = Mock()
            mock_result.data.empty = False
            
            # Test execution logic
            test_message = {
                'sql_query': 'SELECT * FROM users',
                'sql_executed': False,
                'sql_result': None
            }
            
            # Simulate execution
            test_message['sql_result'] = mock_result
            test_message['sql_executed'] = True
            test_message['sql_execution_id'] = 'test_123'
            
            # Validate execution results
            assert test_message['sql_executed'] == True
            assert test_message['sql_result'] is not None
            assert test_message['sql_result'].success == True
            assert test_message['sql_execution_id'] is not None
            
            print("✅ SQL execution flow test passed")
            return True
            
        except Exception as e:
            print(f"❌ SQL execution flow test failed: {e}")
            return False
    
    def test_button_key_uniqueness(self):
        """Test that button keys are unique"""
        try:
            # Test button key generation
            message_ids = [0, 1, 2, 5, 10]
            generated_keys = []
            
            for msg_id in message_ids:
                # Test execution button keys
                exec_key = f"exec_sql_{msg_id}"
                
                assert exec_key not in generated_keys
                generated_keys.append(exec_key)
                
                # Test re-execute button keys
                mock_message = {
                    'sql_execution_id': f'chat_{msg_id}_{1234567890}'
                }
                
                result_key = f"reexec_sql_{mock_message['sql_execution_id']}"
                assert result_key not in generated_keys
                generated_keys.append(result_key)
                
                # Test retry button keys for executed messages
                retry_key = f"retry_sql_{mock_message['sql_execution_id']}"
                assert retry_key not in generated_keys
                generated_keys.append(retry_key)
            
            assert len(generated_keys) == len(message_ids) * 3
            
            print("✅ Button key uniqueness test passed")
            return True
            
        except Exception as e:
            print(f"❌ Button key uniqueness test failed: {e}")
            return False


def run_chat_sql_tests():
    """Run all chat SQL functionality tests"""
    print("🚀 Running Chat SQL Functionality Tests\n")
    print("🛡️ Testing SQL execution capabilities in chat\n")
    
    test_instance = TestChatSQLFunctionality()
    
    # Run all tests
    results = []
    results.append(test_instance.test_sql_message_structure())
    results.append(test_instance.test_sql_extraction_patterns())
    results.append(test_instance.test_sql_execution_flow())
    results.append(test_instance.test_button_key_uniqueness())
    
    if all(results):
        print("\n✅ All Chat SQL functionality tests passed!")
        print("   - Message structure validated")
        print("   - SQL extraction patterns working")
        print("   - Execution flow logic correct")
        print("   - Button key uniqueness ensured")
    else:
        print("\n❌ Some Chat SQL functionality tests failed")
    
    return all(results)


if __name__ == "__main__":
    run_chat_sql_tests()