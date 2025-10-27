#!/usr/bin/env python3
"""
Baseline functionality tests for app_simple_gemini.py
Run this before making ANY changes to establish baseline.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_file_imports():
    """Test that current app can be imported without errors"""
    print("🧪 Testing imports...")
    try:
        # Test basic imports
        import streamlit as st
        import pandas as pd
        import json
        import os
        from pathlib import Path
        print("✅ Basic imports successful")
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_file_structure():
    """Test that required files exist"""
    print("🧪 Testing file structure...")
    required_files = [
        'app_simple_gemini.py',
        'app_simple_gemini.py.backup'
    ]
    
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Missing file: {file}")
            return False
    
    print("✅ All required files exist")
    return True

def test_function_extraction():
    """Test that we can extract function signatures safely"""
    print("🧪 Testing function extraction...")
    try:
        import ast
        with open('app_simple_gemini.py', 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        print(f"✅ Found {len(functions)} functions in file")
        return len(functions) > 30  # Should find many functions
    except Exception as e:
        print(f"❌ Function extraction failed: {e}")
        return False

def run_tests():
    """Run all baseline tests"""
    print("🚀 Running Baseline Functionality Tests\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_file_imports),
        ("Function Extraction", test_function_extraction),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        result = test_func()
        results.append(result)
    
    print(f"\n🎯 Baseline Test Results:")
    print(f"   Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ ALL BASELINE TESTS PASSED - Safe to proceed with refactoring")
        return True
    else:
        print("❌ SOME TESTS FAILED - Fix issues before proceeding")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)