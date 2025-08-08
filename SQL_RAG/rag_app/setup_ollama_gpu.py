#!/usr/bin/env python3
"""
Ollama GPU Setup and Optimization Script

Helps users configure Ollama for optimal GPU acceleration performance
with the standalone embedding generator.

Usage:
    python setup_ollama_gpu.py
    python setup_ollama_gpu.py --check-only
"""

import os
import sys
import subprocess
import platform
import json
import argparse
from pathlib import Path

def run_command(cmd, capture_output=True):
    """Run a command and return the result"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def check_ollama_installed():
    """Check if Ollama is installed and accessible"""
    print("🔍 Checking Ollama installation...")
    success, stdout, stderr = run_command("ollama --version")
    
    if success:
        print(f"✅ Ollama installed: {stdout}")
        return True
    else:
        print("❌ Ollama not found. Please install Ollama first:")
        print("   Windows: https://ollama.ai/download")
        print("   Or: curl -fsSL https://ollama.ai/install.sh | sh")
        return False

def check_ollama_running():
    """Check if Ollama server is running"""
    print("\n🔍 Checking if Ollama server is running...")
    success, stdout, stderr = run_command("curl -s http://localhost:11434/api/version")
    
    if success:
        try:
            version_info = json.loads(stdout)
            print(f"✅ Ollama server running: version {version_info.get('version', 'unknown')}")
            return True
        except:
            print("⚠️  Ollama server responding but couldn't parse version")
            return True
    else:
        print("❌ Ollama server not running")
        print("💡 Start it with: ollama serve")
        return False

def check_gpu_support():
    """Check for NVIDIA GPU support"""
    print("\n🔍 Checking GPU support...")
    
    # Check for NVIDIA GPU
    success, stdout, stderr = run_command("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits")
    
    if success and stdout:
        gpus = stdout.strip().split('\n')
        print("✅ NVIDIA GPU(s) detected:")
        for gpu in gpus:
            parts = gpu.split(', ')
            if len(parts) >= 2:
                name, memory = parts[0], parts[1]
                print(f"   📊 {name}: {memory} MB VRAM")
        return True
    else:
        print("⚠️  No NVIDIA GPU detected or nvidia-smi not available")
        print("💡 GPU acceleration may not be available")
        return False

def check_required_model():
    """Check if the required embedding model is available"""
    print("\n🔍 Checking for nomic-embed-text model...")
    success, stdout, stderr = run_command("ollama list")
    
    if success:
        if "nomic-embed-text" in stdout:
            print("✅ nomic-embed-text model found")
            return True
        else:
            print("❌ nomic-embed-text model not found")
            print("💡 Install it with: ollama pull nomic-embed-text")
            return False
    else:
        print("⚠️  Could not check available models")
        return False

def test_embedding_performance():
    """Test embedding generation performance"""
    print("\n🔍 Testing embedding performance...")
    
    try:
        from langchain_ollama import OllamaEmbeddings
        import time
        
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # Test single embedding
        start_time = time.time()
        result = embeddings.embed_query("test embedding performance with GPU acceleration")
        single_time = time.time() - start_time
        
        if result and len(result) > 0:
            print(f"✅ Single embedding: {single_time:.3f}s")
            print(f"📊 Embedding dimensions: {len(result)}")
            
            # Performance assessment
            if single_time < 0.1:
                print("🚀 Excellent performance - GPU acceleration likely active!")
            elif single_time < 0.5:
                print("⚡ Good performance - embeddings working well")
            elif single_time < 2.0:
                print("📈 Moderate performance - consider checking GPU setup")
            else:
                print("⚠️  Slow performance - may be CPU-only mode")
            
            # Test batch processing
            print("\n🔍 Testing batch performance...")
            test_queries = [
                "SELECT * FROM customers WHERE active = true",
                "UPDATE products SET price = price * 1.1",
                "DELETE FROM orders WHERE status = 'cancelled'",
                "INSERT INTO logs (message) VALUES ('test entry')",
                "CREATE INDEX idx_customer_email ON customers(email)"
            ]
            
            start_time = time.time()
            batch_results = embeddings.embed_documents(test_queries)
            batch_time = time.time() - start_time
            
            print(f"✅ Batch embedding (5 queries): {batch_time:.3f}s")
            print(f"📊 Average per query: {batch_time/len(test_queries):.3f}s")
            
            return True
        else:
            print("❌ Embedding test failed - no results returned")
            return False
            
    except ImportError:
        print("❌ LangChain Ollama not installed")
        print("💡 Install with: pip install langchain-ollama")
        return False
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False

def set_optimal_environment():
    """Set optimal environment variables for GPU performance"""
    print("\n🔧 Setting optimal environment variables...")
    
    optimal_settings = {
        'OLLAMA_NUM_PARALLEL': '16',
        'OLLAMA_MAX_LOADED_MODELS': '3',
        'OLLAMA_MAX_QUEUE': '512'
    }
    
    for var, value in optimal_settings.items():
        os.environ[var] = value
        print(f"✅ Set {var}={value}")
    
    print("\n💡 To make these permanent, add to your shell profile:")
    for var, value in optimal_settings.items():
        if platform.system() == 'Windows':
            print(f"   setx {var} {value}")
        else:
            print(f"   export {var}={value}")

def provide_recommendations(gpu_detected, model_available, performance_good):
    """Provide optimization recommendations based on test results"""
    print("\n🎯 Recommendations for optimal performance:")
    
    if not gpu_detected:
        print("⚠️  GPU Recommendations:")
        print("   1. Install NVIDIA GPU drivers")
        print("   2. Ensure GPU is properly detected (nvidia-smi)")
        print("   3. Consider CPU-only mode with fewer workers")
    
    if not model_available:
        print("📥 Model Setup:")
        print("   1. Download model: ollama pull nomic-embed-text")
        print("   2. Verify installation: ollama list")
    
    if gpu_detected and model_available:
        if performance_good:
            print("🚀 Optimal Configuration Detected!")
            print("   Recommended settings for your system:")
            print("   python standalone_embedding_generator.py \\")
            print("     --csv 'your_data.csv' \\")
            print("     --batch-size 300 \\")
            print("     --workers 16")
        else:
            print("⚡ Performance Tuning:")
            print("   1. Check GPU memory usage during processing")
            print("   2. Start with conservative settings:")
            print("      --batch-size 150 --workers 8")
            print("   3. Gradually increase if system handles well")
    
    print("\n🔧 General Optimization:")
    print("   1. Keep Ollama server running: ollama serve")
    print("   2. Monitor GPU memory with: nvidia-smi")
    print("   3. Use higher batch sizes if you have 32GB+ RAM")

def main():
    parser = argparse.ArgumentParser(description="Setup and optimize Ollama for GPU acceleration")
    parser.add_argument('--check-only', action='store_true', help='Only check current setup, do not configure')
    args = parser.parse_args()
    
    print("🔧 Ollama GPU Setup and Optimization")
    print("=" * 50)
    
    # Run checks
    ollama_installed = check_ollama_installed()
    if not ollama_installed:
        return 1
    
    ollama_running = check_ollama_running()
    gpu_detected = check_gpu_support()
    model_available = check_required_model()
    
    if ollama_running and model_available:
        performance_good = test_embedding_performance()
    else:
        performance_good = False
    
    # Configure environment if not check-only
    if not args.check_only:
        set_optimal_environment()
    
    # Provide recommendations
    provide_recommendations(gpu_detected, model_available, performance_good)
    
    # Overall status
    print("\n" + "=" * 50)
    print("📋 Setup Status Summary:")
    print(f"   Ollama installed: {'✅' if ollama_installed else '❌'}")
    print(f"   Ollama running: {'✅' if ollama_running else '❌'}")
    print(f"   GPU detected: {'✅' if gpu_detected else '⚠️'}")
    print(f"   Model available: {'✅' if model_available else '❌'}")
    print(f"   Performance good: {'✅' if performance_good else '⚠️'}")
    
    if ollama_installed and ollama_running and model_available:
        print("\n🎉 Ready for GPU-accelerated embedding generation!")
        return 0
    else:
        print("\n⚠️  Some setup steps needed before optimal performance")
        return 1

if __name__ == "__main__":
    sys.exit(main())