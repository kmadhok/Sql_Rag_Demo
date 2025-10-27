#!/usr/bin/env python3
"""
Master test runner for app_simple_gemini.py testing
Runs all test suites and provides comprehensive coverage report
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestRunner:
    """Comprehensive test runner for all test suites"""
    
    def __init__(self):
        self.test_suites = [
            ("Refactoring Safety", "test_refactoring_safety.py"),
            ("Security Improvements", "test_security_improvements.py"),
            ("App Comprehensive", "test_app_simple_gemini_comprehensive.py"),
            ("Streamlit Workflow", "test_streamlit_workflow.py"),
            ("Performance & Regression", "test_performance_regression.py")
        ]
        self.results = {}
        self.total_elapsed = 0
    
    def run_test_suite(self, suite_name: str, test_file: str) -> Tuple[bool, float, str]:
        """Run a single test suite and return results"""
        print(f"\n{'='*60}")
        print(f"🚀 Running {suite_name}")
        print(f"📁 File: {test_file}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run the test file as a subprocess
            result = subprocess.run(
                [sys.executable, test_file],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                success = True
                status = "✅ PASSED"
            else:
                success = False
                status = "❌ FAILED"
            
            output = result.stdout + result.stderr
            
            print(f"\n{status} - {elapsed_time:.2f}s")
            
            # Show first few lines of output
            if output:
                output_lines = output.split('\n')
                for line in output_lines[:10]:  # Show first 10 lines
                    if line.strip():
                        print(f"   {line}")
                if len(output_lines) > 10:
                    print(f"   ... ({len(output_lines) - 10} more lines)")
            
            return success, elapsed_time, output
            
        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            print(f"\n⏰ TIMEOUT - {elapsed_time:.2f}s (limit: 300s)")
            return False, elapsed_time, "Test suite timed out after 5 minutes"
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n💥 CRASH - {elapsed_time:.2f}s")
            print(f"   Error: {e}")
            return False, elapsed_time, str(e)
    
    def run_all_suites(self) -> bool:
        """Run all test suites and collect results"""
        print("🎯 Comprehensive Testing for app_simple_gemini.py")
        print("🛡️  Ensuring refactoring safety and quality")
        
        overall_start = time.time()
        all_passed = True
        
        for suite_name, test_file in self.test_suites:
            success, elapsed_time, output = self.run_test_suite(suite_name, test_file)
            
            self.results[suite_name] = {
                'success': success,
                'elapsed_time': elapsed_time,
                'output': output,
                'file': test_file
            }
            
            if not success:
                all_passed = False
        
        self.total_elapsed = time.time() - overall_start
        
        return all_passed
    
    def print_summary(self):
        """Print comprehensive test results summary"""
        print(f"\n{'='*80}")
        print(f"🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        
        passed_suites = sum(1 for r in self.results.values() if r['success'])
        total_suites = len(self.results)
        
        for suite_name, result in self.results.items():
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            time_str = f"{result['elapsed_time']:.2f}s"
            print(f"   {status:<10} {suite_name:<30} ({time_str})")
        
        print(f"\n{'='*80}")
        print(f"OVERALL: {passed_suites}/{total_suites} test suites passed")
        print(f"Total Time: {self.total_elapsed:.2f}s")
        
        if passed_suites == total_suites:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"✅ Your app_simple_gemini.py is safe for refactoring")
            print(f"🚀 You can proceed with confidence")
            return True
        else:
            print(f"\n⚠️  SOME TESTS FAILED!")
            print(f"🛠️  Fix the issues before refactoring")
            print(f"📋 Review the failed test suites above")
            return False
    
    def generate_detailed_report(self, output_file: str = None):
        """Generate detailed HTML report of test results"""
        if output_file is None:
            output_file = Path(__file__).parent / "test_results.html"
        
        html_content = self._generate_html_report()
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"\n📄 Detailed report saved to: {output_file}")
    
    def _generate_html_report(self) -> str:
        """Generate HTML content for detailed report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Results - app_simple_gemini.py</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .test-suite {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .suite-header {{ padding: 15px; font-weight: bold; }}
        .passed {{ background: #d4edda; color: #155724; }}
        .failed {{ background: #f8d7da; color: #721c24; }}
        .suite-content {{ padding: 15px; }}
        .output {{ background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }}
        .metrics {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .metric {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Test Results for app_simple_gemini.py</h1>
        <p>Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <div class="metrics">
            <div class="metric">
                <h3>{len(self.results)}</h3>
                <p>Total Suites</p>
            </div>
            <div class="metric">
                <h3>{sum(1 for r in self.results.values() if r['success'])}</h3>
                <p>Passed</p>
            </div>
            <div class="metric">
                <h3>{sum(1 for r in self.results.values() if not r['success'])}</h3>
                <p>Failed</p>
            </div>
            <div class="metric">
                <h3>{self.total_elapsed:.2f}s</h3>
                <p>Total Time</p>
            </div>
        </div>
    </div>
"""
        
        for suite_name, result in self.results.items():
            status_class = "passed" if result['success'] else "failed"
            status_text = "✅ PASSED" if result['success'] else "❌ FAILED"
            
            html += f"""
    <div class="test-suite">
        <div class="suite-header {status_class}">
            {status_text} {suite_name} ({result['elapsed_time']:.2f}s)
        </div>
        <div class="suite-content">
            <p><strong>File:</strong> {result['file']}</p>
            <h4>Output:</h4>
            <div class="output">{result['output']}</div>
        </div>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html


def main():
    """Main test runner function"""
    print("🐕 pikushi's Comprehensive Test Suite for Refactoring Safety")
    print("=" * 60)
    
    # Change to the tests directory
    os.chdir(Path(__file__).parent)
    
    # Verify all test files exist
    missing_files = []
    for suite_name, test_file in TestRunner().test_suites:
        if not Path(test_file).exists():
            missing_files.append(test_file)
    
    if missing_files:
        print(f"❌ Missing test files: {missing_files}")
        return False
    
    # Run all tests
    runner = TestRunner()
    all_passed = runner.run_all_suites()
    
    # Print summary
    safe_to_proceed = runner.print_summary()
    
    # Generate detailed report
    runner.generate_detailed_report()
    
    # Exit with appropriate code
    return safe_to_proceed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)