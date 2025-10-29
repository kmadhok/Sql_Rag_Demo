"""
Chat API endpoints for SQL RAG application
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from config import settings
from services.rag_service import rag_service
from services.conversation_service import conversation_service

logger = logging.getLogger(__name__)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    agent_type: str = "normal"
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    session_id: str
    timestamp: datetime
    agent_used: str
    sql_query: Optional[str] = None
    sql_result: Optional[str] = None
    sources: List[Dict[str, Any]] = []
    token_usage: Dict[str, int] = {}
    context_utilization: float = 0.0

class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = None

class CreateSessionResponse(BaseModel):
    session_id: str
    message: str

# Create router without prefix (will be added in app.py)
router = APIRouter(tags=["chat"])

@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest = None):
    """Create a new chat session"""
    try:
        user_id = request.user_id if request else None
        session_id = conversation_service.create_session(user_id)
        return CreateSessionResponse(
            session_id=session_id,
            message="Session created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all chat sessions for a user"""
    try:
        sessions = conversation_service.get_sessions_for_user(user_id)
        return {"status": "success", "data": sessions}
    except Exception as e:
        logger.error(f"Error getting sessions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get all messages in a chat session"""
    try:
        messages = conversation_service.get_conversation(session_id)
        return {"status": "success", "data": {"messages": messages}}
    except Exception as e:
        logger.error(f"Error getting messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message to the chat assistant"""
    try:
        # Create or get session
        if not request.session_id:
            session_id = conversation_service.create_session(request.user_id)
        else:
            session_id = request.session_id
        
        # Add user message to conversation
        user_message = {
            "id": str(int(datetime.now().timestamp() * 1000)),
            "content": request.message,
            "role": "user",
            "timestamp": datetime.now().isoformat(),
        }
        conversation_service.add_message(session_id, user_message)
        
        # Process with RAG service
        rag_response = rag_service.process_query(
            question=request.message,
            agent_type=request.agent_type
        )
        
        # Add assistant message to conversation
        assistant_message = {
            "id": str(int(datetime.now().timestamp() * 1000) + 1),
            "content": rag_response.get("message", ""),
            "role": "assistant",
            "timestamp": datetime.now().isoformat(),
            "sql_query": rag_response.get("sql_query"),
            "sql_result": rag_response.get("sql_result"),
            "sources": rag_response.get("sources", []),
        }
        conversation_service.add_message(session_id, assistant_message)
        
        return ChatResponse(
            message=rag_response.get("message", ""),
            session_id=session_id,
            timestamp=datetime.now(),
            agent_used=rag_response.get("agent_used", request.agent_type),
            sql_query=rag_response.get("sql_query"),
            sql_result=rag_response.get("sql_result"),
            sources=rag_response.get("sources", []),
            token_usage=rag_response.get("token_usage", {}),
            context_utilization=rag_response.get("context_utilization", 0.0),
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    try:
        if session_id in conversation_service.conversations:
            del conversation_service.conversations[session_id]
            return {"status": "success", "message": "Session deleted"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))