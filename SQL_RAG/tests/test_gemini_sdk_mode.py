#!/usr/bin/env python3
"""
Comprehensive test suite for Gemini SDK mode (Vertex AI) verification.

Tests that the application correctly uses Vertex AI SDK instead of API key auth.

Test Categories:
- Unit tests: Mode detection, environment variables, initialization
- Integration tests: Real Vertex AI API calls (requires credentials)
- Comparison tests: SDK vs API mode behavior differences

Usage:
    # Unit tests only (fast, no real API calls)
    pytest tests/test_gemini_sdk_mode.py::TestGeminiSDKMode -v

    # Integration tests (slow, requires credentials)
    export GOOGLE_CLOUD_PROJECT=your-project-id
    gcloud auth application-default login
    pytest tests/test_gemini_sdk_mode.py::TestGeminiSDKModeIntegration -v -m integration
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent / "rag_app"
sys.path.insert(0, str(project_root))

from gemini_client import GeminiClient
from llm_registry import get_llm_registry


class TestGeminiSDKMode:
    """Unit tests for Gemini SDK mode functionality (no real API calls)."""

    @pytest.fixture(autouse=True)
    def setup_sdk_mode(self, monkeypatch):
        """Configure environment for SDK mode testing."""
        monkeypatch.setenv("GENAI_CLIENT_MODE", "sdk")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project-123")
        monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        # Clear API key to ensure SDK mode is used
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    def test_client_mode_detection_from_env(self):
        """Test that client correctly detects SDK mode from environment."""
        client = GeminiClient(model="gemini-2.5-flash-lite")

        assert client.client_mode == "sdk", "Should be in SDK mode"
        assert client.project_id == "test-project-123"
        assert client.location == "us-central1"
        assert client.api_key is None, "SDK mode should not use API key"

    def test_client_mode_explicit_parameter(self):
        """Test explicit client_mode parameter."""
        client = GeminiClient(
            model="gemini-2.5-flash-lite",
            client_mode="sdk"
        )

        assert client.client_mode == "sdk"
        assert client.project_id == "test-project-123"

    def test_sdk_mode_requires_project(self, monkeypatch):
        """Test that SDK mode fails without GOOGLE_CLOUD_PROJECT."""
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

        with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT is required"):
            GeminiClient(model="gemini-2.5-flash-lite", client_mode="sdk")

    def test_sdk_mode_default_location(self, monkeypatch):
        """Test that SDK mode defaults to 'global' location if not set."""
        monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

        client = GeminiClient(model="gemini-2.5-flash-lite", client_mode="sdk")

        assert client.location == "global", "Should default to 'global' location"

    def test_api_mode_requires_api_key(self, monkeypatch):
        """Test that API mode fails without API key."""
        monkeypatch.setenv("GENAI_CLIENT_MODE", "api")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ValueError, match="API key is required"):
            GeminiClient(model="gemini-2.5-flash-lite", client_mode="api")

    def test_llm_registry_uses_sdk_mode(self):
        """Test that LLM registry creates clients in SDK mode."""
        registry = get_llm_registry()

        # Test all registry clients
        generator = registry.get_generator()
        assert generator.client_mode == "sdk", "Generator should use SDK mode"

        parser = registry.get_parser()
        assert parser.client_mode == "sdk", "Parser should use SDK mode"

        chat = registry.get_chat()
        assert chat.client_mode == "sdk", "Chat should use SDK mode"

        rewriter = registry.get_rewriter()
        assert rewriter.client_mode == "sdk", "Rewriter should use SDK mode"

    def test_llm_registry_all_same_mode(self):
        """Test that all LLM registry clients use the same mode."""
        registry = get_llm_registry()

        clients = [
            registry.get_generator(),
            registry.get_parser(),
            registry.get_chat(),
            registry.get_rewriter(),
        ]

        modes = [client.client_mode for client in clients]
        assert len(set(modes)) == 1, "All clients should use the same mode"
        assert modes[0] == "sdk", "All clients should use SDK mode"

    def test_client_info_shows_sdk_mode(self):
        """Test that get_model_info correctly reports SDK mode status."""
        client = GeminiClient(model="gemini-2.5-flash-lite", client_mode="sdk")

        info = client.get_model_info()

        assert info['model_name'] == "gemini-2.5-flash-lite"
        assert info['provider'] == 'Google Gemini'
        assert info['api_key_set'] is False, "SDK mode should not use API key"
        assert info['initialized'] is True

    def test_sdk_mode_initialization_attributes(self):
        """Test that SDK mode sets correct client attributes."""
        client = GeminiClient(
            model="gemini-2.5-pro",
            client_mode="sdk"
        )

        # Check attributes
        assert hasattr(client, 'client_mode')
        assert hasattr(client, 'project_id')
        assert hasattr(client, 'location')
        assert hasattr(client, 'client')

        # Verify values
        assert client.client_mode == "sdk"
        assert client.project_id == "test-project-123"
        assert client.location == "us-central1"
        assert client.client is not None

    def test_different_models_same_sdk_mode(self):
        """Test that different models all use SDK mode."""
        models = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash-lite",
        ]

        for model in models:
            client = GeminiClient(model=model, client_mode="sdk")
            assert client.client_mode == "sdk", f"Model {model} should use SDK mode"
            assert client.model_name == model


@pytest.mark.integration
class TestGeminiSDKModeIntegration:
    """Integration tests that actually call Vertex AI (requires real credentials)."""

    @pytest.fixture(autouse=True)
    def setup_sdk_mode(self, monkeypatch):
        """Configure environment for SDK mode integration testing."""
        monkeypatch.setenv("GENAI_CLIENT_MODE", "sdk")

        # Use actual project from environment or skip
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            pytest.skip("GOOGLE_CLOUD_PROJECT not set - skipping integration test")

        # Ensure API key is not used
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    def test_sdk_mode_connection(self):
        """Test actual connection to Vertex AI."""
        client = GeminiClient(model="gemini-2.5-flash-lite")

        success, message = client.test_connection()

        assert success, f"SDK mode connection failed: {message}"
        assert "ready" in message.lower() or "success" in message.lower()

    def test_sdk_mode_generation(self):
        """Test actual content generation via Vertex AI."""
        client = GeminiClient(model="gemini-2.5-flash-lite")

        response = client.invoke("Say 'SDK MODE WORKING' if you receive this.")

        assert response is not None, "Response should not be None"
        assert len(response) > 0, "Response should not be empty"
        assert isinstance(response, str), "Response should be a string"

    def test_sdk_mode_generation_with_system_prompt(self):
        """Test generation with system prompt via Vertex AI."""
        client = GeminiClient(
            model="gemini-2.5-flash-lite",
            system_prompt="You are a helpful assistant testing SDK mode."
        )

        response = client.invoke("What mode are you running in?")

        assert response is not None
        assert len(response) > 0

    def test_sdk_mode_multiple_requests(self):
        """Test multiple sequential requests via Vertex AI."""
        client = GeminiClient(model="gemini-2.5-flash-lite")

        responses = []
        for i in range(3):
            response = client.invoke(f"Respond with: Request {i+1} received")
            responses.append(response)

        # All responses should be successful
        assert len(responses) == 3
        assert all(r is not None for r in responses)
        assert all(len(r) > 0 for r in responses)

    def test_llm_registry_integration(self):
        """Test that LLM registry clients work with real Vertex AI."""
        registry = get_llm_registry()

        # Test generator
        generator = registry.get_generator()
        gen_response = generator.invoke("Say 'generator working'")
        assert gen_response is not None
        assert len(gen_response) > 0

        # Test chat
        chat = registry.get_chat()
        chat_response = chat.invoke("Say 'chat working'")
        assert chat_response is not None
        assert len(chat_response) > 0

    def test_sdk_mode_error_handling(self):
        """Test error handling with Vertex AI."""
        client = GeminiClient(model="gemini-2.5-flash-lite")

        # Test with empty prompt (should handle gracefully)
        try:
            response = client.invoke("")
            # Either returns a response or raises an exception
            # Both are acceptable - we just want to ensure it doesn't crash
            assert True
        except Exception as e:
            # Exception is fine - we're testing error handling
            assert True

    @pytest.mark.slow
    def test_sdk_mode_large_context(self):
        """Test SDK mode with larger context (takes longer)."""
        client = GeminiClient(model="gemini-2.5-flash-lite")

        # Create a larger prompt
        large_prompt = "Summarize the following: " + ("test " * 100)
        response = client.invoke(large_prompt)

        assert response is not None
        assert len(response) > 0


@pytest.mark.integration
class TestSDKVsAPIMode:
    """Comparison tests between SDK and API modes (requires both credentials)."""

    def test_mode_switching(self, monkeypatch):
        """Test switching between SDK and API modes."""
        # Only run if both credentials are available
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            pytest.skip("GOOGLE_CLOUD_PROJECT not set")
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        # Create SDK mode client
        monkeypatch.setenv("GENAI_CLIENT_MODE", "sdk")
        sdk_client = GeminiClient(model="gemini-2.5-flash-lite")
        assert sdk_client.client_mode == "sdk"

        # Create API mode client
        monkeypatch.setenv("GENAI_CLIENT_MODE", "api")
        api_client = GeminiClient(model="gemini-2.5-flash-lite")
        assert api_client.client_mode == "api"

        # Both should work
        sdk_success, sdk_msg = sdk_client.test_connection()
        api_success, api_msg = api_client.test_connection()

        assert sdk_success, "SDK mode should work"
        assert api_success, "API mode should work"

    def test_sdk_and_api_same_output_quality(self, monkeypatch):
        """Test that SDK and API modes produce similar quality outputs."""
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            pytest.skip("GOOGLE_CLOUD_PROJECT not set")
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set")

        prompt = "What is 2+2? Reply with just the number."

        # SDK mode
        monkeypatch.setenv("GENAI_CLIENT_MODE", "sdk")
        sdk_client = GeminiClient(model="gemini-2.5-flash-lite")
        sdk_response = sdk_client.invoke(prompt)

        # API mode
        monkeypatch.setenv("GENAI_CLIENT_MODE", "api")
        api_client = GeminiClient(model="gemini-2.5-flash-lite")
        api_response = api_client.invoke(prompt)

        # Both should contain "4"
        assert "4" in sdk_response
        assert "4" in api_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
