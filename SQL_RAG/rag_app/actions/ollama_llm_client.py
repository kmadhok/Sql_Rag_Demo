"""
Ollama LLM Interaction Module

This module handles all interactions with local Ollama models for RAG applications.
Currently supports Phi3 models for local, private inference without API keys.
"""

import time
from typing import Dict, Optional, Any
from langchain_ollama import ChatOllama

# Model configuration
OLLAMA_MODEL_NAME = "phi3:3.8b"  # Primary Phi3 model
FALLBACK_MODELS = ["phi3.5:3.8b", "phi3:latest", "phi3"]  # Fallback options


def initialize_ollama_client(model_name: str = OLLAMA_MODEL_NAME) -> ChatOllama:
    """Initialize and return the Ollama ChatOllama client.
    
    Args:
        model_name: The Ollama model to use (defaults to phi3:3.8b)
    
    Returns:
        Initialized ChatOllama client
        
    Raises:
        Exception: If Ollama service is not available or model not found
    """
    try:
        client = ChatOllama(
            model=model_name,
            temperature=0.2,
            num_predict=512,  # Max tokens for response
        )
        
        # Test the connection with a simple query
        test_response = client.invoke("Hello")
        if not test_response:
            raise Exception("Ollama client test failed - no response received")
            
        return client
        
    except Exception as e:
        # Try fallback models
        for fallback_model in FALLBACK_MODELS:
            if fallback_model != model_name:  # Don't retry the same model
                try:
                    print(f"Trying fallback model: {fallback_model}")
                    client = ChatOllama(
                        model=fallback_model,
                        temperature=0.2,
                        num_predict=512,
                    )
                    test_response = client.invoke("Hello")
                    if test_response:
                        print(f"Successfully connected using {fallback_model}")
                        return client
                except Exception:
                    continue
        
        # If all models failed, provide helpful error message
        error_msg = (
            f"Could not connect to Ollama or load Phi3 model. "
            f"Please ensure:\n"
            f"1. Ollama is running: `ollama serve`\n"
            f"2. Phi3 model is installed: `ollama pull phi3:3.8b`\n"
            f"Original error: {e}"
        )
        raise Exception(error_msg)


def generate_answer_with_ollama(
    query: str, 
    context: str,
    model_name: str = OLLAMA_MODEL_NAME,
    retries: int = 3,
    system_prompt: Optional[str] = None
) -> tuple[str, Dict[str, Any]]:
    """Generate an answer to a question using the provided context with Ollama Phi3.
    
    Args:
        query: The user's question
        context: The context information to help answer the question
        model_name: The specific Ollama model to use
        retries: Number of retry attempts for connection issues
        system_prompt: Optional custom system prompt
    
    Returns:
        Tuple of (answer text, token usage statistics)
        
    Raises:
        Exception: If all retry attempts fail
    """
    # Default expert SQL analyst prompt if none provided
    if not system_prompt:
        system_prompt = (
            "You are an expert SQL analyst helping answer questions about a retail analytics codebase. "
            "Use ONLY the provided context to answer the user's question. If the answer is not contained "
            "within the context, respond with 'I don't know based on the provided context.'"
        )
    
    # Construct the full prompt
    prompt = f"{system_prompt}\n\nContext:\n{context}\n\nUser question: {query}\n\nAnswer:"
    
    # Get or initialize client
    client = None
    
    # Resilient call with simple exponential backoff
    for attempt in range(1, retries + 1):
        try:
            # Initialize client on each attempt (handles connection issues)
            if client is None:
                client = initialize_ollama_client(model_name)
            
            # Generate response
            response = client.invoke(prompt)
            answer_text = response.content.strip() if hasattr(response, 'content') else str(response).strip()
            
            # Estimate token usage (Ollama doesn't provide exact counts)
            prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
            completion_tokens = len(answer_text.split()) * 1.3  # Rough estimate
            token_usage = {
                'prompt_tokens': int(prompt_tokens),
                'completion_tokens': int(completion_tokens),
                'total_tokens': int(prompt_tokens + completion_tokens),
                'model': model_name
            }
            
            return answer_text, token_usage
            
        except Exception as exc:
            if attempt == retries:
                raise  # re-throw after last attempt
            
            # Reset client for next attempt
            client = None
            wait_secs = 2 ** attempt
            print(f"Ollama connection error ({exc}). Retrying in {wait_secs}s...")
            time.sleep(wait_secs)
    
    # This line should never be reached due to the exception in the loop
    raise RuntimeError("Failed to generate answer after all retry attempts")


def check_ollama_availability() -> tuple[bool, str]:
    """Check if Ollama is available and which Phi3 models are installed.
    
    Returns:
        Tuple of (is_available, status_message)
    """
    try:
        # Try to initialize with the primary model
        client = initialize_ollama_client()
        return True, f"Ollama is available with {OLLAMA_MODEL_NAME}"
        
    except Exception as e:
        # Check if it's a model issue vs service issue
        if "model" in str(e).lower():
            return False, f"Ollama service running but Phi3 model not found. Run: ollama pull phi3:3.8b"
        else:
            return False, f"Ollama service not available. Start with: ollama serve"


def list_available_phi3_models() -> list[str]:
    """List available Phi3 models in local Ollama installation.
    
    Returns:
        List of available Phi3 model names
    """
    available_models = []
    
    for model in [OLLAMA_MODEL_NAME] + FALLBACK_MODELS:
        try:
            client = ChatOllama(model=model, temperature=0)
            test_response = client.invoke("test")
            if test_response:
                available_models.append(model)
        except Exception:
            continue
    
    return available_models