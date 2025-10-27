#!/usr/bin/env python3
"""
Refactoring Readiness Assessment
Final validation that app_simple_gemini.py is ready for safe refactoring
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class RefactoringReadinessAssessment:
    """Comprehensive assessment of refactoring readiness"""
    
    def __init__(self):
        self.assessments = []
    
    def add_assessment(self, category: str, status: str, details: str, critical: bool = False):
        """Add an assessment result"""
        self.assessments.append({
            'category': category,
            'status': status,  # 'PASS', 'WARN', 'FAIL'
            'details': details,
            'critical': critical
        })
    
    def assess_function_structure(self):
        """Assess function structure and organization"""
        print("🔍 Assessing function structure...")
        
        app_path = Path(__file__).parent.parent / "app_simple_gemini.py"
        with open(app_path, 'r') as f:
            source_code = f.read()
        
        # Count functions
        function_count = source_code.count('def ')
        self.add_assessment(
            "Function Count",
            "PASS" if function_count >= 30 else "FAIL",
            f"Found {function_count} functions (expected ≥ 30)",
            critical=True
        )
        
        # Check for critical functions
        critical_functions = [
            'main', 'load_vector_store', 'load_csv_data', 'calculate_context_utilization',
            'detect_agent_type', 'create_chat_page', 'estimate_token_count'
        ]
        
        missing_critical = []
        for func in critical_functions:
            if f"def {func}(" not in source_code:
                missing_critical.append(func)
        
        self.add_assessment(
            "Critical Functions",
            "PASS" if not missing_critical else "FAIL",
            f"Missing: {missing_critical}" if missing_critical else "All critical functions present",
            critical=True
        )
        
        # Check function size (rough estimate by counting lines between defs)
        lines = source_code.split('\n')
        long_functions = []
        current_function_lines = 0
        
        for line in lines:
            if line.startswith('def '):
                if current_function_lines > 100:  # Rough estimate of long function
                    long_functions.append(current_function_lines)
                current_function_lines = 0
            current_function_lines += 1
        
        if long_functions:
            avg_long = sum(long_functions) / len(long_functions)
            self.add_assessment(
                "Function Size",
                "WARN",
                f"Some functions appear long (avg ~{avg_long:.0f} lines) - consider splitting",
                critical=False
            )
        else:
            self.add_assessment(
                "Function Size",
                "PASS",
                "Functions appear reasonably sized",
                critical=False
            )
    
    def assess_error_handling(self):
        """Assess error handling patterns"""
        print("🔍 Assessing error handling...")
        
        app_path = Path(__file__).parent.parent / "app_simple_gemini.py"
        with open(app_path, 'r') as f:
            source_code = f.read()
        
        # Check for try/except patterns
        try_count = source_code.count('try:')
        except_count = source_code.count('except')
        
        self.add_assessment(
            "Error Handling Structure",
            "PASS" if try_count >= 10 else "WARN",
            f"Found {try_count} try blocks and {except_count} except blocks",
            critical=True
        )
        
        # Check for specific error handling patterns
        has_streamlit_errors = "st.error(" in source_code
        has_logging = "logger." in source_code
        has_fallbacks = "return None" in source_code
        
        if has_streamlit_errors and has_logging and has_fallbacks:
            self.add_assessment(
                "Error Handling Quality",
                "PASS",
                "Comprehensive error handling with user feedback and logging",
                critical=True
            )
        else:
            missing = []
            if not has_streamlit_errors:
                missing.append("Streamlit error messages")
            if not has_logging:
                missing.append("Logging")
            if not has_fallbacks:
                missing.append("Fallback returns")
            
            self.add_assessment(
                "Error Handling Quality",
                "WARN",
                f"Consider adding: {', '.join(missing)}",
                critical=False
            )
    
    def assess_data_loading_patterns(self):
        """Assess data loading patterns and fallbacks"""
        print("🔍 Assessing data loading patterns...")
        
        app_path = Path(__file__).parent.parent / "app_simple_gemini.py"
        with open(app_path, 'r') as f:
            source_code = f.read()
        
        # Check for loading functions
        loading_functions = [
            'load_vector_store', 'load_csv_data', 'load_lookml_safe_join_map',
            'load_schema_manager', 'get_available_indices'
        ]
        
        present_loading = []
        for func in loading_functions:
            if f"def {func}(" in source_code:
                present_loading.append(func)
        
        self.add_assessment(
            "Data Loading Functions",
            "PASS" if len(present_loading) >= 4 else "WARN",
            f"Found {len(present_loading)}/{len(loading_functions)} loading functions",
            critical=True
        )
        
        # Check for fallback patterns
        has_fallback_imports = "try:" in source_code and "except ImportError:" in source_code
        has_graceful_degradation = "availability" in source_code.lower() or "optional" in source_code.lower()
        
        if has_fallback_imports and has_graceful_degradation:
            self.add_assessment(
                "Graceful Degradation",
                "PASS",
                "Good fallback patterns for optional dependencies",
                critical=True
            )
        else:
            self.add_assessment(
                "Graceful Degradation",
                "WARN",
                "Could improve fallback patterns for optional dependencies",
                critical=False
            )
    
    def assess_documentation_quality(self):
        """Assess documentation and comments"""
        print("🔍 Assessing documentation quality...")
        
        app_path = Path(__file__).parent.parent / "app_simple_gemini.py"
        with open(app_path, 'r') as f:
            source_code = f.read()
        
        # Check for docstrings
        docstring_count = source_code.count('"""')
        comment_lines = len([line for line in source_code.split('\n') if line.strip().startswith('#')])
        
        line_count = len(source_code.split('\n'))
        comment_ratio = comment_lines / line_count if line_count > 0 else 0
        
        self.add_assessment(
            "Documentation Coverage",
            "PASS" if comment_ratio > 0.05 else "WARN",
            f"{comment_ratio:.1%} comment coverage ({comment_lines} comments in {line_count} lines)",
            critical=False
        )
        
        self.add_assessment(
            "Function Documentation",
            "PASS" if docstring_count >= 20 else "WARN",
            f"Found {docstring_count} docstring blocks",
            critical=False
        )
        
        # Check for module docstring
        if source_code.startswith('#!/usr/bin/env python3') and '"""' in source_code[:500]:
            self.add_assessment(
                "Module Documentation",
                "PASS",
                "Good module-level documentation",
                critical=False
            )
        else:
            self.add_assessment(
                "Module Documentation",
                "WARN",
                "Consider adding module-level documentation",
                critical=False
            )
    
    def assess_refactoring_complexity(self):
        """Assess overall refactoring complexity"""
        print("🔍 Assessing refactoring complexity...")
        
        app_path = Path(__file__).parent.parent / "app_simple_gemini.py"
        
        # Get file size
        file_size = app_path.stat().st_size
        lines = len(app_path.read_text().split('\n'))
        
        # Size-based complexity
        if file_size > 200000:  # > 200KB
            size_status = "WARN"
            size_details = f"Large file ({file_size/1024:.1f}KB, {lines} lines) - consider splitting"
        elif file_size > 100000:  # > 100KB
            size_status = "WARN" 
            size_details = f"Medium-large file ({file_size/1024:.1f}KB, {lines} lines) - monitor size"
        else:
            size_status = "PASS"
            size_details = f"Reasonable size ({file_size/1024:.1f}KB, {lines} lines)"
        
        self.add_assessment(
            "File Size",
            size_status,
            size_details,
            critical=False
        )
        
        # Dependencies
        import_lines = [line for line in app_path.read_text().split('\n') if line.strip().startswith('import') or line.strip().startswith('from')]
        complex_deps = len([line for line in import_lines if 'langchain' in line.lower() or 'streamlit' in line.lower()])
        
        if complex_deps > 10:
            self.add_assessment(
                "Dependency Complexity",
                "WARN",
                f"Many complex dependencies ({complex_deps} major imports) - careful refactoring needed",
                critical=True
            )
        else:
            self.add_assessment(
                "Dependency Complexity",
                "PASS",
                f"Manageable dependency count ({complex_deps} major imports)",
                critical=False
            )
    
    def generate_report(self):
        """Generate final assessment report"""
        print("\n" + "="*80)
        print("📋 REFACTORING READINESS ASSESSMENT")
        print("="*80)
        
        critical_issues = []
        warnings = []
        passes = []
        
        for assessment in self.assessments:
            icon = "❌" if assessment['status'] == 'FAIL' else "⚠️" if assessment['status'] == 'WARN' else "✅"
            critical_marker = " [CRITICAL]" if assessment['critical'] else ""
            
            print(f"\n{icon} {assessment['category']}{critical_marker}")
            print(f"   {assessment['details']}")
            
            if assessment['status'] == 'FAIL':
                critical_issues.append(assessment)
            elif assessment['status'] == 'WARN':
                warnings.append(assessment)
            else:
                passes.append(assessment)
        
        print(f"\n{'='*80}")
        print(f"🎯 SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Passes: {len(passes)}")
        print(f"⚠️  Warnings: {len(warnings)}")
        print(f"❌ Critical Issues: {len(critical_issues)}")
        
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES - Must fix before refactoring:")
            for issue in critical_issues:
                print(f"   • {issue['category']}: {issue['details']}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS - Consider addressing:")
            for warning in warnings:
                print(f"   • {warning['category']}: {warning['details']}")
        
        # Overall readiness
        if not critical_issues:
            if not warnings:
                print(f"\n🎉 EXCELLENT - Ready for refactoring with confidence!")
                print(f"🚀 All critical and warning areas addressed")
                return "READY"
            else:
                print(f"\n✅ GOOD - Ready for refactoring with caution")
                print(f"📝 Address warnings for optimal refactoring")
                return "READY_WITH_CAUTION"
        else:
            print(f"\n❌ NOT READY - Fix critical issues first")
            return "NOT_READY"
    
    def run_full_assessment(self):
        """Run complete assessment"""
        print("🔍 Starting Comprehensive Refactoring Readiness Assessment")
        print("🛡️ Ensuring your app is safe to refactor")
        
        # Run all assessments
        self.assess_function_structure()
        self.assess_error_handling()
        self.assess_data_loading_patterns()
        self.assess_documentation_quality()
        self.assess_refactoring_complexity()
        
        # Generate report
        return self.generate_report()


def main():
    """Main assessment function"""
    print("🐕 pikushi's Refactoring Readiness Assessment")
    
    # Change to the parent directory
    os.chdir(Path(__file__).parent.parent)
    
    # Run assessment
    assessor = RefactoringReadinessAssessment()
    readiness = assessor.run_full_assessment()
    
    # Return status
    return readiness in ["READY", "READY_WITH_CAUTION"]


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)