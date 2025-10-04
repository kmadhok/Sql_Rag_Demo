#!/usr/bin/env python3
"""
Embedding provider factory.

Allows switching between local Ollama embeddings and OpenAI embeddings
via environment variables without touching call sites.

Configuration (env vars):
- EMBEDDINGS_PROVIDER: "ollama" (default) or "openai"
- OLLAMA_EMBEDDING_MODEL: defaults to "nomic-embed-text"
- OPENAI_EMBEDDING_MODEL: defaults to "text-embedding-3-small"
- OPENAI_API_KEY: required when EMBEDDINGS_PROVIDER=openai
"""

import os
from typing import Any


def get_embedding_function(
    provider: str | None = None,
    model: str | None = None,
) -> Any:
    """Return a LangChain-compatible embedding function based on configuration.

    Args:
        provider: "ollama" or "openai". Defaults to env EMBEDDINGS_PROVIDER or "ollama".
        model: Optional explicit model override.

    Returns:
        An embeddings object implementing LangChain's Embeddings interface.

    Raises:
        RuntimeError: if required packages or API keys are missing.
    """
    selected = (provider or os.getenv("EMBEDDINGS_PROVIDER", "ollama")).lower()

    if selected == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "langchain-openai is not installed. Add 'langchain-openai' to requirements.txt"
            ) from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Export it or add it to your .env when using OpenAI embeddings."
            )

        model_name = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        # OpenAIEmbeddings reads key from env automatically; passing explicitly is fine too
        return OpenAIEmbeddings(model=model_name, api_key=api_key)

    # Default to Ollama
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "langchain-ollama is not installed. Add 'langchain-ollama' to requirements.txt"
        ) from e

    model_name = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    return OllamaEmbeddings(model=model_name)

