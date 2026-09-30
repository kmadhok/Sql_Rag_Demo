#!/usr/bin/env python3
"""
Unit tests for the OpenRouter LLM + embeddings provider (no network calls).

Requirements covered:
- LLM_PROVIDER selects the client; gemini stays the default; unknown providers fail loudly
- Bare Gemini model names map to OpenRouter "google/<name>" slugs; full slugs pass through
- OpenRouterClient: key required, text returned, retries on empty/transient failures,
  structured output translated for Pydantic / dict / no schema, test_connection reports errors
- EMBEDDINGS_PROVIDER=openrouter targets OpenRouter and sends raw text; missing key fails
- scripts/reembed_index.py preserves every document when rebuilding an index

Usage:
    pytest tests/test_openrouter_provider.py -v
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

project_root = Path(__file__).parent.parent / "rag_app"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))

import llm_registry  # noqa: E402
import openrouter_client  # noqa: E402
from openrouter_client import OpenRouterClient, _to_response_format  # noqa: E402


def _reply(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def _fake_openai(*replies):
    client = MagicMock()
    client.chat.completions.create.side_effect = list(replies)
    return client


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("LLM_PROVIDER", "OPENROUTER_API_KEY", "EMBEDDINGS_PROVIDER", "OPENROUTER_EMBEDDING_MODEL"):
        monkeypatch.delenv(var, raising=False)
    # Never pick up a developer's real key from a local .env file.
    monkeypatch.setattr(openrouter_client, "get_openrouter_api_key", lambda: __import__("os").getenv("OPENROUTER_API_KEY"))


# --- Provider selection -------------------------------------------------------

class TestProviderSelection:
    def test_default_provider_is_gemini(self, monkeypatch):
        created = {}
        fake_module = SimpleNamespace(GeminiClient=lambda model: created.setdefault("model", model))
        monkeypatch.setitem(sys.modules, "gemini_client", fake_module)
        llm_registry.make_llm_client("gemini-2.5-pro")
        assert created["model"] == "gemini-2.5-pro"

    def test_openrouter_provider_returns_openrouter_client(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        client = llm_registry.make_llm_client("gemini-2.5-pro")
        assert isinstance(client, OpenRouterClient)
        assert client.model_name == "google/gemini-2.5-pro"

    def test_provider_value_is_case_and_space_insensitive(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "  OpenRouter ")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        assert isinstance(llm_registry.make_llm_client("x/y"), OpenRouterClient)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "bogus")
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            llm_registry.make_llm_client("gemini-2.5-pro")

    def test_registry_roles_use_configured_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        monkeypatch.setenv("LLM_GEN_MODEL", "anthropic/claude-sonnet-5")
        registry = llm_registry.LLMRegistry()
        assert registry.get_generator().model_name == "anthropic/claude-sonnet-5"
        assert registry.get_chat().model_name == "google/gemini-2.5-flash-lite"
        assert registry.info()["provider"] == "openrouter"


class TestModelNameResolution:
    @pytest.mark.parametrize("name,expected", [
        ("gemini-2.5-pro", "google/gemini-2.5-pro"),
        ("gemini-2.5-flash-lite", "google/gemini-2.5-flash-lite"),
        ("anthropic/claude-sonnet-5", "anthropic/claude-sonnet-5"),
        ("openai/gpt-5-mini", "openai/gpt-5-mini"),
    ])
    def test_openrouter_mapping(self, name, expected):
        assert llm_registry.resolve_model_name(name, "openrouter") == expected

    def test_gemini_provider_leaves_names_untouched(self):
        assert llm_registry.resolve_model_name("gemini-2.5-pro", "gemini") == "gemini-2.5-pro"


# --- OpenRouterClient ---------------------------------------------------------

class TestOpenRouterClient:
    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            OpenRouterClient(model="google/gemini-2.5-pro")

    def test_invoke_returns_stripped_text_and_sends_prompt(self):
        fake = _fake_openai(_reply("  SELECT 1  "))
        client = OpenRouterClient(model="m/x", client=fake)
        assert client.invoke("hi") == "SELECT 1"
        kwargs = fake.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "m/x"
        assert kwargs["messages"] == [{"role": "user", "content": "hi"}]

    def test_retries_on_empty_then_succeeds(self):
        fake = _fake_openai(_reply(""), _reply("ok"))
        client = OpenRouterClient(model="m/x", client=fake, retry_delay=0)
        assert client.invoke("hi") == "ok"
        assert fake.chat.completions.create.call_count == 2

    def test_retries_on_transient_error_then_succeeds(self):
        fake = _fake_openai(ConnectionError("reset"), _reply("ok"))
        client = OpenRouterClient(model="m/x", client=fake, retry_delay=0)
        assert client.invoke("hi") == "ok"

    def test_raises_after_exhausting_retries(self):
        fake = _fake_openai(*[RuntimeError("401 invalid key")] * 3)
        client = OpenRouterClient(model="m/x", client=fake, max_retries=2, retry_delay=0)
        with pytest.raises(RuntimeError, match="invalid key"):
            client.invoke("hi")
        assert fake.chat.completions.create.call_count == 3

    def test_no_choices_counts_as_empty(self):
        fake = _fake_openai(SimpleNamespace(choices=[]))
        client = OpenRouterClient(model="m/x", client=fake, max_retries=0)
        with pytest.raises(ValueError, match="Empty response"):
            client.invoke("hi")

    def test_invoke_structured_passes_json_schema(self):
        class Tables(BaseModel):
            tables: list[str]

        fake = _fake_openai(_reply('{"tables": ["orders"]}'))
        client = OpenRouterClient(model="m/x", client=fake)
        assert client.invoke_structured("p", response_schema=Tables) == '{"tables": ["orders"]}'
        fmt = fake.chat.completions.create.call_args.kwargs["response_format"]
        assert fmt["type"] == "json_schema"
        assert fmt["json_schema"]["name"] == "Tables"
        assert "tables" in fmt["json_schema"]["schema"]["properties"]

    def test_invoke_structured_non_json_format_is_plain(self):
        fake = _fake_openai(_reply("text"))
        OpenRouterClient(model="m/x", client=fake).invoke_structured("p", response_format="text")
        assert "response_format" not in fake.chat.completions.create.call_args.kwargs

    def test_test_connection_reports_failure_without_raising(self):
        fake = _fake_openai(RuntimeError("boom"))
        ok, message = OpenRouterClient(model="m/x", client=fake, max_retries=0).test_connection()
        assert ok is False and "boom" in message

    def test_test_connection_success(self):
        ok, message = OpenRouterClient(model="m/x", client=_fake_openai(_reply("ok"))).test_connection()
        assert ok is True and "m/x" in message

    def test_model_info_reports_provider(self):
        info = OpenRouterClient(model="m/x", client=_fake_openai()).get_model_info()
        assert info["provider"] == "OpenRouter" and info["model_name"] == "m/x"


class TestResponseFormat:
    def test_dict_schema(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}}
        fmt = _to_response_format(schema)
        assert fmt["json_schema"]["schema"] == schema

    def test_no_schema_uses_json_object(self):
        assert _to_response_format(None) == {"type": "json_object"}

    def test_unrecognised_schema_falls_back_to_json_object(self):
        assert _to_response_format("not-a-schema") == {"type": "json_object"}


# --- Embeddings ---------------------------------------------------------------

class TestOpenRouterEmbeddings:
    def test_openrouter_embeddings_configuration(self, monkeypatch):
        monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        from utils.embedding_provider import DEFAULT_OPENROUTER_EMBEDDING_MODEL, get_embedding_function
        emb = get_embedding_function()
        assert emb.model == DEFAULT_OPENROUTER_EMBEDDING_MODEL
        assert emb.openai_api_base == "https://openrouter.ai/api/v1"
        assert emb.check_embedding_ctx_length is False

    def test_embedding_model_override(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        monkeypatch.setenv("OPENROUTER_EMBEDDING_MODEL", "google/gemini-embedding-001")
        from utils.embedding_provider import get_embedding_function
        assert get_embedding_function("openrouter").model == "google/gemini-embedding-001"

    def test_missing_key_raises(self):
        from utils.embedding_provider import get_embedding_function
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            get_embedding_function("openrouter")

    def test_unknown_provider_lists_openrouter(self):
        from utils.embedding_provider import get_embedding_function
        with pytest.raises(RuntimeError, match="openrouter"):
            get_embedding_function("nope")


# --- Index re-embedding -------------------------------------------------------

class TestReembedIndex:
    def test_load_documents_roundtrip(self, tmp_path):
        from langchain_community.embeddings import FakeEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        import reembed_index

        docs = [Document(page_content=f"SELECT {i}", metadata={"id": i}) for i in range(5)]
        FAISS.from_documents(docs, FakeEmbeddings(size=8)).save_local(str(tmp_path / "src"))

        loaded = reembed_index.load_documents(tmp_path / "src")
        assert sorted(d.page_content for d in loaded) == [f"SELECT {i}" for i in range(5)]
        assert sorted(d.metadata["id"] for d in loaded) == list(range(5))
