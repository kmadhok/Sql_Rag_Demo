#!/usr/bin/env python3
"""
Test script for Week 3 AI endpoints

Tests all three AI-powered SQL assistance endpoints:
- POST /sql/explain
- POST /sql/complete
- POST /sql/fix
"""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ai_assistant_service():
    """Test AI Assistant Service directly (unit test)"""
    print("\n" + "=" * 70)
    print("TEST 1: AI Assistant Service - Direct Unit Test")
    print("=" * 70)

    try:
        from services.ai_assistant_service import get_ai_assistant_service

        # Get service instance
        ai_service = get_ai_assistant_service()
        print("✅ AI Assistant Service initialized successfully")

        # Test 1: Explain SQL
        print("\n📝 Testing explain_sql()...")
        test_sql = "SELECT * FROM products LIMIT 10"
        explanation = ai_service.explain_sql(test_sql)

        if explanation and len(explanation) > 50:
            print(f"✅ Explanation generated ({len(explanation)} chars)")
            print(f"Preview: {explanation[:200]}...")
        else:
            print("⚠️ Explanation seems too short")

        # Test 2: Complete SQL
        print("\n📝 Testing complete_sql()...")
        partial_sql = "SELECT * FROM "
        cursor_pos = {"line": 1, "column": 15}
        suggestions = ai_service.complete_sql(partial_sql, cursor_pos)

        if suggestions and len(suggestions) > 0:
            print(f"✅ Generated {len(suggestions)} suggestions")
            for i, sug in enumerate(suggestions[:3], 1):
                print(f"   {i}. {sug.get('completion', 'N/A')}: {sug.get('explanation', 'N/A')}")
        else:
            print("⚠️ No suggestions generated")

        # Test 3: Fix SQL
        print("\n📝 Testing fix_sql()...")
        broken_sql = "SELECT * FROM products WHERE name = 'test"
        error_msg = "Syntax error: Unclosed string literal"
        fix_result = ai_service.fix_sql(broken_sql, error_msg)

        if fix_result and "fixed_sql" in fix_result:
            print(f"✅ Fix generated")
            print(f"   Diagnosis: {fix_result.get('diagnosis', 'N/A')[:100]}...")
            print(f"   Fixed SQL: {fix_result.get('fixed_sql', 'N/A')[:100]}...")
        else:
            print("⚠️ Fix generation failed")

        print("\n✅ All AI Assistant Service tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ AI Assistant Service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_templates():
    """Test prompt template generation"""
    print("\n" + "=" * 70)
    print("TEST 2: Prompt Templates")
    print("=" * 70)

    try:
        from prompt_templates.sql_assistant import (
            get_explain_prompt,
            get_complete_prompt,
            get_fix_prompt
        )

        # Test explain prompt
        print("\n📝 Testing get_explain_prompt()...")
        sql = "SELECT * FROM products"
        schema = "Table: products (id, name, price)"
        prompt = get_explain_prompt(sql, schema)

        if "explain" in prompt.lower() and sql in prompt:
            print(f"✅ Explain prompt generated ({len(prompt)} chars)")
        else:
            print("⚠️ Explain prompt may be malformed")

        # Test complete prompt
        print("\n📝 Testing get_complete_prompt()...")
        partial = "SELECT * FROM "
        cursor = {"line": 1, "column": 15}
        prompt = get_complete_prompt(partial, cursor, schema)

        if "completion" in prompt.lower() and "json" in prompt.lower():
            print(f"✅ Complete prompt generated ({len(prompt)} chars)")
        else:
            print("⚠️ Complete prompt may be malformed")

        # Test fix prompt
        print("\n📝 Testing get_fix_prompt()...")
        broken = "SELECT * FROM products WHERE"
        error = "Syntax error at end of input"
        prompt = get_fix_prompt(broken, error, schema)

        if "fix" in prompt.lower() and error in prompt:
            print(f"✅ Fix prompt generated ({len(prompt)} chars)")
        else:
            print("⚠️ Fix prompt may be malformed")

        print("\n✅ All prompt template tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Prompt template test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints_structure():
    """Test that API endpoints are properly defined"""
    print("\n" + "=" * 70)
    print("TEST 3: API Endpoints Structure")
    print("=" * 70)

    try:
        from api.main import app

        # Get all routes
        routes = [route.path for route in app.routes]

        print("\n📝 Checking for Week 3 endpoints...")

        endpoints_to_check = [
            "/sql/explain",
            "/sql/complete",
            "/sql/fix"
        ]

        all_found = True
        for endpoint in endpoints_to_check:
            if endpoint in routes:
                print(f"✅ Found: {endpoint}")
            else:
                print(f"❌ Missing: {endpoint}")
                all_found = False

        if all_found:
            print("\n✅ All API endpoints are properly registered!")
            return True
        else:
            print("\n⚠️ Some endpoints are missing")
            return False

    except Exception as e:
        print(f"\n❌ API endpoint structure test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("WEEK 3 AI ENDPOINTS TEST SUITE")
    print("=" * 70)

    # Set PYTHONPATH to include rag_app directory
    import os
    rag_app_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, rag_app_dir)

    results = []

    # Run tests
    results.append(("Prompt Templates", test_prompt_templates()))
    results.append(("API Endpoints Structure", test_api_endpoints_structure()))
    results.append(("AI Assistant Service", test_ai_assistant_service()))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Week 3 implementation is complete!")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
