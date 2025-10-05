#!/usr/bin/env python3
"""
Embedding provider factory.

Allows switching between embedding backends via environment variables without
touching call sites.

Supported providers (env `EMBEDDINGS_PROVIDER`):
- "ollama" (default) → local Ollama server
- "openai"           → OpenAI embeddings API
- "huggingface"      → Local Hugging Face (sentence-transformers) model path or model id

Configuration (env vars):
- EMBEDDINGS_PROVIDER: "ollama" | "openai" | "huggingface"

Ollama:
- OLLAMA_EMBEDDING_MODEL: defaults to "nomic-embed-text"
- OLLAMA_BASE_URL: e.g. "http://localhost:11434" or "http://ollama:11434"

OpenAI:
- OPENAI_EMBEDDING_MODEL: defaults to "text-embedding-3-small"
- OPENAI_API_KEY: required when EMBEDDINGS_PROVIDER=openai

Hugging Face (local/offline):
- HF_EMBEDDING_MODEL: model id or local path (e.g. "/models/bge-small-en-v1.5")
- HF_EMBEDDING_DEVICE: "cpu" (default) or "cuda:0"
- HF_CACHE_DIR: optional cache directory (e.g. "/models/cache")
- TRANSFORMERS_OFFLINE / HF_HUB_OFFLINE: set to "1" to force offline mode
"""

import os
from typing import Any
import os


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

    if selected == "huggingface":
        # Local/offline Hugging Face embeddings (sentence-transformers)
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "langchain-community is missing HuggingFaceEmbeddings. Add 'sentence-transformers' to requirements.txt"
            ) from e

        model_name = model or os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        device = os.getenv("HF_EMBEDDING_DEVICE", "cpu")
        cache_dir = os.getenv("HF_CACHE_DIR")

        # HuggingFaceEmbeddings accepts model_name (id or local path), device via model_kwargs,
        # and optional cache_folder for offline setups.
        model_kwargs = {"device": device}
        kwargs = {"model_name": model_name, "model_kwargs": model_kwargs}
        if cache_dir:
            kwargs["cache_folder"] = cache_dir
        return HuggingFaceEmbeddings(**kwargs)

    # Default to Ollama
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "langchain-ollama is not installed. Add 'langchain-ollama' to requirements.txt"
        ) from e

    model_name = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    base_url = os.getenv("OLLAMA_BASE_URL")
    if base_url:
        return OllamaEmbeddings(model=model_name, base_url=base_url)
    return OllamaEmbeddings(model=model_name)
