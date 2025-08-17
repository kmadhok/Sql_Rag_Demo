#!/usr/bin/env python3
"""
Verification script for the modular SQL RAG application setup.
Tests that all files are correctly referenced and ready for use.
"""

import sys
from pathlib import Path

def verify_modular_setup():
    """Verify the complete modular setup"""
    print("🔍 Verifying Modular SQL RAG Setup")
    print("=" * 50)
    
    # Add current directory to path
    sys.path.append('.')
    
    try:
        # Import configuration
        from modular.config import (
            DEFAULT_VECTOR_STORE, SCHEMA_CSV_PATH, CSV_PATH, 
            FAISS_INDICES_DIR, CATALOG_ANALYTICS_DIR
        )
        print("✅ Configuration import successful")
        
        # Test file references
        print("\n📁 Checking File References:")
        
        # 1. CSV Data File
        csv_exists = CSV_PATH.exists()
        print(f"   📄 CSV Data: {CSV_PATH.name} {'✅' if csv_exists else '❌'}")
        if csv_exists:
            # Check CSV structure
            try:
                import pandas as pd
                df = pd.read_csv(CSV_PATH)
                expected_columns = ['query', 'description', 'tables', 'joins']
                has_columns = all(col in df.columns for col in expected_columns)
                print(f"      - Structure: {'✅' if has_columns else '❌'} ({len(df)} rows, columns: {list(df.columns)})")
            except Exception as e:
                print(f"      - Structure check failed: {e}")
        
        # 2. Schema File
        schema_exists = SCHEMA_CSV_PATH.exists()
        print(f"   🗃️ Schema File: {SCHEMA_CSV_PATH.name} {'✅' if schema_exists else '❌'}")
        if schema_exists:
            try:
                import pandas as pd
                schema_df = pd.read_csv(SCHEMA_CSV_PATH)
                print(f"      - Structure: ✅ ({len(schema_df)} schema rows)")
                # Count unique tables
                if 'tableid' in schema_df.columns:
                    unique_tables = schema_df['tableid'].nunique()
                    print(f"      - Tables defined: {unique_tables}")
            except Exception as e:
                print(f"      - Structure check failed: {e}")
        
        # 3. Vector Store
        vector_store_path = FAISS_INDICES_DIR / DEFAULT_VECTOR_STORE
        vector_exists = vector_store_path.exists()
        print(f"   📂 Vector Store: {DEFAULT_VECTOR_STORE} {'✅' if vector_exists else '❌'}")
        if vector_exists:
            faiss_file = vector_store_path / 'index.faiss'
            pkl_file = vector_store_path / 'index.pkl'
            complete = faiss_file.exists() and pkl_file.exists()
            print(f"      - Complete: {'✅' if complete else '❌'} (faiss: {faiss_file.exists()}, pkl: {pkl_file.exists()})")
        
        # 4. Analytics Cache (Optional)
        analytics_exists = CATALOG_ANALYTICS_DIR.exists()
        print(f"   📊 Analytics Cache: {'✅' if analytics_exists else '⚠️ Optional'}")
        if analytics_exists:
            metadata_file = CATALOG_ANALYTICS_DIR / "cache_metadata.json"
            join_file = CATALOG_ANALYTICS_DIR / "join_analysis.json"
            cache_complete = metadata_file.exists() and join_file.exists()
            print(f"      - Complete: {'✅' if cache_complete else '⚠️ Partial'}")
        
        print("\n🔧 Testing Module Imports:")
        
        # Test key module imports (without external dependencies)
        modules_to_test = [
            ("modular.session_manager", "SessionManager"),
            ("modular.vector_store_manager", "VectorStoreManager"),
            ("modular.navigation", "Navigation"),
            ("modular.rag_engine", "RAGEngine")
        ]
        
        for module_name, class_name in modules_to_test:
            try:
                __import__(module_name)
                print(f"   ✅ {module_name}")
            except ImportError as e:
                print(f"   ⚠️ {module_name} (dependency issue: {type(e).__name__})")
            except Exception as e:
                print(f"   ❌ {module_name} (error: {e})")
        
        # Calculate readiness score
        checks = [csv_exists, schema_exists, vector_exists]
        optional_checks = [analytics_exists]
        
        required_passed = sum(checks)
        optional_passed = sum(optional_checks)
        
        print(f"\n📊 Setup Status:")
        print(f"   Required: {required_passed}/3 ({'✅ Ready' if required_passed == 3 else '❌ Issues'})")
        print(f"   Optional: {optional_passed}/1 ({'✅ Complete' if optional_passed == 1 else '⚠️ Partial'})")
        
        if required_passed == 3:
            print("\n🚀 Modular App Ready to Launch!")
            print("   Run: streamlit run modular/app.py")
            
            print("\n💡 Next Steps:")
            print("   1. Install dependencies: pip install -r requirements.txt")
            print("   2. Set up Google Cloud: export GOOGLE_CLOUD_PROJECT='your-project'")
            print("   3. Launch: streamlit run modular/app.py")
            
            if not analytics_exists:
                print("\n⚡ Performance Tip:")
                print("   Generate analytics cache for faster catalog browsing:")
                print("   python catalog_analytics_generator.py --csv 'sample_queries_with_metadata.csv'")
            
            return True
        else:
            print("\n❌ Setup Issues Detected")
            print("   Fix the missing files above before launching the app")
            return False
            
    except Exception as e:
        print(f"\n❌ Setup verification failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_modular_setup()
    sys.exit(0 if success else 1)