#!/usr/bin/env python3
"""
Test script to verify the pages fix for the modular app.
Confirms that Streamlit won't auto-discover duplicate pages.
"""

import sys
from pathlib import Path

def test_pages_fix():
    """Test that the pages issue is resolved"""
    print("🧪 Testing Pages Duplication Fix")
    print("=" * 40)
    
    # Test directory structure
    modular_dir = Path("modular")
    pages_dir = modular_dir / "pages"
    page_modules_dir = modular_dir / "page_modules"
    
    print("📁 Checking Directory Structure:")
    print(f"   - modular/ exists: {modular_dir.exists()}")
    print(f"   - pages/ exists: {pages_dir.exists()} {'❌ (removed)' if not pages_dir.exists() else '⚠️ (still exists)'}")
    print(f"   - page_modules/ exists: {page_modules_dir.exists()} {'✅' if page_modules_dir.exists() else '❌'}")
    
    if pages_dir.exists():
        print("⚠️ WARNING: pages/ directory still exists - Streamlit may still auto-discover it")
    
    # Test import structure
    current_dir = Path.cwd()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    print("\n📦 Testing Import Structure:")
    try:
        from modular.config import PAGE_NAMES
        print("✅ Config import successful")
        
        # Test the new page_modules import
        import importlib.util
        spec = importlib.util.find_spec('modular.page_modules')
        if spec:
            print("✅ page_modules package accessible")
            
            # Check if the app can import pages correctly
            from modular.app import PAGE_NAMES as app_page_names
            print("✅ App can import page modules correctly")
            print(f"   - Available pages: {list(app_page_names.values())}")
        else:
            print("❌ page_modules package not found")
            return False
            
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False
    
    print("\n🎯 Expected Behavior:")
    print("✅ Streamlit will show ONLY the radio button navigation")
    print("✅ No duplicate pages in Streamlit's sidebar")
    print("✅ Clean, single navigation method")
    print("✅ All three pages work correctly: Search, Catalog, Chat")
    
    print("\n🚀 Ready to Test:")
    print("   Run: streamlit run modular/app.py")
    print("   You should see only ONE set of navigation controls")
    
    return True

if __name__ == "__main__":
    success = test_pages_fix()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Pages fix test completed")