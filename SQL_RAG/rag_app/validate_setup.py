#!/usr/bin/env python3
"""
Setup Validation Script for SQL RAG Application

This script validates that all dependencies, configurations, and data files
are correctly set up for your SQL RAG application.

Usage:
    python3 validate_setup.py

Features:
- Validates all Python dependencies
- Tests API connections (Gemini, Ollama)
- Checks data file formats
- Validates core application imports
- Provides actionable error messages and solutions
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")

class SetupValidator:
    """Main validator class for SQL RAG application setup"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.app_dir = Path(__file__).parent
        
    def validate_python_version(self) -> bool:
        """Validate Python version"""
        print_header("🐍 Python Version Check")
        
        version_info = sys.version_info
        required_major = 3
        required_minor = 11  # Minimum supported
        recommended_minor = 12  # Recommended version
        
        if version_info.major != required_major or version_info.minor < required_minor:
            self.errors.append(
                f"Python {required_major}.{required_minor}+ required. "
                f"Current: {version_info.major}.{version_info.minor}.{version_info.micro}"
            )
            print_error(f"Python {version_info.major}.{version_info.minor}.{version_info.micro} detected")
            print_error(f"Minimum required: Python {required_major}.{required_minor}")
            print_info("Install Python 3.12: https://www.python.org/downloads/")
            return False
        elif version_info.minor < recommended_minor:
            self.warnings.append(
                f"Python {required_major}.{recommended_minor} recommended. "
                f"Current: {version_info.major}.{version_info.minor}.{version_info.micro}"
            )
            print_warning(f"Python {version_info.major}.{version_info.minor}.{version_info.micro} detected")
            print_warning(f"Recommended: Python {required_major}.{recommended_minor}")
        
        print_success(f"Python {version_info.major}.{version_info.minor}.{version_info.micro} is compatible")
        return True
    
    def validate_dependencies(self) -> bool:
        """Validate all required Python packages"""
        print_header("📦 Dependency Check")
        
        # Core dependencies with their import names
        dependencies = {
            'streamlit': 'streamlit',
            'langchain': 'langchain',
            'langchain-community': 'langchain_community',
            'langchain-core': 'langchain_core',
            'langchain-ollama': 'langchain_ollama',
            'google-generativeai': 'google.genai',
            'faiss-cpu': 'faiss',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'rank-bm25': 'rank_bm25'
        }
        
        # Optional dependencies
        optional_deps = {
            'pyarrow': 'pyarrow',
            'graphviz': 'graphviz',
            'pyvis': 'pyvis'
        }
        
        missing_deps = []
        missing_optional = []
        
        for package, import_name in dependencies.items():
            try:
                __import__(import_name)
                print_success(f"{package} installed")
            except ImportError:
                missing_deps.append(package)
                print_error(f"{package} missing")
        
        for package, import_name in optional_deps.items():
            try:
                __import__(import_name)
                print_success(f"{package} installed (optional)")
            except ImportError:
                missing_optional.append(package)
                print_warning(f"{package} missing (optional)")
        
        if missing_deps:
            self.errors.append(f"Missing required packages: {', '.join(missing_deps)}")
            print_error("Install missing packages:")
            print_info("pip install -r requirements.txt")
            return False
        
        if missing_optional:
            self.warnings.append(f"Missing optional packages: {', '.join(missing_optional)}")
            print_info("Optional packages can be installed for enhanced features")
        
        print_success("All required dependencies installed")
        return True
    
    def validate_core_imports(self) -> bool:
        """Validate core application module imports"""
        print_header("🔧 Core Module Import Check")
        
        # Updated for new organized directory structure
        core_modules = [
            ('core/gemini_client', 'GeminiClient, test_gemini_connection'),
            ('data/data_source_manager', 'DataSourceManager'),
            ('core/simple_rag_simple_gemini', 'answer_question_simple_gemini'),
            ('app', None)  # Updated to new main app file
        ]
        
        optional_modules = [
            ('core/hybrid_retriever', 'HybridRetriever, SearchWeights'),
            ('core/query_rewriter', 'QueryRewriter, create_query_rewriter'),
            ('core/schema_manager', 'SchemaManager, create_schema_manager'),
        ]
        
        all_good = True
        
        # Check core modules
        for module_path, imports in core_modules:
            module_file = self.app_dir / f"{module_path}.py"
            module_name = module_path.replace('/', '.')  # Convert path to module name
            
            if not module_file.exists():
                self.errors.append(f"Core module missing: {module_path}.py")
                print_error(f"{module_path}.py not found")
                all_good = False
                continue
            
            if imports:  # Test imports
                try:
                    # Add the directories to Python path for imports
                    if str(self.app_dir) not in sys.path:
                        sys.path.insert(0, str(self.app_dir))
                    exec(f"from {module_name} import {imports}")
                    print_success(f"{module_path}.py imports work")
                except ImportError as e:
                    self.errors.append(f"Import error in {module_path}: {str(e)}")
                    print_error(f"{module_path}.py import failed: {e}")
                    all_good = False
            else:
                print_success(f"{module_path}.py exists")
        
        # Check optional modules
        for module_path, imports in optional_modules:
            module_file = self.app_dir / f"{module_path}.py"
            module_name = module_path.replace('/', '.')  # Convert path to module name
            
            if not module_file.exists():
                self.warnings.append(f"Optional module missing: {module_path}.py")
                print_warning(f"{module_path}.py not found (optional)")
                continue
            
            try:
                # Add the directories to Python path for imports
                if str(self.app_dir) not in sys.path:
                    sys.path.insert(0, str(self.app_dir))
                exec(f"from {module_name} import {imports}")
                print_success(f"{module_path}.py imports work (optional)")
            except ImportError as e:
                self.warnings.append(f"Optional import error in {module_path}: {str(e)}")
                print_warning(f"{module_path}.py import failed (optional): {e}")
        
        return all_good
    
    def validate_api_configuration(self) -> bool:
        """Validate API configurations"""
        print_header("🔑 API Configuration Check")
        
        all_good = True
        
        # Check Vertex AI project configuration
        vertex_project = os.getenv('vertex_ai_client')
        if not vertex_project:
            self.errors.append("vertex_ai_client environment variable not set")
            print_error("vertex_ai_client not found")
            print_info("Set it with: export vertex_ai_client='your-gcp-project-id'")
            print_info("Configure authentication: gcloud auth application-default login")
            all_good = False
        else:
            print_success(f"vertex_ai_client set: {vertex_project}")
        
        # Test Gemini connection if project is available
        if vertex_project:
            try:
                from core.gemini_client import test_gemini_connection
                success, message = test_gemini_connection()
                if success:
                    print_success("Gemini API connection successful")
                else:
                    self.errors.append(f"Gemini API connection failed: {message}")
                    print_error(f"Gemini connection failed: {message}")
                    all_good = False
            except Exception as e:
                self.warnings.append(f"Could not test Gemini connection: {str(e)}")
                print_warning(f"Gemini connection test failed: {e}")
        
        # Check Ollama service
        try:
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:11434/api/tags'],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                print_success("Ollama service is running")
                
                # Check for nomic-embed-text model
                try:
                    model_result = subprocess.run(
                        ['ollama', 'list'],
                        capture_output=True, text=True, timeout=10
                    )
                    if 'nomic-embed-text' in model_result.stdout:
                        print_success("nomic-embed-text model available")
                    else:
                        self.warnings.append("nomic-embed-text model not found")
                        print_warning("nomic-embed-text model missing")
                        print_info("Install with: ollama pull nomic-embed-text")
                except Exception as e:
                    self.warnings.append(f"Could not check Ollama models: {str(e)}")
                    print_warning(f"Ollama model check failed: {e}")
                    
            else:
                self.warnings.append("Ollama service not running")
                print_warning("Ollama service not running")
                print_info("Start with: ollama serve")
        except Exception as e:
            self.warnings.append(f"Could not check Ollama service: {str(e)}")
            print_warning(f"Ollama service check failed: {e}")
            print_info("Install Ollama: https://ollama.ai/download")
        
        return all_good
    
    def validate_data_files(self) -> bool:
        """Validate data files and their formats"""
        print_header("📊 Data Files Check")
        
        # Required data files
        required_files = {
            'sample_queries_with_metadata.csv': ['query'],
            'sample_queries_metadata_schema.csv': ['tableid', 'columnnames', 'datatype']
        }
        
        all_good = True
        
        for filename, required_columns in required_files.items():
            filepath = self.app_dir / filename
            
            if not filepath.exists():
                self.errors.append(f"Required data file missing: {filename}")
                print_error(f"{filename} not found")
                all_good = False
                continue
            
            # Validate file format
            try:
                import pandas as pd
                df = pd.read_csv(filepath)
                
                if df.empty:
                    self.errors.append(f"Data file is empty: {filename}")
                    print_error(f"{filename} is empty")
                    all_good = False
                    continue
                
                # Check required columns
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    self.errors.append(
                        f"Missing columns in {filename}: {', '.join(missing_columns)}"
                    )
                    print_error(f"{filename} missing columns: {', '.join(missing_columns)}")
                    print_info(f"Available columns: {', '.join(df.columns)}")
                    all_good = False
                else:
                    print_success(f"{filename}: {len(df)} rows, all required columns present")
                    
            except Exception as e:
                self.errors.append(f"Error reading {filename}: {str(e)}")
                print_error(f"Error reading {filename}: {e}")
                all_good = False
        
        return all_good
    
    def validate_generated_assets(self) -> bool:
        """Check for generated assets (optional)"""
        print_header("🗂️ Generated Assets Check")
        
        # Check for vector indices
        faiss_dir = self.app_dir / "faiss_indices"
        if faiss_dir.exists() and any(faiss_dir.iterdir()):
            indices = list(faiss_dir.glob("index_*"))
            print_success(f"Vector indices found: {len(indices)} indices")
            for index_dir in indices[:3]:  # Show first 3
                print_success(f"  - {index_dir.name}")
        else:
            print_warning("No vector indices found")
            print_info("Generate with: python3 standalone_embedding_generator.py --csv 'sample_queries_with_metadata.csv'")
        
        # Check for analytics cache
        analytics_dir = self.app_dir / "catalog_analytics"
        if analytics_dir.exists() and (analytics_dir / "join_analysis.json").exists():
            print_success("Analytics cache found")
        else:
            print_warning("No analytics cache found")
            print_info("Generate with: python3 catalog_analytics_generator.py --csv 'sample_queries_with_metadata.csv'")
        
        return True  # These are optional, so always return True
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite"""
        print_header("🔍 SQL RAG Application Setup Validation")
        print_info("Validating your complete RAG application setup...")
        
        validation_steps = [
            ("Python Version", self.validate_python_version),
            ("Dependencies", self.validate_dependencies),
            ("Core Imports", self.validate_core_imports),
            ("API Configuration", self.validate_api_configuration),
            ("Data Files", self.validate_data_files),
            ("Generated Assets", self.validate_generated_assets)
        ]
        
        results = {}
        for step_name, validator_func in validation_steps:
            try:
                results[step_name] = validator_func()
            except Exception as e:
                self.errors.append(f"Validation error in {step_name}: {str(e)}")
                results[step_name] = False
        
        # Summary
        print_header("📋 Validation Summary")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for step_name, result in results.items():
            if result:
                print_success(f"{step_name}: PASSED")
            else:
                print_error(f"{step_name}: FAILED")
        
        print(f"\n{Colors.BOLD}Results: {passed}/{total} checks passed{Colors.END}")
        
        if self.errors:
            print_error(f"\n{len(self.errors)} Critical Issues Found:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print_warning(f"\n{len(self.warnings)} Warnings:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        # Final recommendations
        print_header("🚀 Next Steps")
        
        if not self.errors:
            print_success("Your SQL RAG application is ready to run!")
            print_info("Start the application with:")
            print("    streamlit run app.py")
            
            if not (self.app_dir / "faiss_indices").exists():
                print_info("\nOptional: Generate embeddings first for better performance:")
                print("    python3 data/standalone_embedding_generator.py --csv 'sample_queries_with_metadata.csv'")
            
            return True
        else:
            print_error("Please fix the critical issues above before running the application.")
            print_info("\nRefer to SETUP_GUIDE.md for detailed instructions.")
            return False

def main():
    """Main validation script entry point"""
    validator = SetupValidator()
    success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()