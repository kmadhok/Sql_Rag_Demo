#!/usr/bin/env python3
"""
LLM Registry

Centralizes model selection per pipeline role so the app can choose
different Gemini models for parsing, generation, rewriting, and chat.

Environment variables (all optional):
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
"""

import os
from typing import Optional

from gemini_client import GeminiClient


class LLMRegistry:
    def __init__(self):
        # Defaults honor the request: Pro for generation; flash-lite for everything else
        self.parse_model = os.getenv("LLM_PARSE_MODEL", "gemini-2.5-flash-lite")
        self.gen_model = os.getenv("LLM_GEN_MODEL", "gemini-2.5-pro")
        self.rewrite_model = os.getenv("LLM_REWRITE_MODEL", self.parse_model)
        self.chat_model = os.getenv("LLM_CHAT_MODEL", "gemini-2.5-flash-lite")

    # --- Clients ---
    def get_parser(self) -> GeminiClient:
        return GeminiClient(model=self.parse_model)

    def get_generator(self) -> GeminiClient:
        return GeminiClient(model=self.gen_model)

    def get_chat(self) -> GeminiClient:
        return GeminiClient(model=self.chat_model)

    # --- Introspection ---
    def info(self) -> dict:
        return {
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

