#!/usr/bin/env python3
"""
Firestore Client Utilities for SQL RAG Application

Provides a simple and robust interface to Google Cloud Firestore for
conversation persistence in the Cloud Run deployment.

Features:
- Automatic client initialization with Cloud Run service account
- Connection health checking and error handling
- Graceful fallback when Firestore is unavailable
- Optimized for Cloud Run stateless environment
"""

import os
import logging
from typing import Optional
from google.cloud import firestore
from google.cloud.exceptions import GoogleCloudError
import google.auth.exceptions

logger = logging.getLogger(__name__)

class FirestoreClient:
    """
    Wrapper class for Google Cloud Firestore client with robust error handling
    and automatic configuration for Cloud Run deployment.
    """
    
    def __init__(self):
        """Initialize Firestore client with automatic Cloud Run configuration."""
        self._client: Optional[firestore.Client] = None
        self._is_available = False
        self._initialization_attempted = False
        
    def _initialize_client(self) -> bool:
        """
        Initialize the Firestore client with proper error handling.
        
        Returns:
            bool: True if client was successfully initialized, False otherwise
        """
        if self._initialization_attempted:
            return self._is_available
            
        self._initialization_attempted = True
        
        try:
            # Initialize with default credentials (Cloud Run service account)
            self._client = firestore.Client()
            
            # Test connection with a lightweight operation
            collections = list(self._client.collections())
            logger.info("✅ Firestore client initialized successfully")
            self._is_available = True
            return True
            
        except google.auth.exceptions.DefaultCredentialsError as e:
            logger.warning(f"⚠️ Firestore credentials not available: {e}")
            self._is_available = False
            return False
            
        except GoogleCloudError as e:
            logger.warning(f"⚠️ Firestore service unavailable: {e}")
            self._is_available = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing Firestore: {e}")
            self._is_available = False
            return False
    
    @property
    def is_available(self) -> bool:
        """
        Check if Firestore is available for use.
        
        Returns:
            bool: True if Firestore client is ready, False otherwise
        """
        if not self._initialization_attempted:
            self._initialize_client()
        return self._is_available
    
    @property
    def client(self) -> Optional[firestore.Client]:
        """
        Get the Firestore client instance.
        
        Returns:
            Optional[firestore.Client]: Firestore client if available, None otherwise
        """
        if self.is_available:
            return self._client
        return None
    
    def test_connection(self) -> dict:
        """
        Test Firestore connection and return status information.
        
        Returns:
            dict: Connection status with details
        """
        status = {
            'available': False,
            'error': None,
            'project_id': None,
            'collections_accessible': False
        }
        
        try:
            if not self.is_available:
                status['error'] = 'Client not initialized'
                return status
                
            # Test basic operations
            status['project_id'] = self._client.project
            
            # Test collection access (lightweight operation)
            collections = list(self._client.collections())
            status['collections_accessible'] = True
            status['available'] = True
            
            logger.info(f"✅ Firestore connection test successful for project: {status['project_id']}")
            
        except Exception as e:
            status['error'] = str(e)
            logger.warning(f"⚠️ Firestore connection test failed: {e}")
            
        return status


# Global client instance for reuse across the application
_firestore_client: Optional[FirestoreClient] = None


def get_firestore_client() -> FirestoreClient:
    """
    Get the global Firestore client instance (singleton pattern).
    
    Returns:
        FirestoreClient: Shared Firestore client instance
    """
    global _firestore_client
    
    if _firestore_client is None:
        _firestore_client = FirestoreClient()
        
    return _firestore_client


def is_firestore_available() -> bool:
    """
    Quick check if Firestore is available without creating a client.
    
    Returns:
        bool: True if Firestore should be available, False otherwise
    """
    try:
        # Check if we're in a Google Cloud environment
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GCP_PROJECT')
        if project_id:
            return True
            
        # Check if we have explicit credentials
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            return True
            
        # Try to get default credentials without initializing client
        import google.auth
        credentials, project = google.auth.default()
        return project is not None
        
    except Exception:
        return False


if __name__ == "__main__":
    """Test script for Firestore client functionality."""
    import json
    
    print("🧪 Testing Firestore Client...")
    
    # Test availability check
    print(f"Environment check: {is_firestore_available()}")
    
    # Test client initialization
    client = get_firestore_client()
    print(f"Client available: {client.is_available}")
    
    # Test connection
    status = client.test_connection()
    print(f"Connection test: {json.dumps(status, indent=2)}")
    
    if client.is_available:
        print("✅ Firestore client is ready for use")
    else:
        print("❌ Firestore client is not available")
        print("💡 Ensure you're running in Google Cloud or have GOOGLE_APPLICATION_CREDENTIALS set")