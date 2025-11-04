import { useState } from 'react';

/**
 * Query Tabs Component
 * Manages multiple query tabs like browser tabs
 * Double-click tab name to rename
 */
export default function QueryTabs({ tabs, activeTabId, onTabChange, onTabClose, onTabAdd, onTabRename }) {
  const [editingTabId, setEditingTabId] = useState(null);
  const [editingName, setEditingName] = useState('');

  const startEditing = (tab) => {
    setEditingTabId(tab.id);
    setEditingName(tab.name);
  };

  const saveEdit = (tabId) => {
    const newName = editingName.trim();
    if (newName && newName !== tabs.find(t => t.id === tabId)?.name) {
      onTabRename(tabId, newName);
    }
    setEditingTabId(null);
    setEditingName('');
  };

  const cancelEdit = () => {
    setEditingTabId(null);
    setEditingName('');
  };

  const handleKeyDown = (e, tabId) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit(tabId);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEdit();
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.tabsWrapper}>
        {tabs.map((tab) => (
          <div
            key={tab.id}
            style={{
              ...styles.tab,
              ...(tab.id === activeTabId ? styles.tabActive : styles.tabInactive),
            }}
            onClick={() => editingTabId !== tab.id && onTabChange(tab.id)}
          >
            {editingTabId === tab.id ? (
              <input
                type="text"
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, tab.id)}
                onBlur={() => saveEdit(tab.id)}
                onClick={(e) => e.stopPropagation()}
                style={styles.tabInput}
                autoFocus
              />
            ) : (
              <span
                style={styles.tabName}
                onDoubleClick={() => startEditing(tab)}
                title="Double-click to rename"
              >
                {tab.name}
              </span>
            )}
            {tabs.length > 1 && (
              <button
                style={styles.closeButton}
                onClick={(e) => {
                  e.stopPropagation();
                  onTabClose(tab.id);
                }}
                aria-label={`Close ${tab.name}`}
                title="Close tab"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <button
          style={styles.addButton}
          onClick={onTabAdd}
          aria-label="Add new tab"
          title="Add new tab"
        >
          +
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    borderBottom: '1px solid var(--surface-border)',
    backgroundColor: 'var(--surface-section)',
  },
  tabsWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '0.5rem 1rem',
    overflowX: 'auto',
    overflowY: 'hidden',
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.5rem 1rem',
    borderRadius: '6px 6px 0 0',
    cursor: 'pointer',
    fontSize: '0.9rem',
    fontWeight: '500',
    transition: 'all 0.2s',
    border: '1px solid transparent',
    borderBottom: 'none',
    whiteSpace: 'nowrap',
    minWidth: '120px',
    maxWidth: '200px',
  },
  tabActive: {
    backgroundColor: 'var(--surface-ground)',
    color: 'var(--text-color)',
    borderColor: 'var(--surface-border)',
    borderBottomColor: 'var(--surface-ground)',
  },
  tabInactive: {
    backgroundColor: 'transparent',
    color: 'var(--text-color-secondary)',
  },
  tabName: {
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    cursor: 'text',
  },
  tabInput: {
    flex: 1,
    background: 'var(--surface-ground)',
    border: '1px solid var(--primary-color)',
    borderRadius: '3px',
    padding: '0.25rem 0.5rem',
    fontSize: '0.9rem',
    color: 'var(--text-color)',
    outline: 'none',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '1.3rem',
    lineHeight: '1',
    cursor: 'pointer',
    color: 'var(--text-color-secondary)',
    padding: '0 0.25rem',
    transition: 'color 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  addButton: {
    background: 'none',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    fontSize: '1.2rem',
    lineHeight: '1',
    cursor: 'pointer',
    color: 'var(--text-color-secondary)',
    padding: '0.4rem 0.8rem',
    transition: 'all 0.2s',
    marginLeft: '0.5rem',
  },
};
