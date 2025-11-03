/**
 * Query Tabs Component
 * Manages multiple query tabs like browser tabs
 */
export default function QueryTabs({ tabs, activeTabId, onTabChange, onTabClose, onTabAdd }) {
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
            onClick={() => onTabChange(tab.id)}
          >
            <span style={styles.tabName}>{tab.name}</span>
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
