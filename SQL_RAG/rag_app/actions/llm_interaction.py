"""
LLM Interaction Module

This module handles all interactions with large language models for RAG applications.
Currently supports Google's Gemini models through the GenAI client.
"""

import time
from typing import Dict, Optional, Any
from google import genai

# Model configuration
GENAI_MODEL_NAME = "gemini-2.5-flash-lite"

def initialize_llm_client():
    """Initialize and return the Google GenAI client.
    
    Returns:
        Initialized GenAI client
    """
    return genai.Client(
        vertexai=True,
        project="wmt-dv-bq-analytics",
        location="global",
    )

def generate_answer_from_context(
    query: str, 
    context: str,
    model_name: str = GENAI_MODEL_NAME,
    retries: int = 3,
    system_prompt: Optional[str] = None
) -> tuple[str, Dict[str, Any]]:
    """Generate an answer to a question using the provided context with Google's Gemini.
    
    Args:
        query: The user's question
        context: The context information to help answer the question
        model_name: The specific GenAI model to use
        retries: Number of retry attempts for API calls
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
    
    # Get client
    client = initialize_llm_client()
    
    # Resilient call with simple exponential backoff
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            answer_text = response.text.strip()
            
            # Estimate token usage (Google GenAI doesn't provide detailed counts)
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
            wait_secs = 2 ** attempt
            print(f"Google GenAI API error ({exc}). Retrying in {wait_secs}s...")
            time.sleep(wait_secs)
    
    # This line should never be reached due to the exception in the loop
    raise RuntimeError("Failed to generate answer after all retry attempts")