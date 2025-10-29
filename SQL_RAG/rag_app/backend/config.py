"""
Configuration settings for the SQL RAG application
"""
import os
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

settings = Settings()