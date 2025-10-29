"""
Configuration settings for the SQL RAG application
"""
import os
from pathlib import Path

# Simple configuration without Pydantic for now
class Settings:
    def __init__(self):
        # BigQuery Configuration
        self.BIGQUERY_PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID", "demo-project")
        self.MODEL_LOCATION = os.getenv("MODEL_LOCATION", "us-central1")
        
        # Gemini Configuration
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "demo-key")
        
        # Application Configuration
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY", "demo-secret-key-change-in-production")
        
        # Data paths
        self.PROJECT_ROOT = Path(__file__).parent.parent
        self.FAISS_INDICES_DIR = self.PROJECT_ROOT / "faiss_indices"
        self.DATA_NEW_DIR = self.PROJECT_ROOT / "data_new"
        self.SCHEMA_CSV_PATH = self.DATA_NEW_DIR / "thelook_ecommerce_schema.csv"
        self.EMBEDDINGS_PATH = self.PROJECT_ROOT / "data" / "embeddings"
        self.QUERY_CACHE_PATH = self.PROJECT_ROOT / "data" / "query_cache"
        self.LLM_CACHE_PATH = self.PROJECT_ROOT / "data" / "llm_cache"
        
        # Cache
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

settings = Settings()