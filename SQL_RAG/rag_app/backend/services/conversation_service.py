"""
Conversation Service for managing chat sessions and message history
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self):
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        self.conversations[session_id] = []
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """Add a message to a conversation session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        message["timestamp"] = datetime.now().isoformat()
        self.conversations[session_id].append(message)
        logger.info(f"Added message to session {session_id}")
    
    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a conversation"""
        return self.conversations.get(session_id, [])
    
    def get_sessions_for_user(self, user_id: str) -> Dict[str, Any]:
        """Get all sessions for a user"""
        return {
            "sessions": [
                {
                    "id": session_id,
                    "message_count": len(messages),
                    "last_updated": messages[-1].get("timestamp") if messages else None
                }
                for session_id, messages in self.conversations.items()
            ]
        }

# Global instance
conversation_service = ConversationService()