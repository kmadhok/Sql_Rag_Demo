import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { RootState, AppDispatch } from '../store';
import { sendMessage, setAgentType } from '../store/chatSlice';
import { AgentType } from '../types/api';
import AgentSelector from '../components/chat/AgentSelector';
import MessageBubble from '../components/chat/MessageBubble';
import '../styles/ChatPage.css';

const ChatPage: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const { messages, isLoading, agentType } = useSelector((state: RootState) => state.chat);
  const [inputMessage, setInputMessage] = useState('');

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    try {
      await dispatch(sendMessage({
        message: inputMessage,
        agentType: (agentType as AgentType) || AgentType.NORMAL,
      }));
      setInputMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-interface">
        <div className="chat-header">
          <h2>SQL RAG Assistant</h2>
          <div className="chat-controls">
            <AgentSelector />
          </div>
        </div>

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h3>Welcome to SQL RAG Assistant! 🐕</h3>
              <p>Ask me anything about your database.</p>
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))
          )}
          {isLoading && <div className="loading-message">Thinking...</div>}
        </div>

        <form onSubmit={handleSendMessage} className="input-form">
          <div className="input-container">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask me about your database..."
              rows={3}
              disabled={isLoading}
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
    </div>
  );
};

export default ChatPage;