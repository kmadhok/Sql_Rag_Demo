#!/usr/bin/env python3
"""
Gemini Client Module for SQL RAG System

A clean wrapper around Google's genai library that provides the same interface
as the previous Vertex AI implementation but uses the simpler google.genai approach
from gemini_quick_start.py.

Features:
- Configurable authentication via API key or Vertex AI Gen AI SDK
- Support for multiple Gemini models
- Robust error handling and connection testing
- Drop-in replacement for VertexGeminiLLM
- Environment variable configuration for security
"""

import time
import logging
import os
from typing import Optional, Tuple, Dict, Any

# Google Generative AI imports
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    print("❌ Error: google-generativeai is required. Install with: pip install google-generativeai")
    genai = None
    GENAI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 2.0


class GeminiClient:
    """
    Gemini Client wrapper that provides a clean interface for Google's genai library
    
    This class provides the same interface as VertexGeminiLLM but uses the simpler
    google.genai approach for easier setup and deployment.
    """
    
    def __init__(
        self, 
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        client_mode: Optional[str] = None,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY
    ):
        """
        Initialize the Gemini Client
        
        Args:
            model: Gemini model name (e.g., "gemini-2.5-flash", "gemini-2.5-flash-lite")
            api_key: Gemini API key for API mode (defaults to GEMINI_API_KEY env var)
            client_mode: Override authentication mode ("api" or "sdk"); defaults to GENAI_CLIENT_MODE env var
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.model_name = model
        raw_mode = client_mode if client_mode is not None else os.getenv("GENAI_CLIENT_MODE")
        if not raw_mode:
            vertexai_override = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
            if vertexai_override is not None:
                default_mode = "sdk" if vertexai_override.lower() in ("true", "1", "yes") else "api"
            elif os.getenv("GOOGLE_CLOUD_PROJECT") and not (
                os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            ):
                default_mode = "sdk"
            else:
                default_mode = "api"
            raw_mode = default_mode
        self.client_mode = raw_mode.strip().lower()
        if self.client_mode not in {"api", "sdk"}:
            raise ValueError("GENAI_CLIENT_MODE must be 'api' or 'sdk'")
        # Attempt to load from .env if not already present
        if self.client_mode == "api" and not api_key and not os.getenv('GEMINI_API_KEY'):
            try:
                from dotenv import load_dotenv, find_dotenv
                _env_path = find_dotenv(usecwd=True)
                if _env_path:
                    load_dotenv(_env_path, override=False)
                    logger.debug(f"Loaded environment from {_env_path}")
            except Exception as _e:
                logger.debug(f"dotenv not loaded in GeminiClient: {_e}")

        # Accept both GEMINI_API_KEY and GOOGLE_API_KEY for convenience
        if self.client_mode == "api":
            self.api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        else:
            self.api_key = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = None
        self.project_id: Optional[str] = None
        self.location: Optional[str] = None
        self._initialized = False
        
        # Validate required parameters
        if self.client_mode == "api":
            if not self.api_key:
                raise ValueError(
                    "Gemini API key is required in API mode. Set GEMINI_API_KEY environment variable "
                    "or pass api_key parameter. Get your API key from: https://makersuite.google.com/app/apikey"
                )
        else:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not project_id:
                raise ValueError(
                    "GOOGLE_CLOUD_PROJECT is required when GENAI_CLIENT_MODE=sdk. "
                    "Ensure Application Default Credentials are available (e.g. set GOOGLE_APPLICATION_CREDENTIALS)."
                )
            self.project_id = project_id
            self.location = (
                os.getenv("GOOGLE_CLOUD_LOCATION")
                or os.getenv("GOOGLE_CLOUD_REGION")
                or "global"
            )
        
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai is required. Install with: "
                "pip install google-generativeai"
            )
        
        # Initialize Gemini client
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Initialize Gemini client using the configured authentication mode."""
        try:
            if self.client_mode == "sdk":
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location,
                )
                logger.info(
                    "✅ Gemini client initialized in Vertex SDK mode: %s (project=%s, location=%s)",
                    self.model_name,
                    self.project_id,
                    self.location,
                )
            else:
                # Initialize the client with API key
                self.client = genai.Client(api_key=self.api_key)
                logger.info("✅ Gemini client initialized in API mode: %s", self.model_name)
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def invoke(self, prompt: str) -> str:
        """
        Generate content using the Gemini model
        
        Args:
            prompt: Input prompt for the model
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If the model fails to generate content after all retries
        """
        if not self._initialized:
            raise RuntimeError("Gemini client not properly initialized")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Generate content using Gemini
                response = self.client.models.generate_content(
                    model=self.model_name, 
                    contents=prompt
                )
                
                # Extract and return the text
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
                else:
                    raise ValueError("Empty response from Gemini model")
                    
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
                    raise
    
    def invoke_structured(self, 
                         prompt: str, 
                         response_format: str = "json",
                         response_schema: Optional[Any] = None) -> str:
        """
        Generate structured content using the Gemini model with JSON schema
        
        Args:
            prompt: Input prompt for the model
            response_format: Response format ("json" for structured output)
            response_schema: Pydantic model class for response validation
            
        Returns:
            Generated JSON response as string
            
        Raises:
            Exception: If the model fails to generate content after all retries
        """
        if not self._initialized:
            raise RuntimeError("Gemini client not properly initialized")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Import types for structured output
                from google.genai import types
                
                # Build config for structured output
                config = types.GenerateContentConfig()
                
                if response_format == "json" and response_schema:
                    config.response_mime_type = "application/json"
                    config.response_schema = response_schema
                
                # Generate content using Gemini with structured output
                response = self.client.models.generate_content(
                    model=self.model_name, 
                    contents=prompt,
                    config=config
                )
                
                # Extract and return the text
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
                else:
                    raise ValueError("Empty response from Gemini model")
                    
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Structured output attempt {attempt + 1} failed: {e}. Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All structured output attempts failed: {e}")
                    raise
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Gemini service
        
        Returns:
            Tuple of (success, status_message)
        """
        try:
            if not self._initialized:
                return False, "❌ Gemini client not initialized"
            
            # Test with a simple query
            start_time = time.time()
            test_prompt = "Hello, please respond with 'Hello from Gemini!'"
            response = self.invoke(test_prompt)
            response_time = time.time() - start_time
            
            if response and len(response.strip()) > 0:
                return True, f"✅ {self.model_name} ready ({response_time:.2f}s response time)"
            else:
                return False, f"❌ {self.model_name} responded but returned empty response"
                
        except Exception as e:
            error_msg = str(e)
            
            # Provide helpful error messages for common issues
            if "API_KEY" in error_msg or "authentication" in error_msg.lower():
                return False, (
                    "❌ API key authentication failed. Check your GEMINI_API_KEY environment variable. "
                    "Get your API key from: https://makersuite.google.com/app/apikey"
                )
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                return False, "❌ API quota exceeded or rate limited. Try again later"
            elif "invalid" in error_msg.lower() and "model" in error_msg.lower():
                return False, (
                    f"❌ Invalid model '{self.model_name}'. "
                    "Try 'gemini-2.5-flash' or 'gemini-2.5-flash-lite'"
                )
            elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
                return False, "❌ Permission denied. Check your API key permissions"
            else:
                return False, f"❌ Gemini connection error: {error_msg}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'provider': 'Google Gemini',
            'api_key_set': bool(self.api_key),
            'initialized': self._initialized,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }
    
    def __str__(self) -> str:
        """String representation of the client instance"""
        return f"GeminiClient(model={self.model_name})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (
            f"GeminiClient(model='{self.model_name}', "
            f"api_key_set={bool(self.api_key)}, initialized={self._initialized})"
        )


def test_gemini_connection(
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Test connection to Gemini service
    
    Args:
        model: Gemini model name to test
        api_key: API key (defaults to GEMINI_API_KEY env var)
        
    Returns:
        Tuple of (success, status_message)
    """
    try:
        client = GeminiClient(model=model, api_key=api_key)
        return client.test_connection()
    except Exception as e:
        return False, f"❌ Failed to initialize Gemini client: {e}"


def main():
    """Test function for the Gemini Client"""
    print("🤖 Testing Gemini Client")
    print("=" * 60)
    
    # Check environment setup
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        print("   Set it with: export GEMINI_API_KEY='your-api-key'")
        print("   Get your API key from: https://makersuite.google.com/app/apikey")
        return
    
    print(f"🔑 API Key: {'*' * 10}...{api_key[-4:] if len(api_key) > 4 else '****'}")
    print(f"🤖 Model: {DEFAULT_MODEL}")
    
    # Test connection
    print("\n1. Testing connection...")
    success, message = test_gemini_connection()
    print(message)
    
    if not success:
        print("\n❌ Cannot proceed without working Gemini connection.")
        print("\n🔧 Setup steps:")
        print("1. Install dependencies: pip install google-generativeai")
        print("2. Get API key: https://makersuite.google.com/app/apikey")
        print("3. Set environment variable: export GEMINI_API_KEY='your-api-key'")
        return
    
    # Test client functionality
    print("\n2. Testing client functionality...")
    try:
        client = GeminiClient()
        
        test_prompts = [
            "What is SQL?",
            "Explain the difference between INNER JOIN and LEFT JOIN in one sentence.",
            "List 3 SQL aggregate functions."
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n   Test {i}: {prompt}")
            start_time = time.time()
            response = client.invoke(prompt)
            response_time = time.time() - start_time
            
            print(f"   Response ({response_time:.2f}s): {response[:100]}{'...' if len(response) > 100 else ''}")
    
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return
    
    print("\n✅ Gemini Client is ready for use!")
    print("   You can now use this client in your RAG applications.")


if __name__ == "__main__":
    main()
