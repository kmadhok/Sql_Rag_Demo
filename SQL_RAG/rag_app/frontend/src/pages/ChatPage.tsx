import React, { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { sendMessage, setAgentType, addStreamingMessage } from '../store/chatSlice';
import { AgentType } from '../types/api';
import { Message } from '../types/chat';
import { AgentSelector } from '../components/chat/AgentSelector';
import { MessageBubble } from '../components/chat/MessageBubble';
import { useWebSocket } from '../hooks/useWebSocket';
import { useLocalStorage } from '../hooks/useLocalStorage';
import '../styles/ChatPage.css';

const ChatPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const [inputMessage, setInputMessage] = useState('');
  const [sessionId] = useLocalStorage('sql-rag-session', () => crypto.randomUUID());
  
  const { 
    conversations, 
    agentType, 
    isLoading 
  } = useSelector((state: RootState) => state.chat);
  
  const { sendWebSocketMessage, isConnected } = useWebSocket(
    `ws://localhost:8000/ws/chat/${sessionId}`
  );
  
  const currentConversation = conversations[sessionId];
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);
  
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;
    
    // Add user message immediately
    const userMessage: Message = {
      id: crypto.randomUUID(),
      content: inputMessage,
      role: 'user',
      timestamp: new Date(),
    };
    
    dispatch(addStreamingMessage({
      sessionId,
      message: userMessage,
    }));
    
    const messagePayload = {
      message: inputMessage,
      agentType,
      sessionId,
      stream: true,
    };
    
    if (isConnected) {
      sendWebSocketMessage(messagePayload);
    } else {
      dispatch(sendMessage(messagePayload));
    }
    
    setInputMessage('');
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  const messages = currentConversation?.messages || [];
  
  return (
    <div className="chat-page">
      <div className="chat-header">
        <h1>💬 SQL RAG Chat</h1>
        <div className="connection-status">
          {isConnected ? (
            <span className="status-connected">🟢 Connected</span>
          ) : (
            <span className="status-disconnected">🔴 Disconnected</span>
          )}
        </div>
      </div>
      
      <div className="chat-controls">
        <AgentSelector 
          selectedAgent={agentType}
          onAgentChange={(agent) => dispatch(setAgentType(agent))}
        />
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h3>👋 Welcome to SQL RAG!</h3>
            <p>Ask me anything about your data. I can help you:</p>
            <ul>
              <li>📊 Generate SQL queries with @create</li>
              <li>📖 Explain complex queries with @explain</li>
              <li>🗂️ Browse database schema with @schema</li>
              <li>💬 Get detailed answers with @longanswer</li>
            </ul>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              isStreaming={message.isStreaming}
            />
          ))
        )}
        
        {isLoading && (
          <div className="typing-indicator">
            <span>🤔 Thinking...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input-container">
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question about your data (use @create, @explain, @schema for special agents)..."
          className="chat-input"
          rows={3}
          disabled={isLoading}
        />
        <button
          onClick={handleSendMessage}
          disabled={isLoading || !inputMessage.trim()}
          className="send-button"
        >
          {isLoading ? '⏳' : '🚀'} Send
        </button>
      </div>
    </div>
  );
};

export default ChatPage;