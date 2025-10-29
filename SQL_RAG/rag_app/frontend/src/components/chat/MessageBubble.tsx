import React from 'react';
import { Message } from '../../types/api';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const formatDate = (timestamp: Date | string): string => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const isUser = message.role === 'user';
  const hasSQL = message.sqlQuery && message.sqlQuery.trim();
 const hasResults = message.sqlResult;

  const styles = {
    messageBubble: {
      display: 'flex',
      flexDirection: 'column' as const,
      marginBottom: '16px',
      alignItems: isUser ? 'flex-end' : 'flex-start'
    },
    messageContent: {
      backgroundColor: isUser ? '#007bff' : '#f8f9fa',
      color: isUser ? 'white' : '#333',
      padding: '12px 16px',
      borderRadius: '12px',
      maxWidth: '70%',
      wordBreak: 'break-word' as const
    },
    messageText: {
      marginBottom: '8px',
      lineHeight: '1.4'
    },
    sqlSection: {
      marginTop: '12px',
      borderTop: `1px solid ${isUser ? 'rgba(255,255,255,0.3)' : '#ddd'}`,
      paddingTop: '12px'
    },
    sqlCode: {
      backgroundColor: isUser ? 'rgba(255,255,255,0.1)' : '#f4f4f4',
      padding: '8px',
      borderRadius: '4px',
      fontSize: '12px',
      overflowX: 'auto' as const,
      whiteSpace: 'pre-wrap' as const
    },
    sqlResults: {
      marginTop: '8px'
    },
    resultData: {
      backgroundColor: isUser ? 'rgba(255,255,255,0.1)' : '#f9f9f9',
      padding: '8px',
      borderRadius: '4px',
      fontSize: '11px',
      maxHeight: '200px',
      overflow: 'auto' as const
    },
    tokenUsage: {
      marginTop: '8px',
      opacity: 0.8
    },
    messageMeta: {
      fontSize: '12px',
      opacity: 0.6,
      marginTop: '4px',
      display: 'flex',
      gap: '8px',
      alignItems: 'center',
      justifyContent: isUser ? 'flex-end' : 'flex-start'
    },
    agentBadge: {
      backgroundColor: isUser ? 'rgba(255,255,255,0.2)' : '#007bff',
      color: isUser ? 'white' : 'white',
      padding: '2px 6px',
      borderRadius: '10px',
      fontSize: '10px'
    }
  };

  return (
    <div style={styles.messageBubble}>
      <div style={styles.messageContent}>
        <div style={styles.messageText}>
          {message.content}
        </div>
        
        {hasSQL && (
          <div style={styles.sqlSection}>
            <div>
              <strong>Generated SQL:</strong>
            </div>
            <pre style={styles.sqlCode}>
              <code>{message.sqlQuery}</code>
            </pre>
            
            {hasResults && (
              <div style={styles.sqlResults}>
                <strong>Results:</strong>
                <pre style={styles.resultData}>
                  {JSON.stringify(message.sqlResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
        
        {message.tokenUsage && (
          <div style={styles.tokenUsage}>
            <small>
              Tokens: {message.tokenUsage.prompt} + {message.tokenUsage.completion} = {message.tokenUsage.total}
            </small>
          </div>
        )}
      </div>
      
      <div style={styles.messageMeta}>
        <span>{formatDate(message.timestamp)}</span>
        {message.agentUsed && (
          <span style={styles.agentBadge}>{message.agentUsed}</span>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;