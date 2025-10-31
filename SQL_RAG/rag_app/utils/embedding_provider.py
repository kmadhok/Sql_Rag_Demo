#!/usr/bin/env python3
"""
Embedding provider factory for SQL RAG application.

Provides a unified interface for different embedding providers with
optimized configuration for both local development and cloud deployment.

Supports:
- Google Gemini embeddings (default, recommended for Cloud Run and Vertex AI)
- OpenAI embeddings (production-ready, cloud-optimized)
- Ollama embeddings (local development, legacy support)

Configuration (environment variables):
- EMBEDDINGS_PROVIDER: "gemini" (default, recommended), "openai", or "ollama"
- GEMINI_EMBEDDING_MODEL: defaults to "gemini-embedding-001" (Google's embedding model)
- OPENAI_EMBEDDING_MODEL: defaults to "text-embedding-3-small" (cost-effective, high quality)
- GOOGLE_CLOUD_PROJECT: required for Gemini embeddings (your GCP project ID)
- GOOGLE_CLOUD_LOCATION: defaults to "global" for Gemini embeddings
- GENAI_CLIENT_MODE: "api" (default) uses API key auth, "sdk" uses Vertex AI with ADC
- GOOGLE_GENAI_USE_VERTEXAI: override to force Vertex AI usage (otherwise inferred from GENAI_CLIENT_MODE)
- OPENAI_API_KEY: required when using OpenAI (store in Google Secret Manager for Cloud Run)
- OLLAMA_EMBEDDING_MODEL: defaults to "nomic-embed-text" (local development only)

Cloud Run Deployment Notes:
- Gemini embeddings are RECOMMENDED for serverless deployment with Vertex AI
- OpenAI provider is also supported for serverless deployment
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
            - "gemini" (default, recommended for Cloud Run): Uses Google's Gemini embedding API via Vertex AI
            - "openai": Uses OpenAI's embedding API (alternative option)
            - "ollama": Local Ollama embeddings (development only, not for Cloud Run)
            Defaults to EMBEDDINGS_PROVIDER environment variable or "gemini".
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
    selected = (provider or os.getenv("EMBEDDINGS_PROVIDER", "gemini")).lower()
    logger.info(f"Initializing embedding provider: {selected}")

    if selected == "gemini":
        return _create_gemini_embeddings(model)
    elif selected == "openai":
        return _create_openai_embeddings(model)
    elif selected == "ollama":
        return _create_ollama_embeddings(model)
    else:
        error_msg = f"Unknown embeddings provider: '{selected}'. Supported providers: 'gemini', 'openai', 'ollama'"
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


def _create_gemini_embeddings(model: str | None = None) -> Any:
    """Create Google Gemini embeddings instance via Gen AI SDK.
    
    Recommended production choice for Cloud Run deployment with Vertex AI.
    
    Args:
        model: Optional model name override.
        
    Returns:
        Configured Gemini embeddings object compatible with LangChain interface.
        
    Raises:
        RuntimeError: If google-genai is not installed or required environment
                     variables are missing.
    """
    try:
        from google import genai
        from google.genai.types import EmbedContentConfig
        logger.info("Successfully imported Google Gen AI SDK")
    except ImportError as e:
        error_msg = (
            "google-genai is not installed. "
            "Install it with: pip install --upgrade google-genai"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

    raw_mode = os.getenv("GENAI_CLIENT_MODE")
    if not raw_mode:
        raw_mode = "api"
    client_mode = raw_mode.strip().lower()
    use_vertexai_env = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    if use_vertexai_env is None:
        use_vertexai = client_mode == "sdk"
    else:
        use_vertexai = use_vertexai_env.lower() in ("true", "1", "yes")

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = (
        os.getenv("GOOGLE_CLOUD_LOCATION")
        or os.getenv("GOOGLE_CLOUD_REGION")
        or "global"
    )
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if use_vertexai and not project_id:
        error_msg = (
            "GOOGLE_CLOUD_PROJECT environment variable not set. "
            "Required when using Vertex AI for embeddings. "
            "Configure gcloud or set GOOGLE_APPLICATION_CREDENTIALS."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    if not use_vertexai and not api_key:
        error_msg = (
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is required when using the public Gemini API "
            "for embeddings. Set GENAI_CLIENT_MODE=sdk to use Vertex AI credentials instead."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    model_name = model or os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    
    logger.info(f"Using Gemini embedding model: {model_name}")
    if use_vertexai:
        logger.info("Initializing Gemini embeddings via Vertex AI SDK (project=%s, location=%s)", project_id, location)
    else:
        logger.info("Initializing Gemini embeddings via public Gemini API key")

    try:
        # Initialize Gen AI client
        if use_vertexai:
            client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location
            )
        else:
            client = genai.Client(api_key=api_key)
        
        # Create a LangChain-compatible wrapper for Gemini embeddings
        class GeminiEmbeddings:
            """LangChain-compatible wrapper for Google Gemini embeddings."""
            
            def __init__(self, client: genai.Client, model: str, task_type: str = "RETRIEVAL_DOCUMENT"):
                self.client = client
                self.model = model
                self.task_type = task_type
                # Gemini embedding has 768 dimensions by default
                self._dimension = 768
                
            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                """Embed multiple documents for retrieval."""
                return self._embed_batch(texts, "RETRIEVAL_DOCUMENT")
                
            def embed_query(self, text: str) -> list[float]:
                """Embed a single query for retrieval."""
                return self._embed_batch([text], "RETRIEVAL_QUERY")[0]
            
            def __call__(self, input_text: str | list[str]) -> list[float] | list[list[float]]:
                """Make the embedding function callable directly.
                
                This is required for compatibility with LangChain vector stores
                that expect the embedding function to be callable.
                
                Args:
                    input_text: Single text string or list of texts to embed.
                    
                Returns:
                    Embedding vector(s) as list(s) of floats.
                """
                if isinstance(input_text, str):
                    # Single text - use query embedding
                    return self.embed_query(input_text)
                elif isinstance(input_text, list):
                    # Multiple texts - use document embedding
                    return self.embed_documents(input_text)
                else:
                    raise TypeError(f"Expected str or list[str], got {type(input_text)}")
                
            def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
                """Internal method to embed a batch of texts."""
                embeddings = []
                
                # Process texts in batches to avoid rate limits
                batch_size = 100  # Gemini has generous rate limits
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    
                    try:
                        response = client.models.embed_content(
                            model=self.model,
                            contents=batch,
                            config=EmbedContentConfig(
                                task_type=task_type,
                                output_dimensionality=768  # Standard Gemini embedding dimension
                            )
                        )
                        
                        # Extract embedding values from response
                        for embedding in response.embeddings:
                            embeddings.append(embedding.values)
                            
                    except Exception as batch_error:
                        error_msg = f"Failed to embed batch {i//batch_size + 1}: {str(batch_error)}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg) from batch_error
                
                return embeddings
            
            @property
            def dimension(self) -> int:
                """Return the embedding dimension."""
                return self._dimension
                
        embeddings = GeminiEmbeddings(client, model_name)
        logger.info("Gemini embeddings initialized successfully")
        return embeddings
        
    except Exception as e:
        error_msg = (
            f"Failed to initialize Gemini embeddings: {str(e)}. "
            "Ensure Google Cloud authentication is properly configured. "
            "For local development: run 'gcloud auth application-default login' "
            "For Cloud Run: ensure the service account has 'aiplatform.user' role"
        )
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
    provider = os.getenv("EMBEDDINGS_PROVIDER", "gemini").lower()
    
    if provider == "gemini":
        model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        raw_mode = os.getenv("GENAI_CLIENT_MODE")
        if not raw_mode:
            raw_mode = "api"
        client_mode = raw_mode.strip().lower()
        use_vertexai_env = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
        if use_vertexai_env is None:
            use_vertexai = client_mode == "sdk"
        else:
            use_vertexai = use_vertexai_env.lower() in ("true", "1", "yes")
        api_key_set = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        return {
            "provider": "gemini",
            "model": model,
            "project_id": project_id or "NOT_SET",
            "use_vertexai": use_vertexai,
            "client_mode": client_mode,
            "api_key_configured": api_key_set,
            "cloud_ready": True,
            "dimensions": 768,  # Gemini embedding standard dimensions
        }
    elif provider == "openai":
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
