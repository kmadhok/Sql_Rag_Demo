from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import os
import json
from typing import Dict, Any
import asyncio

from api import chat, data, sql
from services.websocket_service import WebSocketManager
from models.schemas import ChatRequest, ChatResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket manager for real-time connections
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up RAG SQL Service")
    # Initialize services here if needed
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
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(sql.router, prefix="/api/sql", tags=["sql"])
app.include_router(data.router, prefix="/api/data", tags=["data"])

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                # Validate message structure
                chat_request = ChatRequest(**message_data)
                
                # Process the message using chat service
                # This would use your existing RAG logic
                try:
                    from services.rag_service import rag_service
                    from models.schemas import ChatResponse
                    from datetime import datetime
                    
                    # Process query
                    result = await rag_service.process_query(
                        question=chat_request.message,
                        agent_type=chat_request.agentType,
                        conversation_context=chat_request.conversationContext,
                        session_id=session_id
                    )
                    
                    # Send response
                    response = ChatResponse(
                        message=result.get('message', ''),
                        sqlQuery=result.get('sql_query'),
                        sqlExecuted=result.get('sql_executed', False),
                        sqlResult=result.get('sql_result'),
                        sources=result.get('sources', []),
                        tokenUsage=result.get('token_usage', {}),
                        contextUtilization=result.get('context_utilization'),
                        agentUsed=result.get('agent_used'),
                        sessionId=session_id,
                        timestamp=datetime.now().isoformat(),
                        processingTime=result.get('processing_time')
                    )
                    
                    await websocket.send_text(response.json())
                    
                except Exception as e:
                    logger.error(f"Error processing chat message: {e}")
                    error_response = {
                        "error": "Failed to process message",
                        "message": str(e),
                        "sessionId": session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_text(json.dumps({
                    "error": "Invalid message format",
                    "sessionId": session_id
                }))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_text(json.dumps({
                    "error": "Failed to process message",
                    "message": str(e),
                    "sessionId": session_id
                }))
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from session {session_id}")
        await websocket_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket_manager.disconnect(websocket, session_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RAG SQL Service",
        "version": "1.0.0"
    }

# Root endpoint with basic info
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RAG SQL Service</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            .api-list { list-style: none; padding: 0; }
            .api-list li { margin: 10px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px; }
            .endpoint { font-family: monospace; background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ RAG SQL Service API</h1>
            <p>FastAPI backend for SQL RAG application</p>
            
            <h2>Available Endpoints:</h2>
            <ul class="api-list">
                <li><span class="endpoint">GET /api/data/schema</span> - Get database schema</li>
                <li><span class="endpoint">GET /api/data/analytics</span> - Get catalog analytics</li>
                <li><span class="endpoint">GET /api/data/queries</span> - Get query catalog</li>
                <li><span class="endpoint">POST /api/chat/query</span> - Send chat query</li>
                <li><span class="endpoint">POST /api/chat/execute-sql</span> - Execute SQL</li>
                <li><span class="endpoint">GET /api/chat/history/{session_id}</span> - Get conversation history</li>
                <li><span class="endpoint">WS /ws/chat/{session_id}</span> - Real-time chat WebSocket</li>
            </ul>
            
            <h2>Documentation:</h2>
            <p>Visit <a href="/docs">/docs</a> for interactive API documentation</p>
        </div>
    </body>
    </html>
    """

# For development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )