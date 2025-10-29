"""
Streamlit application for SQL query generation and data analysis
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os
import json
from typing import Dict, Any
import asyncio
from pathlib import Path

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"✅ Loaded environment from: {env_path}")
else:
    print(f"⚠️ No .env file found at: {env_path}")

from api import chat, data, sql, query_search
from services.websocket_service import WebSocketManager
from models.schemas import ChatRequest, ChatResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up RAG SQL Service")
    # Initialize any connections here
    yield
    # Shutdown
    logger.info("Shutting down RAG SQL Service")
    # Cleanup connections
    await websocket_manager.disconnect_all()

app = FastAPI(
    title="RAG SQL Service",
    description="RAG-powered SQL chat with BigQuery integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
        "http://localhost:80",      # Nginx proxy on localhost
        "http://127.0.0.1:80",      # Nginx proxy on 127.0.0.1
        "http://0.0.0.0:80",        # Alternative local access
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(sql.router, prefix="/api/sql", tags=["sql"])
app.include_router(data.router, prefix="/api", tags=["data"])
app.include_router(query_search.router, prefix="/api", tags=["query-search"])

# Health check endpoint
@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RAG SQL Service",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic info"""
    return """
    <html>
        <head>
            <title>RAG SQL Service</title>
        </head>
        <body>
            <h1>RAG SQL Service</h1>
            <p>FastAPI backend for SQL RAG application</p>
            <p><a href="/docs">API Documentation</a></p>
            <p><a href="/health">Health Check</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )