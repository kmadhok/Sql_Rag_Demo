import React, { useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../../store';
import { sendMessage, addMessage, clearMessages } from '../../store/chatSlice';
import { AgentType } from '../../types/api';
import MessageBubble from './MessageBubble';
import LoadingSpinner from '../common/LoadingSpinner';
import './ChatInterface.css';

const ChatInterface: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { messages, isLoading, agentType, currentSessionId } = useSelector(
    (state: RootState) => state.chat
  );
  const [inputMessage, setInputMessage] = React.useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      content: inputMessage,
      role: 'user' as const,
      timestamp: new Date(),
    };

    dispatch(addMessage(userMessage));
    setInputMessage('');

    try {
      await dispatch(sendMessage({
        message: inputMessage,
        agentType: agentType as AgentType,
        sessionId: currentSessionId || undefined,
      }));
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleClearChat = () => {
    dispatch(clearMessages());
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>SQL RAG Assistant</h2>
        <div className="chat-controls">
          <button 
            onClick={handleClearChat}
            className="clear-chat-btn"
            disabled={messages.length === 0}
          >
            Clear Chat
          </button>
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h3>Welcome to SQL RAG Assistant! 🐕</h3>
            <p>Ask me anything about your database. I can help you with:</p>
            <ul>
              <li>Writing SQL queries</li>
              <li>Explaining database schemas</li>
              <li>Analyzing query results</li>
              <li>Creating complex joins</li>
            </ul>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && <LoadingSpinner message="Thinking..." />}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSendMessage} className="input-form">
        <div className="input-container">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask me about your database..."
            rows={3}
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e);
              }
            }}
          />
          <button 
            type="submit" 
            disabled={!inputMessage.trim() || isLoading}
            className="send-button"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;