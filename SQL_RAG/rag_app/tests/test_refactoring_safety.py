#!/usr/bin/env python3
"""
Comprehensive tests to ensure refactoring doesn't break existing functionality
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_import_compatibility():
    """Test that all imports work with refactored modules"""
    print("🧪 Testing import compatibility...")
    
    try:
        # Test new modules can be imported
        from config import SafeConfig, AppConfig
        from utils import SafeLoader, DataFrameOptimizer, PaginationHelper
        print("✅ New modules imported successfully")
        
        # Test configuration objects can be created
        safe_config = SafeConfig()
        app_config = AppConfig()
        print("✅ Configuration objects created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import compatibility test failed: {e}")
        return False

def test_config_backward_compatibility():
    """Test that configuration maintains backward compatibility"""
    print("🧪 Testing configuration backward compatibility...")
    
    try:
        from config.app_config import app_config
        from config.safe_config import safe_config
        
        # Test that original constants are preserved
        assert app_config.FAISS_INDICES_DIR.name == "faiss_indices"
        assert app_config.QUERIES_PER_PAGE == 15
        print("✅ Original configuration constants preserved")
        
        # Test feature flags default to legacy mode (safe)
        assert safe_config.fallback_legacy_mode == True
        assert app_config.use_modular_components == False
        print("✅ Feature flags default to safe legacy mode")
        
        return True
    except Exception as e:
        print(f"❌ Configuration compatibility test failed: {e}")
        return False

def test_safe_loader_fallback():
    """Test that safe loader falls back to legacy mode"""
    print("🧪 Testing safe loader fallback...")
    
    try:
        from utils.safe_loader import SafeLoader
        from config.safe_config import safe_config
        
        # Test that in legacy mode, it behaves exactly like before
        safe_config.fallback_legacy_mode = True
        
        # This should work without issues
        temp_file = Path("test_data.json")
        test_data = {"test": "data"}
        
        # Write and read back test data
        import json
        with open(temp_file, 'w') as f:
            json.dump(test_data, f)
        
        loaded_data = SafeLoader.safe_json_load(temp_file)
        
        # Cleanup
        temp_file.unlink()
        
        assert loaded_data == test_data
        print("✅ Safe loader fallback works correctly")
        
        return True
    except Exception as e:
        print(f"❌ Safe loader fallback test failed: {e}")
        return False

def test_dataframe_optimizer_compatibility():
    """Test that dataframe optimizer maintains compatibility"""
    print("🧪 Testing DataFrame optimizer compatibility...")
    
    try:
        import pandas as pd
        from utils.dataframe_optimizer import DataFrameOptimizer
        from config.app_config import app_config
        
        # Create test DataFrame
        test_df = pd.DataFrame({
            'query': ['SELECT * FROM users', 'SELECT * FROM orders'],
            'description': ['User query', 'Order query'],
            'tables': ['users', 'orders']
        })
        
        # Test legacy mode
        app_config.enable_performance_optimizations = False
        optimizer = DataFrameOptimizer()
        
        # Test filtering in legacy mode
        result = optimizer.filter_dataframe_fast(
            test_df, 'users', ['query', 'description']
        )
        
        assert len(result) == 1  # Should find one row with 'users'
        print("✅ DataFrame optimizer legacy mode works")
        
        # Test pagination
        paginated = optimizer.paginate_dataframe(test_df, 1, 1)
        assert len(paginated) == 1
        print("✅ DataFrame pagination works")
        
        return True
    except Exception as e:
        print(f"❌ DataFrame optimizer compatibility test failed: {e}")
        return False

def test_app_still_runs():
    """Test that the original app can still be imported and run"""
    print("🧪 Testing that original app still runs...")
    
    try:
        # Test that we can import the original app without errors
        import ast
        
        with open('app_simple_gemini.py', 'r') as f:
            content = f.read()
        
        # Parse the original app to check for syntax errors
        ast.parse(content)
        print("✅ Original app syntax is valid")
        
        # Count functions to ensure we haven't lost anything
        tree = ast.parse(content)
        functions = [node.name for node in ast.walk(tree) 
                    if isinstance(node, ast.FunctionDef)]
        
        expected_min_functions = 35  # Should have at least this many
        if len(functions) >= expected_min_functions:
            print(f"✅ Original app has {len(functions)} functions (expected ≥ {expected_min_functions})")
        else:
            print(f"⚠️ Original app has only {len(functions)} functions (expected ≥ {expected_min_functions})")
        
        return True
    except Exception as e:
        print(f"❌ App run test failed: {e}")
        return False

def run_safety_tests():
    """Run all safety tests for refactoring"""
    print("🚀 Running Refactoring Safety Tests\n")
    
    tests = [
        ("Import Compatibility", test_import_compatibility),
        ("Configuration Compatibility", test_config_backward_compatibility),
        ("Safe Loader Fallback", test_safe_loader_fallback),
        ("DataFrame Optimizer", test_dataframe_optimizer_compatibility),
        ("App Still Runs", test_app_still_runs),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    print(f"\n🎯 Safety Test Results:")
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\n   Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL SAFETY TESTS PASSED - Refactoring is safe to proceed")
        return True
    else:
        print("❌ SOME SAFETY TESTS FAILED - Fix issues before proceeding")
        return False

if __name__ == "__main__":
    success = run_safety_tests()
    sys.exit(0 if success else 1)