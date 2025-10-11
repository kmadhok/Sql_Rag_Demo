#!/usr/bin/env python3
"""
Embedding provider factory for SQL RAG application.

Provides a unified interface for different embedding providers with
optimized configuration for both local development and cloud deployment.

Supports:
- OpenAI embeddings (production-ready, cloud-optimized)
- Ollama embeddings (local development, legacy support)

Configuration (environment variables):
- EMBEDDINGS_PROVIDER: "openai" (default, recommended for Cloud Run) or "ollama"
- OPENAI_EMBEDDING_MODEL: defaults to "text-embedding-3-small" (cost-effective, high quality)
- OPENAI_API_KEY: required when using OpenAI (store in Google Secret Manager for Cloud Run)
- OLLAMA_EMBEDDING_MODEL: defaults to "nomic-embed-text" (local development only)

Cloud Run Deployment Notes:
- OpenAI is the recommended provider for serverless deployment
- Ollama requires persistent infrastructure and is not suitable for Cloud Run
- API keys should be managed through Google Secret Manager in production
"""

import os
import logging
from typing import Any

# Set up logging for better debugging in cloud environments
logger = logging.getLogger(__name__)


def get_embedding_function(
    provider: str | None = None,
    model: str | None = None,
) -> Any:
    """Return a LangChain-compatible embedding function optimized for cloud deployment.

    This factory function provides a unified interface for different embedding providers,
    with intelligent defaults and comprehensive error handling for production environments.

    Args:
        provider: Embedding provider to use. Options:
            - "openai" (default, recommended for Cloud Run): Uses OpenAI's embedding API
            - "ollama": Local Ollama embeddings (development only, not for Cloud Run)
            Defaults to EMBEDDINGS_PROVIDER environment variable or "openai".
        model: Optional explicit model name override.

    Returns:
        An embeddings object implementing LangChain's Embeddings interface.

    Raises:
        RuntimeError: If required packages are not installed, API keys are missing,
                     or the provider is not supported.

    Cloud Run Notes:
        - OpenAI provider is optimized for serverless deployment
        - API keys are automatically sourced from environment variables
        - Comprehensive logging for debugging in cloud environments
        - Fallback error handling for missing dependencies
    """
    selected = (provider or os.getenv("EMBEDDINGS_PROVIDER", "openai")).lower()
    logger.info(f"Initializing embedding provider: {selected}")

    if selected == "openai":
        return _create_openai_embeddings(model)
    elif selected == "ollama":
        return _create_ollama_embeddings(model)
    else:
        error_msg = f"Unknown embeddings provider: '{selected}'. Supported providers: 'openai', 'ollama'"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def _create_openai_embeddings(model: str | None = None) -> Any:
    """Create OpenAI embeddings instance with production-ready configuration.
    
    Args:
        model: Optional model name override.
        
    Returns:
        Configured OpenAIEmbeddings instance.
        
    Raises:
        RuntimeError: If langchain-openai is not installed or API key is missing.
    """
    try:
        from langchain_openai import OpenAIEmbeddings  # type: ignore
        logger.info("Successfully imported OpenAI embeddings")
    except ImportError as e:
        error_msg = (
            "langchain-openai is not installed. "
            "Install it with: pip install langchain-openai"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

    # Check for API key with detailed error messaging
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        error_msg = (
            "OPENAI_API_KEY environment variable not set. "
            "For local development: export OPENAI_API_KEY='sk-your-key-here' "
            "For Cloud Run: ensure the secret is properly configured in deployment"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Validate API key format
    if not api_key.startswith("sk-"):
        logger.warning("OpenAI API key does not start with 'sk-', this may indicate an invalid key")

    model_name = model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    logger.info(f"Using OpenAI embedding model: {model_name}")

    try:
        # Create embeddings instance with production-optimized configuration
        embeddings = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            # Optimize for cloud deployment
            request_timeout=30,  # Reasonable timeout for Cloud Run
            max_retries=3,       # Retry failed requests
        )
        logger.info("OpenAI embeddings initialized successfully")
        return embeddings
    except Exception as e:
        error_msg = f"Failed to initialize OpenAI embeddings: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def _create_ollama_embeddings(model: str | None = None) -> Any:
    """Create Ollama embeddings instance for local development.
    
    Note: Ollama is not recommended for Cloud Run deployment as it requires
    persistent infrastructure and local model management.
    
    Args:
        model: Optional model name override.
        
    Returns:
        Configured OllamaEmbeddings instance.
        
    Raises:
        RuntimeError: If langchain-ollama is not installed or Ollama is unavailable.
    """
    logger.warning(
        "Using Ollama embeddings. Note: Ollama is not suitable for Cloud Run deployment. "
        "Consider using OpenAI embeddings for production."
    )
    
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore
        logger.info("Successfully imported Ollama embeddings")
    except ImportError as e:
        error_msg = (
            "langchain-ollama is not installed. "
            "Install it with: pip install langchain-ollama"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

    model_name = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    logger.info(f"Using Ollama embedding model: {model_name}")

    try:
        # Create Ollama embeddings instance
        embeddings = OllamaEmbeddings(model=model_name)
        logger.info("Ollama embeddings initialized successfully")
        return embeddings
    except Exception as e:
        error_msg = (
            f"Failed to initialize Ollama embeddings: {str(e)}. "
            "Ensure Ollama is running locally and the model is available. "
            "Run: ollama serve && ollama pull {model_name}"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_provider_info() -> dict[str, Any]:
    """Get information about the current embedding provider configuration.
    
    Returns:
        Dictionary containing provider configuration details.
    """
    provider = os.getenv("EMBEDDINGS_PROVIDER", "openai").lower()
    
    if provider == "openai":
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        api_key_set = bool(os.getenv("OPENAI_API_KEY"))
        return {
            "provider": "openai",
            "model": model,
            "api_key_configured": api_key_set,
            "cloud_ready": True,
            "dimensions": 1536 if "small" in model else (3072 if "large" in model else 1536),
        }
    elif provider == "ollama":
        model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        return {
            "provider": "ollama",
            "model": model,
            "api_key_configured": True,  # No API key needed for Ollama
            "cloud_ready": False,
            "dimensions": 768,  # nomic-embed-text dimensions
        }
    else:
        return {
            "provider": provider,
            "error": f"Unknown provider: {provider}",
            "cloud_ready": False,
        }

