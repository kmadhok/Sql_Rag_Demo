#!/usr/bin/env python3
"""
Check what mode Gemini clients are using by inspecting initialization logs.

This script:
1. Initializes GeminiClient directly
2. Initializes all LLM registry clients (parser, generator, chat)
3. Captures and displays initialization logs
4. Verifies all clients are using SDK mode

Usage:
    export GENAI_CLIENT_MODE=sdk
    export GOOGLE_CLOUD_PROJECT=your-project-id
    export GOOGLE_CLOUD_LOCATION=us-central1
    python check_sdk_logs.py
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging to capture INFO messages with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"{title:^80}")
    print("=" * 80)


def print_section(title):
    """Print a section divider."""
    print(f"\n--- {title} ---")


def check_environment():
    """Display current environment configuration."""
    print_header("ENVIRONMENT CONFIGURATION")

    env_vars = {
        "GENAI_CLIENT_MODE": os.getenv("GENAI_CLIENT_MODE", "NOT SET"),
        "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT", "NOT SET"),
        "GOOGLE_CLOUD_LOCATION": os.getenv("GOOGLE_CLOUD_LOCATION", "NOT SET"),
        "GEMINI_API_KEY": "SET" if os.getenv("GEMINI_API_KEY") else "NOT SET",
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "NOT SET"),
    }

    for var, value in env_vars.items():
        # Mask API key for security
        if var == "GEMINI_API_KEY" and value == "SET":
            print(f"  {var}: {value} (hidden)")
        else:
            print(f"  {var}: {value}")


def test_direct_client():
    """Test GeminiClient initialization directly."""
    print_header("TEST 1: DIRECT GEMINI CLIENT INITIALIZATION")

    try:
        from gemini_client import GeminiClient

        print_section("Initializing GeminiClient with model 'gemini-2.5-flash-lite'")
        client = GeminiClient(model="gemini-2.5-flash-lite")

        print("\n✅ Client initialized successfully")
        print(f"   Mode: {client.client_mode}")
        print(f"   Model: {client.model_name}")

        if client.client_mode == "sdk":
            print(f"   Project: {client.project_id}")
            print(f"   Location: {client.location}")
            print("   ✅ Using SDK mode (Vertex AI)")
        else:
            print(f"   API Key: {'SET' if client.api_key else 'NOT SET'}")
            print("   ⚠️  Using API mode (not Vertex AI)")

        return client

    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        return None


def test_llm_registry():
    """Test LLM registry clients."""
    print_header("TEST 2: LLM REGISTRY CLIENTS")

    try:
        from llm_registry import get_llm_registry

        print_section("Getting LLM Registry")
        registry = get_llm_registry()

        clients = {}

        # Parser client
        print_section("Initializing Parser Client")
        parser = registry.get_parser()
        clients['parser'] = parser
        print(f"✅ Parser: {parser.model_name} in {parser.client_mode} mode")

        # Generator client
        print_section("Initializing Generator Client")
        generator = registry.get_generator()
        clients['generator'] = generator
        print(f"✅ Generator: {generator.model_name} in {generator.client_mode} mode")

        # Chat client
        print_section("Initializing Chat Client")
        chat = registry.get_chat()
        clients['chat'] = chat
        print(f"✅ Chat: {chat.model_name} in {chat.client_mode} mode")

        # Rewriter client (optional, may not exist in all versions)
        print_section("Initializing Rewriter Client")
        try:
            rewriter = registry.get_rewriter()
            clients['rewriter'] = rewriter
            print(f"✅ Rewriter: {rewriter.model_name} in {rewriter.client_mode} mode")
        except AttributeError:
            print("ℹ️  Rewriter client not available (method doesn't exist)")

        return clients

    except Exception as e:
        print(f"\n❌ Failed to initialize LLM registry: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_all_sdk_mode(direct_client, registry_clients):
    """Verify that all clients are using SDK mode."""
    print_header("VERIFICATION SUMMARY")

    all_clients = {
        'Direct Client': direct_client,
    }

    if registry_clients:
        # Only add clients that exist
        if 'parser' in registry_clients:
            all_clients['Parser'] = registry_clients['parser']
        if 'generator' in registry_clients:
            all_clients['Generator'] = registry_clients['generator']
        if 'chat' in registry_clients:
            all_clients['Chat'] = registry_clients['chat']
        if 'rewriter' in registry_clients:
            all_clients['Rewriter'] = registry_clients['rewriter']

    sdk_count = 0
    api_count = 0
    failed_count = 0

    print("\nClient Mode Summary:")
    print("-" * 80)

    for name, client in all_clients.items():
        if client is None:
            print(f"  ❌ {name:20} : FAILED TO INITIALIZE")
            failed_count += 1
        elif client.client_mode == "sdk":
            print(f"  ✅ {name:20} : SDK mode (Vertex AI) - {client.model_name}")
            sdk_count += 1
        else:
            print(f"  ⚠️  {name:20} : API mode (NOT Vertex AI) - {client.model_name}")
            api_count += 1

    print("-" * 80)
    print(f"\nResults:")
    print(f"  SDK mode (Vertex AI): {sdk_count}")
    print(f"  API mode: {api_count}")
    print(f"  Failed: {failed_count}")

    if sdk_count > 0 and api_count == 0 and failed_count == 0:
        print("\n🎉 SUCCESS: All clients are using SDK mode (Vertex AI)!")
        return True
    elif api_count > 0:
        print("\n⚠️  WARNING: Some clients are using API mode instead of SDK mode")
        print("\nTo fix:")
        print("  1. Check GENAI_CLIENT_MODE environment variable is set to 'sdk'")
        print("  2. Restart the application to pick up new environment variables")
        return False
    else:
        print("\n❌ FAILURE: Some clients failed to initialize")
        return False


def main():
    """Run log checker."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 22 + "GEMINI SDK MODE LOG CHECKER" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")

    # Check environment
    check_environment()

    # Test direct client
    direct_client = test_direct_client()

    # Test LLM registry
    registry_clients = test_llm_registry()

    # Verify all using SDK mode
    all_sdk = verify_all_sdk_mode(direct_client, registry_clients)

    # Print additional guidance
    print_header("WHAT TO LOOK FOR IN LOGS ABOVE")
    print("""
The logs above should contain lines like:

  ✅ Gemini client initialized in Vertex SDK mode: gemini-2.5-flash-lite
     (project=your-project-id, location=us-central1)

If you see:

  ✅ Gemini client initialized in API mode: gemini-2.5-flash-lite

Then the client is NOT using Vertex AI (it's using API key authentication).

To switch to Vertex AI:
  1. export GENAI_CLIENT_MODE=sdk
  2. export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
  3. export GOOGLE_CLOUD_LOCATION=us-central1
  4. gcloud auth application-default login
  5. Restart your application
    """)

    print_header("NEXT STEPS")
    print("""
1. If all clients show SDK mode:
   ✅ Run the Streamlit app: streamlit run app_simple_gemini.py
   ✅ Run integration tests: pytest tests/integration/ -v

2. If some clients show API mode:
   ⚠️  Check your .env file has GENAI_CLIENT_MODE=sdk
   ⚠️  Restart your terminal/IDE to pick up new environment variables
   ⚠️  Run this script again to verify

3. If clients failed to initialize:
   ❌ Check that you've authenticated: gcloud auth application-default login
   ❌ Check GOOGLE_CLOUD_PROJECT is set correctly
   ❌ Ensure Vertex AI API is enabled in your GCP project
    """)

    sys.exit(0 if all_sdk else 1)


if __name__ == "__main__":
    main()
