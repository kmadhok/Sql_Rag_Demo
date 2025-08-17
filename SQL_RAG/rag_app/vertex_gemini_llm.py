#!/usr/bin/env python3
"""
Vertex AI Gemini LLM Module for SQL RAG System

A wrapper class that provides the same interface as OllamaLLM but uses
Google Cloud Vertex AI Gemini models for text generation.

Features:
- Drop-in replacement for OllamaLLM
- Support for Gemini 2.5 Flash Lite and other Gemini models
- Robust error handling and connection testing
- Authentication via Application Default Credentials
- Configurable project and location settings
"""

import time
import logging
import os
from typing import Optional, Tuple, Dict, Any

# Vertex AI imports
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    print("❌ Error: google-cloud-aiplatform is required. Install with: pip install google-cloud-aiplatform>=1.50.0")
    vertexai = None
    GenerativeModel = None
    VERTEX_AI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_LOCATION = "us-central1"
MAX_RETRIES = 3
RETRY_DELAY = 2.0


class VertexGeminiLLM:
    """
    Vertex AI Gemini LLM wrapper that provides the same interface as OllamaLLM
    
    This class allows for drop-in replacement of OllamaLLM with Google Cloud
    Vertex AI Gemini models while maintaining the same API interface.
    """
    
    def __init__(
        self, 
        model: str = DEFAULT_MODEL,
        project_id: Optional[str] = None,
        location: str = DEFAULT_LOCATION,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY
    ):
        """
        Initialize the Vertex AI Gemini LLM
        
        Args:
            model: Gemini model name (e.g., "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro")
            project_id: Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: Vertex AI location (defaults to VERTEX_AI_LOCATION env var or us-central1)
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.model_name = model
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location or os.getenv('VERTEX_AI_LOCATION', DEFAULT_LOCATION)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.model = None
        self._initialized = False
        
        # Validate required parameters
        if not self.project_id:
            raise ValueError(
                "Google Cloud project ID is required. Set GOOGLE_CLOUD_PROJECT environment variable "
                "or pass project_id parameter."
            )
        
        if not VERTEX_AI_AVAILABLE:
            raise ImportError(
                "google-cloud-aiplatform is required. Install with: "
                "pip install google-cloud-aiplatform>=1.50.0"
            )
        
        # Initialize Vertex AI
        self._setup_vertexai()
    
    def _setup_vertexai(self):
        """Initialize Vertex AI and the GenerativeModel"""
        try:
            # Initialize Vertex AI with project and location
            vertexai.init(project=self.project_id, location=self.location)
            
            # Initialize the generative model
            self.model = GenerativeModel(self.model_name)
            self._initialized = True
            
            logger.info(f"✅ Vertex AI Gemini initialized: {self.model_name} in {self.location}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
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
            raise RuntimeError("Vertex AI Gemini LLM not properly initialized")
        
        for attempt in range(self.max_retries + 1):
            try:
                # Generate content using Vertex AI Gemini
                response = self.model.generate_content(prompt)
                
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
        Test connection to Vertex AI Gemini service
        
        Returns:
            Tuple of (success, status_message)
        """
        try:
            if not self._initialized:
                return False, "❌ Vertex AI not initialized"
            
            # Test with a simple query
            start_time = time.time()
            test_prompt = "Hello, please respond with 'Hello from Vertex AI Gemini!'"
            response = self.invoke(test_prompt)
            response_time = time.time() - start_time
            
            if response and len(response.strip()) > 0:
                return True, f"✅ {self.model_name} ready ({response_time:.2f}s response time)"
            else:
                return False, f"❌ {self.model_name} responded but returned empty response"
                
        except Exception as e:
            error_msg = str(e)
            
            # Provide helpful error messages for common issues
            if "Authentication" in error_msg or "credentials" in error_msg.lower():
                return False, (
                    "❌ Authentication failed. Run: gcloud auth application-default login "
                    "or set GOOGLE_APPLICATION_CREDENTIALS environment variable"
                )
            elif "project" in error_msg.lower():
                return False, (
                    f"❌ Project '{self.project_id}' not found or inaccessible. "
                    "Check GOOGLE_CLOUD_PROJECT environment variable"
                )
            elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
                return False, (
                    "❌ Permission denied. Enable Vertex AI API and ensure proper IAM roles: "
                    "roles/aiplatform.user"
                )
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                return False, "❌ API quota exceeded or rate limited. Try again later"
            elif "region" in error_msg.lower() or "location" in error_msg.lower():
                return False, (
                    f"❌ Location '{self.location}' not supported for {self.model_name}. "
                    "Try us-central1 or check available regions"
                )
            else:
                return False, f"❌ Vertex AI connection error: {error_msg}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration
        
        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'project_id': self.project_id,
            'location': self.location,
            'provider': 'Google Cloud Vertex AI',
            'initialized': self._initialized,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }
    
    def __str__(self) -> str:
        """String representation of the LLM instance"""
        return f"VertexGeminiLLM(model={self.model_name}, project={self.project_id}, location={self.location})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return (
            f"VertexGeminiLLM(model='{self.model_name}', project_id='{self.project_id}', "
            f"location='{self.location}', initialized={self._initialized})"
        )


def test_vertex_gemini_connection(
    model: str = DEFAULT_MODEL,
    project_id: Optional[str] = None,
    location: str = DEFAULT_LOCATION
) -> Tuple[bool, str]:
    """
    Test connection to Vertex AI Gemini service
    
    Args:
        model: Gemini model name to test
        project_id: Google Cloud project ID
        location: Vertex AI location
        
    Returns:
        Tuple of (success, status_message)
    """
    try:
        llm = VertexGeminiLLM(model=model, project_id=project_id, location=location)
        return llm.test_connection()
    except Exception as e:
        return False, f"❌ Failed to initialize Vertex AI Gemini: {e}"


def main():
    """Test function for the Vertex AI Gemini LLM"""
    print("🤖 Testing Vertex AI Gemini LLM")
    print("=" * 60)
    
    # Check environment setup
    project_id = 'brainrot-453319'
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        print("   Set it with: export GOOGLE_CLOUD_PROJECT='your-project-id'")
        return
    
    print(f"📋 Project ID: {project_id}")
    print(f"📍 Location: {DEFAULT_LOCATION}")
    print(f"🤖 Model: {DEFAULT_MODEL}")
    
    # Test connection
    print("\n1. Testing connection...")
    success, message = test_vertex_gemini_connection()
    print(message)
    
    if not success:
        print("\n❌ Cannot proceed without working Vertex AI connection.")
        print("\n🔧 Setup steps:")
        print("1. Install dependencies: pip install google-cloud-aiplatform>=1.50.0")
        print("2. Set project: export GOOGLE_CLOUD_PROJECT='your-project-id'")
        print("3. Authenticate: gcloud auth application-default login")
        print("4. Enable Vertex AI API in Google Cloud Console")
        return
    
    # Test LLM functionality
    print("\n2. Testing LLM functionality...")
    try:
        llm = VertexGeminiLLM()
        
        test_prompts = [
            "What is SQL?",
            "Explain the difference between INNER JOIN and LEFT JOIN in one sentence.",
            "List 3 SQL aggregate functions."
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n   Test {i}: {prompt}")
            start_time = time.time()
            response = llm.invoke(prompt)
            response_time = time.time() - start_time
            
            print(f"   Response ({response_time:.2f}s): {response[:100]}{'...' if len(response) > 100 else ''}")
    
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return
    
    print("\n✅ Vertex AI Gemini LLM is ready for use!")
    print("   You can now replace OllamaLLM with VertexGeminiLLM in your applications.")


if __name__ == "__main__":
    main()