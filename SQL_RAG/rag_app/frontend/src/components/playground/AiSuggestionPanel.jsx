import { useEffect, useMemo, useRef, useState } from 'react';

export default function AiSuggestionPanel({
  explanation,
  suggestions,
  isLoading,
  onClose,
  initialTab = 'explain',
  onTabChange,
  chatMessages = [],
  onSendChat,
  isChatLoading = false,
  chatError = null
}) {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [chatInput, setChatInput] = useState('');
  const [localError, setLocalError] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    if (activeTab === 'chat') {
      setLocalError(null);
    }
  }, [activeTab]);

  const handleTabSelect = (tab) => {
    setActiveTab(tab);
    if (onTabChange) {
      onTabChange(tab);
    }
  };

  const handleChatSubmit = async (event) => {
    event.preventDefault();
    if (!onSendChat) {
      return;
    }

    const trimmed = chatInput.trim();
    if (!trimmed) {
      setLocalError('Type a message to start chatting.');
      return;
    }

    try {
      setLocalError(null);
      await onSendChat(trimmed);
      setChatInput('');
    } catch (error) {
      setLocalError(error.message || 'Failed to send message.');
    }
  };

  const renderedMessages = useMemo(() => {
    if (!chatMessages || chatMessages.length === 0) {
      return null;
    }

    return [
      ...chatMessages.map((message) => (
        <div
          key={message.id}
          style={{
            ...styles.chatMessage,
            ...(message.role === 'assistant' ? styles.chatMessageAssistant : styles.chatMessageUser),
          }}
        >
          <div style={styles.chatMessageRole}>
            {message.role === 'assistant' ? 'Assistant' : 'You'}
          </div>
          <div style={styles.chatMessageContent}>{message.content}</div>
        </div>
      )),
      <div key="chat-end-marker" ref={messagesEndRef} />,
    ];
  }, [chatMessages]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isChatLoading]);

  return (
    <div className="ai-panel" style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <h3 style={styles.title}>AI Assistant</h3>
        <button
          onClick={onClose}
          style={styles.closeButton}
          aria-label="Close AI panel"
        >
          ×
        </button>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        <button
          className={activeTab === 'explain' ? 'tab-active' : 'tab-inactive'}
          style={{
            ...styles.tab,
            ...(activeTab === 'explain' ? styles.tabActive : styles.tabInactive)
          }}
          onClick={() => handleTabSelect('explain')}
        >
          Explanation
        </button>
        <button
          className={activeTab === 'suggestions' ? 'tab-active' : 'tab-inactive'}
          style={{
            ...styles.tab,
            ...(activeTab === 'suggestions' ? styles.tabActive : styles.tabInactive)
          }}
          onClick={() => handleTabSelect('suggestions')}
        >
          Suggestions
        </button>
        <button
          className={activeTab === 'chat' ? 'tab-active' : 'tab-inactive'}
          style={{
            ...styles.tab,
            ...(activeTab === 'chat' ? styles.tabActive : styles.tabInactive)
          }}
          onClick={() => handleTabSelect('chat')}
        >
          Chat
        </button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {isLoading && activeTab !== 'chat' ? (
          <div style={styles.loadingContainer}>
            <div style={styles.spinner}></div>
            <p style={styles.loadingText}>AI is thinking...</p>
          </div>
        ) : (
          <>
            {activeTab === 'explain' && (
              <div style={styles.explanationTab}>
                {explanation ? (
                  <div style={styles.explanationText}>
                    {explanation}
                  </div>
                ) : (
                  <div style={styles.emptyState}>
                    <p>💡 Select SQL and click "Explain with AI" to get insights</p>
                  </div>
                )}
              </div>
            )}
            {activeTab === 'suggestions' && (
              <div style={styles.suggestionsTab}>
                {suggestions && suggestions.length > 0 ? (
                  <div style={styles.suggestionsList}>
                    {suggestions.map((s, idx) => (
                      <div key={idx} style={styles.suggestionItem}>
                        <code style={styles.suggestionCode}>{s.completion}</code>
                        <p style={styles.suggestionExplanation}>{s.explanation}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={styles.emptyState}>
                    <p>💡 AI suggestions will appear here during autocomplete</p>
                  </div>
                )}
              </div>
            )}
            {activeTab === 'chat' && (
              <div style={styles.chatTab}>
                <div style={styles.chatMessagesContainer}>
                  {renderedMessages || (
                    <div style={styles.emptyState}>
                      <p>💬 Ask a question about your SQL to get started.</p>
                    </div>
                  )}
                  {isChatLoading && (
                    <div style={styles.chatLoader}>
                      <div style={styles.spinnerSmall}></div>
                      <span style={styles.loadingText}>Assistant is typing…</span>
                    </div>
                  )}
                </div>

                {(localError || chatError) && (
                  <div style={styles.chatError}>{localError || chatError}</div>
                )}

                <form style={styles.chatComposer} onSubmit={handleChatSubmit}>
                  <textarea
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    placeholder="Ask a question about this SQL..."
                    style={styles.chatTextarea}
                    rows={2}
                    disabled={isChatLoading}
                  />
                  <button
                    type="submit"
                    style={{
                      ...styles.chatSendButton,
                      opacity: isChatLoading ? 0.6 : 1,
                      cursor: isChatLoading ? 'not-allowed' : 'pointer'
                    }}
                    disabled={isChatLoading}
                  >
                    {isChatLoading ? 'Sending…' : 'Send'}
                  </button>
                </form>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  panel: {
    width: '350px',
    height: '100%',
    backgroundColor: 'var(--surface-ground)',
    border: '1px solid var(--surface-border)',
    borderRadius: '6px',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1rem',
    borderBottom: '1px solid var(--surface-border)',
    backgroundColor: 'var(--surface-section)',
  },
  title: {
    margin: 0,
    fontSize: '1.1rem',
    fontWeight: '600',
    color: 'var(--text-color)',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '1.5rem',
    cursor: 'pointer',
    color: 'var(--text-color-secondary)',
    padding: '0 0.5rem',
    lineHeight: '1',
    transition: 'color 0.2s',
  },
  tabs: {
    display: 'flex',
    gap: '0.5rem',
    padding: '0.75rem 1rem 0 1rem',
    borderBottom: '1px solid var(--surface-border)',
    backgroundColor: 'var(--surface-section)',
  },
  tab: {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px 4px 0 0',
    cursor: 'pointer',
    fontSize: '0.9rem',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  tabActive: {
    backgroundColor: 'var(--surface-ground)',
    color: 'var(--primary-color)',
    borderBottom: '2px solid var(--primary-color)',
  },
  tabInactive: {
    backgroundColor: 'transparent',
    color: 'var(--text-color-secondary)',
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '1rem',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '4px solid var(--surface-border)',
    borderTop: '4px solid var(--primary-color)',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  spinnerSmall: {
    width: '18px',
    height: '18px',
    border: '3px solid var(--surface-border)',
    borderTop: '3px solid var(--primary-color)',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    marginTop: '1rem',
    color: 'var(--text-color-secondary)',
    fontSize: '0.9rem',
  },
  explanationTab: {
    lineHeight: '1.6',
  },
  explanationText: {
    whiteSpace: 'pre-wrap',
    color: 'var(--text-color)',
    fontSize: '0.95rem',
  },
  suggestionsTab: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  suggestionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  suggestionItem: {
    padding: '0.75rem',
    backgroundColor: 'var(--surface-section)',
    borderRadius: '4px',
    border: '1px solid var(--surface-border)',
  },
  suggestionCode: {
    display: 'block',
    padding: '0.5rem',
    backgroundColor: 'var(--surface-ground)',
    borderRadius: '3px',
    fontSize: '0.85rem',
    fontFamily: 'monospace',
    marginBottom: '0.5rem',
    color: 'var(--primary-color)',
  },
  suggestionExplanation: {
    margin: 0,
    fontSize: '0.85rem',
    color: 'var(--text-color-secondary)',
    lineHeight: '1.4',
  },
  emptyState: {
    textAlign: 'center',
    padding: '2rem 1rem',
    color: 'var(--text-color-secondary)',
  },
  chatTab: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    gap: '0.75rem',
  },
  chatMessagesContainer: {
    flex: 1,
    minHeight: '0',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  chatMessage: {
    padding: '0.75rem',
    borderRadius: '6px',
    border: '1px solid var(--surface-border)',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  chatMessageUser: {
    alignSelf: 'flex-end',
    backgroundColor: 'rgba(79, 70, 229, 0.15)',
    borderColor: 'rgba(79, 70, 229, 0.35)',
    maxWidth: '90%',
  },
  chatMessageAssistant: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(17, 94, 89, 0.15)',
    borderColor: 'rgba(17, 94, 89, 0.35)',
    maxWidth: '90%',
  },
  chatMessageRole: {
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--text-color-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  chatMessageContent: {
    fontSize: '0.9rem',
    color: 'var(--text-color)',
    lineHeight: 1.5,
  },
  chatLoader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 0.75rem',
    backgroundColor: 'var(--surface-section)',
    borderRadius: '4px',
    alignSelf: 'flex-start',
  },
  chatError: {
    padding: '0.5rem 0.75rem',
    borderRadius: '4px',
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    border: '1px solid rgba(239, 68, 68, 0.35)',
    color: 'rgb(248, 113, 113)',
    fontSize: '0.85rem',
  },
  chatComposer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  chatTextarea: {
    width: '100%',
    padding: '0.75rem',
    borderRadius: '6px',
    border: '1px solid var(--surface-border)',
    backgroundColor: 'var(--surface-ground)',
    color: 'var(--text-color)',
    fontSize: '0.9rem',
    resize: 'none',
    fontFamily: 'inherit',
  },
  chatSendButton: {
    alignSelf: 'flex-end',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    border: 'none',
    backgroundColor: 'var(--primary-color)',
    color: 'white',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'opacity 0.2s ease',
  },
};

// Add keyframe animation for spinner
const styleSheet = document.createElement("style");
styleSheet.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);
