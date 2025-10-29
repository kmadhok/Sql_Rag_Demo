#!/usr/bin/env python3
"""
Debug script to check environment variables
"""

import os
from pathlib import Path

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env with dotenv")
except ImportError:
    print("⚠️ dotenv not available")

print("🔍 Environment Variable Debug")
print("=" * 40)

# Check current directory and .env file
current_dir = Path.cwd()
print(f"Current directory: {current_dir}")

env_path = Path(__file__).parent / ".env"
print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

print("\n🔑 Environment Variables:")
print(f"GEMINI_API_KEY exists: {'YES' if os.getenv('GEMINI_API_KEY') else 'NO'}")
print(f"BIGQUERY_PROJECT_ID: {os.getenv('BIGQUERY_PROJECT_ID', 'NOT_SET')}")

gemini_key = os.getenv('GEMINI_API_KEY', '')
if gemini_key and len(gemini_key) > 10:
    print(f"GEMINI_API_KEY (masked): {gemini_key[:10]}...")
else:
    print(f"GEMINI_API_KEY: {gemini_key or 'NOT_SET'}")

# Check if it's a demo key
if gemini_key in ['demo-key', 'your_actual_gemini_api_key_here', '']:
    print("⚠️ Gemini API key appears to be a demo/not set")
else:
    print("✅ Gemini API key appears to be real")