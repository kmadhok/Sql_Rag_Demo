import { useState } from 'react';

/**
 * Query History Panel Component
 * Displays recently executed queries with ability to reload them
 */
export default function QueryHistoryPanel({ history, onLoadQuery, onClearHistory, isVisible, onToggle }) {
  const [searchTerm, setSearchTerm] = useState('');

  if (!isVisible) return null;

  const filteredHistory = history.filter(item =>
    item.sql.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatTimestamp = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hour${Math.floor(diffMins / 60) > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  const truncateSql = (sql, maxLength = 80) => {
    if (sql.length <= maxLength) return sql;
    return sql.substring(0, maxLength) + '...';
  };

  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <h3 style={styles.title}>Query History</h3>
        <div style={styles.headerButtons}>
          <button
            onClick={onClearHistory}
            style={styles.clearButton}
            disabled={history.length === 0}
            title="Clear all history"
          >
            Clear
          </button>
          <button
            onClick={onToggle}
            style={styles.closeButton}
            aria-label="Close history panel"
          >
            ×
          </button>
        </div>
      </div>

      {/* Search */}
      <div style={styles.searchContainer}>
        <input
          type="text"
          placeholder="🔍 Search history..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={styles.searchInput}
        />
      </div>

      {/* History List */}
      <div style={styles.historyList}>
        {filteredHistory.length === 0 ? (
          <div style={styles.emptyState}>
            <p style={styles.emptyText}>
              {history.length === 0
                ? 'No queries executed yet'
                : 'No queries match your search'}
            </p>
          </div>
        ) : (
          filteredHistory.map((item) => (
            <div
              key={item.id}
              style={styles.historyItem}
              onClick={() => onLoadQuery(item.sql)}
            >
              <div style={styles.itemHeader}>
                <span style={styles.statusIcon}>
                  {item.success ? '✓' : '✗'}
                </span>
                <span style={styles.timestamp}>
                  {formatTimestamp(item.timestamp)}
                </span>
              </div>
              <div style={styles.sqlPreview}>
                {truncateSql(item.sql)}
              </div>
              {item.success && item.rowCount !== undefined && (
                <div style={styles.metadata}>
                  {item.rowCount} row{item.rowCount !== 1 ? 's' : ''}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const styles = {
  panel: {
    width: '320px',
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
  headerButtons: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
  },
  clearButton: {
    padding: '0.25rem 0.75rem',
    fontSize: '0.85rem',
    backgroundColor: 'var(--surface-border)',
    color: 'var(--text-color)',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.2s',
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
  searchContainer: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid var(--surface-border)',
  },
  searchInput: {
    width: '100%',
    padding: '0.5rem',
    fontSize: '0.9rem',
    backgroundColor: 'var(--surface-section)',
    color: 'var(--text-color)',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    outline: 'none',
  },
  historyList: {
    flex: 1,
    overflow: 'auto',
    padding: '0.5rem',
  },
  emptyState: {
    textAlign: 'center',
    padding: '2rem 1rem',
  },
  emptyText: {
    color: 'var(--text-color-secondary)',
    fontSize: '0.9rem',
  },
  historyItem: {
    padding: '0.75rem',
    marginBottom: '0.5rem',
    backgroundColor: 'var(--surface-section)',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  itemHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.5rem',
  },
  statusIcon: {
    fontSize: '1rem',
    fontWeight: 'bold',
  },
  timestamp: {
    fontSize: '0.75rem',
    color: 'var(--text-color-secondary)',
  },
  sqlPreview: {
    fontSize: '0.85rem',
    fontFamily: 'monospace',
    color: 'var(--text-color)',
    marginBottom: '0.25rem',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  metadata: {
    fontSize: '0.75rem',
    color: 'var(--text-color-secondary)',
  },
};
