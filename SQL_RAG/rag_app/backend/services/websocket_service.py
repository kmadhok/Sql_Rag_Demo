# WebSocket service for real-time chat communication

import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self):
        # Store active connections by session ID
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        
        # Add to active connections
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        
        self.active_connections[session_id].append(websocket)
        
        # Store connection metadata
        connection_id = f"{session_id}_{len(self.active_connections[session_id])}_{datetime.now().timestamp()}"
        self.connection_metadata[connection_id] = {
            "websocket": websocket,
            "session_id": session_id,
            "connected_at": datetime.now().isoformat(),
            "messages_sent": 0,
            "last_activity": datetime.now().isoformat()
        }
        
        logger.info(f"WebSocket connected for session {session_id} (connections: {len(self.active_connections[session_id])})")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "data": {
                "status": "connected",
                "session_id": session_id,
                "message": "Connected to SQL RAG chat",
                "timestamp": datetime.now().isoformat()
            }
        }, websocket)
    
    async def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            try:
                self.active_connections[session_id].remove(websocket)
                
                # Clean up empty session
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                    
                    # Clean up metadata
                    keys_to_remove = [
                        key for key, metadata in self.connection_metadata.items()
                        if metadata.get("session_id") == session_id
                    ]
                    for key in keys_to_remove:
                        del self.connection_metadata[key]
                
                logger.info(f"WebSocket disconnected for session {session_id}")
                
            except ValueError:
                # Connection not found in list
                logger.warning(f"WebSocket disconnect: connection not found for session {session_id}")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send message to specific WebSocket client"""
        try:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()
            
            await websocket.send_text(json.dumps(message))
            
            # Update metadata
            for connection_id, metadata in self.connection_metadata.items():
                if metadata.get("websocket") == websocket:
                    metadata["messages_sent"] += 1
                    metadata["last_activity"] = datetime.now().isoformat()
                    break
                    
        except Exception as e:
            logger.error(f"Error sending personal message: {str(e)}")
            # Connection might be dead, try to clean up
            await self.cleanup_dead_connection(websocket)
    
    async def broadcast_to_session(self, message: Dict, session_id: str):
        """Broadcast message to all connections in a session"""
        if session_id not in self.active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        disconnected_connections = []
        
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_text(json.dumps(message))
                
                # Update metadata
                for connection_id, metadata in self.connection_metadata.items():
                    if metadata.get("websocket") == connection:
                        metadata["messages_sent"] += 1
                        metadata["last_activity"] = datetime.now().isoformat()
                        break
                        
            except Exception as e:
                logger.error(f"Error broadcasting to connection in session {session_id}: {str(e)}")
                disconnected_connections.append(connection)
        
        # Clean up dead connections
        for dead_connection in disconnected_connections:
            await self.disconnect(dead_connection, session_id)
    
    async def send_status_update(self, session_id: str, status: str, details: Dict = None):
        """Send status update to session"""
        message = {
            "type": "status",
            "data": {
                "status": status,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await self.broadcast_to_session(message, session_id)
    
    async def send_streaming_response(self, session_id: str, response_data: Dict):
        """Send streaming response (for real-time AI responses)"""
        message = {
            "type": "response",
            "data": response_data
        }
        
        await self.broadcast_to_session(message, session_id)
    
    async def send_error(self, session_id: str, error_message: str, error_type: str = "general"):
        """Send error message to session"""
        message = {
            "type": "error",
            "data": {
                "error": error_message,
                "error_type": error_type,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await self.broadcast_to_session(message, session_id)
    
    def get_session_connection_count(self, session_id: str) -> int:
        """Get number of active connections for a session"""
        return len(self.active_connections.get(session_id, []))
    
    def get_active_sessions(self) -> List[str]:
        """Get list of all active session IDs"""
        return list(self.active_connections.keys())
    
    def get_connection_stats(self) -> Dict:
        """Get overall connection statistics"""
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        
        return {
            "total_connections": total_connections,
            "active_sessions": len(self.active_connections),
            "session_details": {
                session_id: len(connections)
                for session_id, connections in self.active_connections.items()
            },
            "total_metadata_entries": len(self.connection_metadata)
        }
    
    async def cleanup_dead_connection(self, websocket: WebSocket):
        """Clean up dead connection"""
        # Find and remove the connection from all sessions
        for session_id, connections in list(self.active_connections.items()):
            if websocket in connections:
                await self.disconnect(websocket, session_id)
                break
    
    async def disconnect_all(self):
        """Disconnect all active connections (for shutdown)"""
        for session_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")
        
        self.active_connections.clear()
        self.connection_metadata.clear()
        logger.info("All WebSocket connections disconnected")
    
    async def ping_all_connections(self):
        """Ping all connections to check they're alive"""
        dead_connections = []
        
        for session_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    ping_message = {
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    }
                    await connection.send_text(json.dumps(ping_message))
                except Exception as e:
                    logger.warning(f"Ping failed for connection in session {session_id}: {str(e)}")
                    dead_connections.append((session_id, connection))
        
        # Clean up dead connections
        for session_id, dead_connection in dead_connections:
            await self.disconnect(dead_connection, session_id)
        
        return {
            "pinged_sessions": len(self.active_connections),
            "dead_connections_removed": len(dead_connections),
            "active_connections": len(self.active_connections)
        }

# Global instance for the application
websocket_manager = WebSocketManager()