#!/usr/bin/env python3
"""
Conversation Manager for SQL RAG Application

Handles persistent storage and retrieval of chat conversations using Google Cloud Firestore.
Designed for Cloud Run deployment with robust error handling and graceful fallbacks.

Features:
- Save/load conversations with automatic timestamping
- Generate intelligent conversation titles from content
- List and search conversations by title or content
- Graceful fallback to session-only storage when Firestore unavailable
- User session management for multi-user support
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from google.cloud.exceptions import GoogleCloudError

from utils.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

@dataclass
class ConversationMetadata:
    """Metadata for a conversation stored in Firestore."""
    conversation_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    user_session_id: str
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings for Firestore
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['tags'] = self.tags or []
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMetadata':
        """Create from Firestore dictionary."""
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['tags'] = data.get('tags', [])
        return cls(**data)


class ConversationManager:
    """
    Manages conversation persistence using Firestore with graceful fallbacks.
    """
    
    def __init__(self):
        """Initialize conversation manager."""
        self.firestore_client = get_firestore_client()
        self.collection_name = "sql_rag_conversations"
        self.fallback_storage: Dict[str, Any] = {}  # In-memory fallback
        
    @property
    def is_persistent_storage_available(self) -> bool:
        """Check if persistent storage (Firestore) is available."""
        return self.firestore_client.is_available
    
    def _generate_conversation_id(self, user_session_id: str, timestamp: datetime) -> str:
        """
        Generate a unique conversation ID.
        
        Args:
            user_session_id: User session identifier
            timestamp: Conversation creation timestamp
            
        Returns:
            str: Unique conversation ID
        """
        # Create hash from user session and timestamp for uniqueness
        content = f"{user_session_id}_{timestamp.isoformat()}"
        hash_object = hashlib.md5(content.encode())
        return f"conv_{hash_object.hexdigest()[:12]}"
    
    def _generate_conversation_title(self, messages: List[Dict[str, Any]]) -> str:
        """
        Generate an intelligent title from conversation content.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            str: Generated conversation title
        """
        if not messages:
            return "Empty Conversation"
        
        # Find the first user message that's not too short
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '').strip()
                if len(content) > 10:  # Avoid very short messages
                    # Extract key concepts and create title
                    words = content.split()[:8]  # First 8 words
                    title = ' '.join(words)
                    
                    # Add ellipsis if truncated
                    if len(words) == 8 and len(content.split()) > 8:
                        title += "..."
                    
                    # Capitalize first letter
                    return title.capitalize()
        
        # Fallback to timestamp-based title
        now = datetime.now(timezone.utc)
        return f"Conversation {now.strftime('%Y-%m-%d %H:%M')}"
    
    def _extract_tags_from_messages(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Extract relevant tags from conversation messages.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            List[str]: Extracted tags
        """
        tags = set()
        
        for msg in messages:
            content = msg.get('content', '').lower()
            agent_type = msg.get('agent_type')
            
            # Add agent type as tag
            if agent_type:
                tags.add(f"agent:{agent_type}")
            
            # Extract SQL-related concepts
            sql_keywords = ['select', 'join', 'where', 'group by', 'order by', 'having', 'union']
            for keyword in sql_keywords:
                if keyword in content:
                    tags.add(f"sql:{keyword.replace(' ', '_')}")
            
            # Extract common database concepts
            db_concepts = ['table', 'column', 'index', 'database', 'schema', 'query', 'optimization']
            for concept in db_concepts:
                if concept in content:
                    tags.add(f"concept:{concept}")
        
        return list(tags)[:10]  # Limit to 10 tags
    
    def save_conversation(
        self, 
        messages: List[Dict[str, Any]], 
        user_session_id: str,
        conversation_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Save a conversation to persistent storage.
        
        Args:
            messages: List of conversation messages
            user_session_id: User session identifier
            conversation_id: Existing conversation ID (for updates) or None for new
            title: Custom conversation title or None for auto-generation
            
        Returns:
            Tuple[str, bool]: (conversation_id, success_flag)
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Generate or use existing conversation ID
            if not conversation_id:
                conversation_id = self._generate_conversation_id(user_session_id, now)
                is_new_conversation = True
            else:
                is_new_conversation = False
            
            # Generate title if not provided
            if not title:
                title = self._generate_conversation_title(messages)
            
            # Extract tags from content
            tags = self._extract_tags_from_messages(messages)
            
            # Create conversation data
            conversation_data = {
                'conversation_id': conversation_id,
                'title': title,
                'messages': messages,
                'user_session_id': user_session_id,
                'message_count': len(messages),
                'tags': tags,
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }
            
            # If it's an update, preserve original creation time
            if not is_new_conversation and self.is_persistent_storage_available:
                try:
                    existing_doc = self.firestore_client.client.collection(self.collection_name).document(conversation_id).get()
                    if existing_doc.exists:
                        existing_data = existing_doc.to_dict()
                        conversation_data['created_at'] = existing_data.get('created_at', now.isoformat())
                except Exception as e:
                    logger.warning(f"Could not retrieve existing conversation timestamp: {e}")
            
            # Try to save to Firestore
            if self.is_persistent_storage_available:
                try:
                    doc_ref = self.firestore_client.client.collection(self.collection_name).document(conversation_id)
                    doc_ref.set(conversation_data)
                    
                    logger.info(f"✅ Conversation saved to Firestore: {conversation_id}")
                    return conversation_id, True
                    
                except GoogleCloudError as e:
                    logger.warning(f"⚠️ Firestore save failed, using fallback: {e}")
                    # Fall through to fallback storage
                except Exception as e:
                    logger.error(f"❌ Unexpected error saving to Firestore: {e}")
                    # Fall through to fallback storage
            
            # Fallback to in-memory storage
            self.fallback_storage[conversation_id] = conversation_data
            logger.info(f"💾 Conversation saved to fallback storage: {conversation_id}")
            return conversation_id, True
            
        except Exception as e:
            logger.error(f"❌ Error saving conversation: {e}")
            return conversation_id or "error", False
    
    def load_conversation(self, conversation_id: str, user_session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a conversation from persistent storage.
        
        Args:
            conversation_id: Conversation identifier
            user_session_id: User session identifier (for security)
            
        Returns:
            Optional[Dict[str, Any]]: Conversation data or None if not found
        """
        try:
            # Try to load from Firestore first
            if self.is_persistent_storage_available:
                try:
                    doc_ref = self.firestore_client.client.collection(self.collection_name).document(conversation_id)
                    doc = doc_ref.get()
                    
                    if doc.exists:
                        data = doc.to_dict()
                        
                        # Verify user session for security
                        if data.get('user_session_id') != user_session_id:
                            logger.warning(f"⚠️ User session mismatch for conversation {conversation_id}")
                            return None
                        
                        logger.info(f"✅ Conversation loaded from Firestore: {conversation_id}")
                        return data
                        
                except GoogleCloudError as e:
                    logger.warning(f"⚠️ Firestore load failed, checking fallback: {e}")
                    # Fall through to fallback storage
                except Exception as e:
                    logger.error(f"❌ Unexpected error loading from Firestore: {e}")
                    # Fall through to fallback storage
            
            # Try fallback storage
            if conversation_id in self.fallback_storage:
                data = self.fallback_storage[conversation_id]
                
                # Verify user session for security
                if data.get('user_session_id') != user_session_id:
                    logger.warning(f"⚠️ User session mismatch for conversation {conversation_id} (fallback)")
                    return None
                
                logger.info(f"💾 Conversation loaded from fallback storage: {conversation_id}")
                return data
            
            logger.info(f"🔍 Conversation not found: {conversation_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error loading conversation {conversation_id}: {e}")
            return None
    
    def list_conversations(
        self, 
        user_session_id: str, 
        limit: int = 50,
        search_term: Optional[str] = None
    ) -> List[ConversationMetadata]:
        """
        List conversations for a user session.
        
        Args:
            user_session_id: User session identifier
            limit: Maximum number of conversations to return
            search_term: Optional search term for filtering
            
        Returns:
            List[ConversationMetadata]: List of conversation metadata
        """
        conversations = []
        
        try:
            # Try to load from Firestore first
            if self.is_persistent_storage_available:
                try:
                    query = self.firestore_client.client.collection(self.collection_name)\
                                  .where('user_session_id', '==', user_session_id)\
                                  .order_by('updated_at', direction='DESCENDING')\
                                  .limit(limit)
                    
                    docs = query.stream()
                    
                    for doc in docs:
                        data = doc.to_dict()
                        
                        # Apply search filter if provided
                        if search_term:
                            search_lower = search_term.lower()
                            title_match = search_lower in data.get('title', '').lower()
                            tag_match = any(search_lower in tag.lower() for tag in data.get('tags', []))
                            
                            if not (title_match or tag_match):
                                continue
                        
                        # Convert to metadata object
                        metadata = ConversationMetadata(
                            conversation_id=data['conversation_id'],
                            title=data['title'],
                            created_at=datetime.fromisoformat(data['created_at']),
                            updated_at=datetime.fromisoformat(data['updated_at']),
                            message_count=data['message_count'],
                            user_session_id=data['user_session_id'],
                            tags=data.get('tags', [])
                        )
                        conversations.append(metadata)
                    
                    logger.info(f"✅ Loaded {len(conversations)} conversations from Firestore")
                    return conversations
                    
                except GoogleCloudError as e:
                    logger.warning(f"⚠️ Firestore list failed, checking fallback: {e}")
                    # Fall through to fallback storage
                except Exception as e:
                    logger.error(f"❌ Unexpected error listing from Firestore: {e}")
                    # Fall through to fallback storage
            
            # Try fallback storage
            for conv_id, data in self.fallback_storage.items():
                if data.get('user_session_id') != user_session_id:
                    continue
                
                # Apply search filter if provided
                if search_term:
                    search_lower = search_term.lower()
                    title_match = search_lower in data.get('title', '').lower()
                    tag_match = any(search_lower in tag.lower() for tag in data.get('tags', []))
                    
                    if not (title_match or tag_match):
                        continue
                
                # Convert to metadata object
                metadata = ConversationMetadata(
                    conversation_id=data['conversation_id'],
                    title=data['title'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    updated_at=datetime.fromisoformat(data['updated_at']),
                    message_count=data['message_count'],
                    user_session_id=data['user_session_id'],
                    tags=data.get('tags', [])
                )
                conversations.append(metadata)
            
            # Sort by updated_at descending
            conversations.sort(key=lambda x: x.updated_at, reverse=True)
            
            # Apply limit
            conversations = conversations[:limit]
            
            logger.info(f"💾 Loaded {len(conversations)} conversations from fallback storage")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error listing conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str, user_session_id: str) -> bool:
        """
        Delete a conversation from persistent storage.
        
        Args:
            conversation_id: Conversation identifier
            user_session_id: User session identifier (for security)
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            deleted_from_persistent = False
            deleted_from_fallback = False
            
            # Try to delete from Firestore
            if self.is_persistent_storage_available:
                try:
                    doc_ref = self.firestore_client.client.collection(self.collection_name).document(conversation_id)
                    doc = doc_ref.get()
                    
                    if doc.exists:
                        data = doc.to_dict()
                        
                        # Verify user session for security
                        if data.get('user_session_id') != user_session_id:
                            logger.warning(f"⚠️ User session mismatch for deletion {conversation_id}")
                            return False
                        
                        doc_ref.delete()
                        deleted_from_persistent = True
                        logger.info(f"✅ Conversation deleted from Firestore: {conversation_id}")
                        
                except GoogleCloudError as e:
                    logger.warning(f"⚠️ Firestore delete failed: {e}")
                except Exception as e:
                    logger.error(f"❌ Unexpected error deleting from Firestore: {e}")
            
            # Try to delete from fallback storage
            if conversation_id in self.fallback_storage:
                data = self.fallback_storage[conversation_id]
                
                # Verify user session for security
                if data.get('user_session_id') == user_session_id:
                    del self.fallback_storage[conversation_id]
                    deleted_from_fallback = True
                    logger.info(f"💾 Conversation deleted from fallback storage: {conversation_id}")
            
            return deleted_from_persistent or deleted_from_fallback
            
        except Exception as e:
            logger.error(f"❌ Error deleting conversation {conversation_id}: {e}")
            return False
    
    def get_storage_status(self) -> Dict[str, Any]:
        """
        Get status information about the storage system.
        
        Returns:
            Dict[str, Any]: Storage status information
        """
        status = {
            'firestore_available': self.is_persistent_storage_available,
            'fallback_conversations': len(self.fallback_storage),
            'storage_mode': 'persistent' if self.is_persistent_storage_available else 'fallback'
        }
        
        if self.is_persistent_storage_available:
            firestore_status = self.firestore_client.test_connection()
            status.update(firestore_status)
        
        return status


# Global conversation manager instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """
    Get the global conversation manager instance (singleton pattern).
    
    Returns:
        ConversationManager: Shared conversation manager instance
    """
    global _conversation_manager
    
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
        
    return _conversation_manager


if __name__ == "__main__":
    """Test script for ConversationManager functionality."""
    import time
    
    print("🧪 Testing ConversationManager...")
    
    # Initialize manager
    manager = get_conversation_manager()
    
    # Test storage status
    status = manager.get_storage_status()
    print(f"Storage status: {status}")
    
    # Test conversation operations
    test_user_session = "test_user_123"
    test_messages = [
        {'role': 'user', 'content': 'How do I optimize SQL queries?', 'agent_type': None},
        {'role': 'assistant', 'content': 'Here are some SQL optimization techniques...', 'agent_type': None}
    ]
    
    # Save conversation
    conv_id, success = manager.save_conversation(test_messages, test_user_session)
    print(f"Save conversation: {success} (ID: {conv_id})")
    
    # Load conversation
    loaded_conv = manager.load_conversation(conv_id, test_user_session)
    print(f"Load conversation: {'✅' if loaded_conv else '❌'}")
    
    # List conversations
    conversations = manager.list_conversations(test_user_session)
    print(f"List conversations: {len(conversations)} found")
    
    # Delete conversation
    deleted = manager.delete_conversation(conv_id, test_user_session)
    print(f"Delete conversation: {'✅' if deleted else '❌'}")
    
    print("🎉 ConversationManager test completed!")