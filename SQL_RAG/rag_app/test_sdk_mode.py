#!/usr/bin/env python3
"""
Quick test to verify Gemini SDK mode (Vertex AI) initialization.

This script tests that:
1. GeminiClient correctly initializes in SDK mode
2. Connection to Vertex AI works
3. Content generation via Vertex AI works

Usage:
    export GENAI_CLIENT_MODE=sdk
    export GOOGLE_CLOUD_PROJECT=your-project-id
    export GOOGLE_CLOUD_LOCATION=us-central1
    python test_sdk_mode.py
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging to see initialization messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)


def check_environment():
    """Check that required environment variables are set."""
    print("\n" + "=" * 80)
    print("ENVIRONMENT CONFIGURATION CHECK")
    print("=" * 80)

    required_vars = {
        "GENAI_CLIENT_MODE": os.getenv("GENAI_CLIENT_MODE"),
        "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "GOOGLE_CLOUD_LOCATION": os.getenv("GOOGLE_CLOUD_LOCATION"),
    }

    optional_vars = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    }

    all_ok = True

    print("\nRequired for SDK mode:")
    for var, value in required_vars.items():
        if value:
            # Mask sensitive values
            display_value = value if var != "GEMINI_API_KEY" else f"{value[:10]}..."
            print(f"  ✅ {var} = {display_value}")
        else:
            print(f"  ❌ {var} = NOT SET")
            all_ok = False

    print("\nOptional:")
    for var, value in optional_vars.items():
        if value:
            # Mask sensitive values
            if var == "GEMINI_API_KEY":
                display_value = f"{value[:10]}..." if len(value) > 10 else "***"
            elif var == "GOOGLE_APPLICATION_CREDENTIALS":
                display_value = value
            else:
                display_value = value
            print(f"  ℹ️  {var} = {display_value}")
        else:
            print(f"  ℹ️  {var} = NOT SET")

    if not all_ok:
        print("\n❌ MISSING REQUIRED ENVIRONMENT VARIABLES")
        print("\nTo fix, run:")
        print("  export GENAI_CLIENT_MODE=sdk")
        print("  export GOOGLE_CLOUD_PROJECT=your-gcp-project-id")
        print("  export GOOGLE_CLOUD_LOCATION=us-central1")
        print("\nAnd authenticate:")
        print("  gcloud auth application-default login")
        return False

    return True


def test_client_initialization():
    """Test that GeminiClient initializes in SDK mode."""
    print("\n" + "=" * 80)
    print("TEST 1: GEMINI CLIENT INITIALIZATION")
    print("=" * 80)

    try:
        from gemini_client import GeminiClient

        print("\nInitializing GeminiClient in SDK mode...")
        client = GeminiClient(
            model="gemini-2.5-flash-lite",
            client_mode="sdk"
        )

        print(f"\n✅ Client initialized successfully!")
        print(f"   Client mode: {client.client_mode}")
        print(f"   Project ID: {client.project_id}")
        print(f"   Location: {client.location}")
        print(f"   Model: {client.model_name}")

        # Check that API key is NOT being used
        if client.api_key:
            print(f"\n⚠️  WARNING: API key is set but shouldn't be used in SDK mode")
            print(f"   API key: {client.api_key[:10]}...")
        else:
            print(f"   API key: None (correct for SDK mode)")

        return client

    except Exception as e:
        print(f"\n❌ INITIALIZATION FAILED")
        print(f"   Error: {e}")
        print(f"\nTroubleshooting:")
        print("  1. Ensure GOOGLE_CLOUD_PROJECT is set correctly")
        print("  2. Run: gcloud auth application-default login")
        print("  3. Ensure you have Vertex AI API enabled in your GCP project")
        return None


def test_connection(client):
    """Test connection to Vertex AI."""
    print("\n" + "=" * 80)
    print("TEST 2: VERTEX AI CONNECTION")
    print("=" * 80)

    try:
        print("\nTesting connection to Vertex AI...")
        success, message = client.test_connection()

        if success:
            print(f"\n✅ CONNECTION SUCCESSFUL")
            print(f"   {message}")
            return True
        else:
            print(f"\n❌ CONNECTION FAILED")
            print(f"   {message}")
            return False

    except Exception as e:
        print(f"\n❌ CONNECTION TEST FAILED")
        print(f"   Error: {e}")
        print(f"\nTroubleshooting:")
        print("  1. Check your internet connection")
        print("  2. Verify GCP project has Vertex AI API enabled")
        print("  3. Run: gcloud auth application-default login")
        return False


def test_generation(client):
    """Test content generation via Vertex AI."""
    print("\n" + "=" * 80)
    print("TEST 3: CONTENT GENERATION VIA VERTEX AI")
    print("=" * 80)

    try:
        print("\nSending test prompt to Vertex AI...")
        print('Prompt: "Respond with exactly: SDK MODE WORKING"')

        response = client.invoke('Respond with exactly: "SDK MODE WORKING"')

        if response and len(response) > 0:
            print(f"\n✅ GENERATION SUCCESSFUL")
            print(f"   Response: {response}")

            # Check if response indicates success
            if "SDK MODE WORKING" in response.upper():
                print(f"\n🎉 SDK MODE IS VERIFIED WORKING!")
                return True
            else:
                print(f"\n✅ Response received, but different than expected")
                return True
        else:
            print(f"\n❌ GENERATION FAILED")
            print(f"   No response received")
            return False

    except Exception as e:
        print(f"\n❌ GENERATION TEST FAILED")
        print(f"   Error: {e}")
        print(f"\nPossible causes:")
        print("  1. Invalid credentials")
        print("  2. Vertex AI API not enabled")
        print("  3. Model not available in your region")
        print("  4. Quota exceeded")
        return False


def test_model_info(client):
    """Test getting model information."""
    print("\n" + "=" * 80)
    print("TEST 4: MODEL INFORMATION")
    print("=" * 80)

    try:
        print("\nRetrieving model information...")
        info = client.get_model_info()

        print(f"\n✅ MODEL INFO RETRIEVED")
        print(f"   Model name: {info.get('model_name')}")
        print(f"   Provider: {info.get('provider')}")
        print(f"   API key set: {info.get('api_key_set')}")
        print(f"   Initialized: {info.get('initialized')}")

        # Verify API key is NOT set for SDK mode
        if not info.get('api_key_set'):
            print(f"\n✅ Correctly using SDK auth (no API key)")
            return True
        else:
            print(f"\n⚠️  WARNING: API key is set (should not be used in SDK mode)")
            return False

    except Exception as e:
        print(f"\n❌ FAILED TO GET MODEL INFO")
        print(f"   Error: {e}")
        return False


def main():
    """Run all SDK mode verification tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "GEMINI SDK MODE VERIFICATION TEST" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    # Check environment
    if not check_environment():
        print("\n" + "=" * 80)
        print("RESULT: ENVIRONMENT NOT CONFIGURED CORRECTLY")
        print("=" * 80)
        sys.exit(1)

    # Test client initialization
    client = test_client_initialization()
    if not client:
        print("\n" + "=" * 80)
        print("RESULT: FAILED - CLIENT INITIALIZATION FAILED")
        print("=" * 80)
        sys.exit(1)

    # Test connection
    if not test_connection(client):
        print("\n" + "=" * 80)
        print("RESULT: FAILED - CONNECTION FAILED")
        print("=" * 80)
        sys.exit(1)

    # Test generation
    generation_ok = test_generation(client)

    # Test model info
    info_ok = test_model_info(client)

    # Final result
    print("\n" + "=" * 80)
    if generation_ok and info_ok:
        print("RESULT: ✅ ALL TESTS PASSED - SDK MODE IS WORKING CORRECTLY!")
    elif generation_ok:
        print("RESULT: ✅ MOSTLY WORKING - Generation successful but some warnings")
    else:
        print("RESULT: ❌ TESTS FAILED - See errors above")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Run Streamlit app and check console logs")
    print("  2. Run: python check_sdk_logs.py")
    print("  3. Run integration tests: pytest tests/integration/ -v")
    print()

    sys.exit(0 if (generation_ok and info_ok) else 1)


if __name__ == "__main__":
    main()
