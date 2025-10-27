#!/usr/bin/env python3
"""
Test Answer Variable Analysis

Debug what's actually in the response @create generates
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_sql_extraction_service():
    """Test the dedicated SQL extraction service"""
    print("🔧 Testing SQL Extraction Service\n")
    
    try:
        from services.sql_extraction_service import extract_sql_from_text
        
        # Test with the sample response that was failing
        sample_response = '''-- Selects the minimum and maximum age from the users table
SELECT MIN(age) AS min_age, -- Finds the minimum age
MAX(age) AS max_age      -- Finds the maximum age
FROM users;'''
        
        print(f"📝 Input response:\n{sample_response}\n")
        
        result = extract_sql_from_text(sample_response, debug=True)
        
        if result:
            print(f"✅ Extraction successful:\n{result}\n")
        else:
            print("❌ Extraction failed\n")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_various_responses():
    """Test various response formats"""
    print("🧪 Testing various response formats\n")
    
    try:
        from services.sql_extraction_service import extract_sql_from_text
        
        test_cases = [
            "Simple response only has text about SQL but no actual query.",
            "Here's SQL: SELECT id, name FROM users WHERE active = true;",
            '''WITH data AS (
    SELECT * FROM orders
)
SELECT * FROM data;
No more queries.''',
            "-- This finds users\nSELECT * FROM users\nWHERE created_at >= '2024-01-01'"
        ]
        
        for i, response in enumerate(test_cases, 1):
            print(f"--- Test Case {i} ---")
            print(f"Input: {response[:100]}...")
            
            result = extract_sql_from_text(response, debug=False)
            
            if result:
                print(f"✅ Extracted: {result}")
            else:
                print("❌ No SQL found")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def analyze_chat_message_structure():
    """Analyze where chat responses are stored"""
    print("📊 Chat Message Structure Analysis\n")
    
    print("Based on the code analysis:")
    print("")
    print("1. 🔄 RAG Pipeline:")
    print("   answer_question_chat_mode() → returns (answer, sources, token_usage)")
    print("")
    print("2. 📦 Storage in chat_messages:")
    print("   ```python")
    print("   st.session_state.chat_messages.append({")
    print("       'role': 'assistant',")
    print("       'content': answer,  # ← This is the RAG response")
    print("       'agent_type': agent_type,")
    print("       'sql_query': extracted_sql,  # ← This should contain extracted SQL")
    print("       'sql_executed': False,")
    print("       'sql_result': None,")
    print("       'timestamp': time.time()")
    print("   })")
    print("   ```")
    print("")
    print("3. 🔍 Extraction Process:")
    print("   ```python")
    print("   if agent_type == 'create' and answer:")
    print("       answer  # ← This variable contains the full RAG response")
    print("       extracted_sql = extract_sql_from_text(answer)  # ← This extracts SQL")
    print("   ```")
    print("")
    print("4. 🐛 Issue Likely:")
    print("   - The 'answer' variable contains what RAG actually returned")
    print("   - We need to log the full 'answer' to see what LLM gave us")
    print("   - The extraction service should handle various response formats")
    print("")
    
    return True

def main():
    """Run all analysis tests"""
    print("🚀 SQL Extraction Analysis\n")
    print("🔍 Analyzing the chat response flow and extraction issues\n")
    
    results = []
    
    results.append(analyze_chat_message_structure())
    results.append(test_sql_extraction_service())
    results.append(test_various_responses())
    
    print("🎯 Key Findings:")
    print("   - Answer variable contains the full RAG response")
    print("   - We need to see what this response actually contains")
    print("   - Extraction service can handle multiple formats")
    print("   - Issue might be in response format, not extraction logic")
    
    return all(results)

if __name__ == "__main__":
    main()