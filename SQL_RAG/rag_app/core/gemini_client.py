#!/usr/bin/env python3
"""
Gemini Client Module for SQL RAG System

A clean wrapper around Google's genai library that uses Vertex AI authentication
for enterprise-grade security and integration with Google Cloud Platform.

Features:
- Vertex AI authentication with Google Cloud project integration
- Support for multiple Gemini models
- Robust error handling and connection testing
- Drop-in replacement for API key-based authentication
- Environment variable configuration for security
"""

import time
import logging
import os
from typing import Optional, Tuple, Dict, Any

# Google Generative AI imports
try:
    import google.generativeai as genai
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
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY
    ):
        """
        Initialize the Gemini Client with API key authentication
        
        Args:
            model: Gemini model name (e.g., "gemini-2.5-flash", "gemini-2.5-flash-lite")
            api_key: Google Gemini API key (defaults to GEMINI_API_KEY env var)
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.model_name = model
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.model = None
        self._initialized = False
        
        # Validate required parameters
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter. Get your API key from: https://makersuite.google.com/app/apikey"
            )
        
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai is required. Install with: "
                "pip install google-generativeai"
            )
        
        # Initialize Gemini client
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Initialize Gemini client with Vertex AI authentication"""
        try:
            # Initialize the client with Vertex AI
            self.client = genai.Client(
                vertexai=True,
                project=f'{self.project}',
                location=self.location,
            )
            self._initialized = True
            
            logger.info(f"✅ Gemini client initialized: {self.model_name} (project: {self.project})")
            
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
            if "authentication" in error_msg.lower() or "credential" in error_msg.lower():
                return False, (
                    "❌ Vertex AI authentication failed. Check your vertex_ai_client environment variable "
                    "and ensure Google Cloud authentication is configured (gcloud auth application-default login)"
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
            'provider': 'Google Gemini (Vertex AI)',
            'project': self.project,
            'location': self.location,
            'initialized': self._initialized,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }
    
    def __str__(self) -> str:
        """String representation of the client instance"""
        return f"GeminiClient(model={self.model_name}, project={self.project})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (
            f"GeminiClient(model='{self.model_name}', "
            f"project='{self.project}', location='{self.location}', initialized={self._initialized})"
        )


def test_gemini_connection(
    model: str = DEFAULT_MODEL,
    project: Optional[str] = None,
    location: str = "global"
) -> Tuple[bool, str]:
    """
    Test connection to Gemini service with Vertex AI
    
    Args:
        model: Gemini model name to test
        project: Google Cloud project ID (defaults to vertex_ai_client env var)
        location: Vertex AI location
        
    Returns:
        Tuple of (success, status_message)
    """
    try:
        client = GeminiClient(model=model, project=project, location=location)
        return client.test_connection()
    except Exception as e:
        return False, f"❌ Failed to initialize Gemini client: {e}"


def main():
    """Test function for the Gemini Client"""
    print("🤖 Testing Gemini Client")
    print("=" * 60)
    
    # Check environment setup
    project = os.getenv('vertex_ai_client')
    if not project:
        print("❌ vertex_ai_client environment variable not set")
        print("   Set it with: export vertex_ai_client='your-gcp-project-id'")
        print("   Configure authentication: gcloud auth application-default login")
        return
    
    print(f"🏗️ Project: {project}")
    print(f"🤖 Model: {DEFAULT_MODEL}")
    print(f"📍 Location: global")
    
    # Test connection
    print("\n1. Testing connection...")
    success, message = test_gemini_connection()
    print(message)
    
    if not success:
        print("\n❌ Cannot proceed without working Gemini connection.")
        print("\n🔧 Setup steps:")
        print("1. Install dependencies: pip install google-generativeai")
        print("2. Set up Google Cloud project with Vertex AI enabled")
        print("3. Authenticate: gcloud auth application-default login")
        print("4. Set environment variable: export vertex_ai_client='your-gcp-project-id'")
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