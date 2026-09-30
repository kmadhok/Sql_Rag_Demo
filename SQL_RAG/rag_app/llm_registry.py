#!/usr/bin/env python3
"""
LLM Registry

Centralizes model selection per pipeline role so the app can choose
different models for parsing, generation, rewriting, and chat.

Environment variables (all optional):
- LLM_PROVIDER      -> "gemini" (default) or "openrouter"
- LLM_PARSE_MODEL   -> model used for parsing/structured extraction
- LLM_GEN_MODEL     -> model used for SQL generation
- LLM_REWRITE_MODEL -> model used for query rewriting
- LLM_CHAT_MODEL    -> model used for chat responses

Defaults:
- Parse/Rewrite/Chat: gemini-2.5-flash-lite
- Generation:         gemini-2.5-pro

Example:
  export LLM_GEN_MODEL="gemini-2.5-pro"
  export LLM_PARSE_MODEL="gemini-2.5-flash-lite"
  export LLM_REWRITE_MODEL="gemini-2.5-flash-lite"
  export LLM_CHAT_MODEL="gemini-2.5-flash-lite"

With LLM_PROVIDER=openrouter, model names are OpenRouter slugs
("anthropic/claude-sonnet-5"); bare Gemini names ("gemini-2.5-pro")
are mapped to "google/<name>" so the defaults keep working.
"""

import os
from typing import Any, Optional


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").strip().lower()


def resolve_model_name(model: str, provider: Optional[str] = None) -> str:
    provider = provider or get_llm_provider()
    if provider == "openrouter" and "/" not in model:
        return f"google/{model}"
    return model


def make_llm_client(model: str) -> Any:
    """Create an LLM client for the configured provider. Every client exposes
    invoke(), invoke_structured(), test_connection() and model_name."""
    provider = get_llm_provider()
    if provider == "openrouter":
        from openrouter_client import OpenRouterClient
        return OpenRouterClient(model=resolve_model_name(model, provider))
    if provider == "gemini":
        from gemini_client import GeminiClient
        return GeminiClient(model=model)
    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'gemini' or 'openrouter'.")


class LLMRegistry:
    def __init__(self):
        # Defaults honor the request: Pro for generation; flash-lite for everything else
        self.parse_model = os.getenv("LLM_PARSE_MODEL", "gemini-2.5-flash-lite")
        self.gen_model = os.getenv("LLM_GEN_MODEL", "gemini-2.5-pro")
        self.rewrite_model = os.getenv("LLM_REWRITE_MODEL", self.parse_model)
        self.chat_model = os.getenv("LLM_CHAT_MODEL", "gemini-2.5-flash-lite")

    # --- Clients ---
    def get_parser(self) -> Any:
        return make_llm_client(self.parse_model)

    def get_generator(self) -> Any:
        return make_llm_client(self.gen_model)

    def get_chat(self) -> Any:
        return make_llm_client(self.chat_model)

    # --- Introspection ---
    def info(self) -> dict:
        return {
            "provider": get_llm_provider(),
            "parse_model": self.parse_model,
            "gen_model": self.gen_model,
            "rewrite_model": self.rewrite_model,
            "chat_model": self.chat_model,
        }


# Singleton accessor
_registry: Optional[LLMRegistry] = None


def get_llm_registry() -> LLMRegistry:
    global _registry
    if _registry is None:
        _registry = LLMRegistry()
    return _registry

