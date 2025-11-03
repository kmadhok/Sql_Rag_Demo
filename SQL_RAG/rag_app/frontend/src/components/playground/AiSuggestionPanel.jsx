import { useState } from 'react';

export default function AiSuggestionPanel({
  explanation,
  suggestions,
  isLoading,
  onClose
}) {
  const [activeTab, setActiveTab] = useState('explain');

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
          onClick={() => setActiveTab('explain')}
        >
          Explanation
        </button>
        <button
          className={activeTab === 'suggestions' ? 'tab-active' : 'tab-inactive'}
          style={{
            ...styles.tab,
            ...(activeTab === 'suggestions' ? styles.tabActive : styles.tabInactive)
          }}
          onClick={() => setActiveTab('suggestions')}
        >
          Suggestions
        </button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {isLoading ? (
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
