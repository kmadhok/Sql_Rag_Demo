#!/usr/bin/env python3
"""
Quick test for the Windows multiprocessing fix in standalone_embedding_generator.py

This script creates a small test dataset and verifies the fix works without the
"cannot pickle '_thread.RLock' object" error.
"""

import tempfile
import pandas as pd
from pathlib import Path

def test_standalone_fix():
    """Test the Windows multiprocessing fix"""
    print("🧪 Testing Windows multiprocessing fix...")
    
    # Create small test dataset
    test_data = pd.DataFrame({
        'query': [
            'SELECT * FROM customers WHERE status = "active"',
            'SELECT COUNT(*) FROM orders',
            'SELECT c.name FROM customers c JOIN orders o ON c.id = o.customer_id',
            'SELECT AVG(total) FROM orders',
            'SELECT category, COUNT(*) FROM products GROUP BY category'
        ],
        'description': [
            'Get active customers',
            'Count all orders',
            'Customer names with orders',
            'Average order value',
            'Products by category'
        ],
        'table': ['customers', 'orders', 'customers,orders', 'orders', 'products'],
        'joins': ['', '', 'c.id = o.customer_id', '', '']
    })
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test CSV
        csv_path = Path(temp_dir) / "test_queries.csv"
        test_data.to_csv(csv_path, index=False)
        print(f"📄 Created test CSV with {len(test_data)} queries")
        
        # Test the fixed standalone generator
        try:
            from standalone_embedding_generator import StandaloneEmbeddingGenerator
            
            generator = StandaloneEmbeddingGenerator(
                csv_path=str(csv_path),
                output_dir=str(Path(temp_dir) / "test_output"),
                batch_size=2,  # Small batches for testing
                max_workers=2,  # Limited workers for test
                verbose=True
            )
            
            print("🔧 Starting embedding generation test...")
            success = generator.generate(force_rebuild=True)
            
            if success:
                print("✅ Windows multiprocessing fix SUCCESSFUL!")
                print("🎉 No more 'cannot pickle _thread.RLock' errors!")
                return True
            else:
                print("❌ Test failed - but not due to pickle error")
                return False
                
        except Exception as e:
            error_msg = str(e)
            if "cannot pickle" in error_msg and "_thread.RLock" in error_msg:
                print(f"❌ Windows pickle error still present: {e}")
                return False
            else:
                print(f"❌ Different error occurred: {e}")
                print("(This might be an Ollama connection issue, not the pickle fix)")
                return False

if __name__ == "__main__":
    import sys
    import multiprocessing
    
    # Set Windows multiprocessing method
    if sys.platform == "win32":
        multiprocessing.set_start_method('spawn', force=True)
    
    success = test_standalone_fix()
    
    if success:
        print("\n🚀 Ready to use with your high-spec system:")
        print("python standalone_embedding_generator.py --csv 'your_data.csv' --batch-size 150 --workers 12")
    else:
        print("\n⚠️  Test failed - check error messages above")
    
    sys.exit(0 if success else 1)