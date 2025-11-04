/**
 * Keyboard Shortcuts Help Modal
 * Displays all available keyboard shortcuts in the SQL Playground
 */
export default function KeyboardShortcutsModal({ onClose }) {
  const shortcuts = [
    {
      category: 'Query Execution',
      items: [
        { keys: ['Cmd', 'Enter'], description: 'Execute query' },
        { keys: ['Cmd', 'Shift', 'Enter'], description: 'Dry run query' },
      ]
    },
    {
      category: 'Editor',
      items: [
        { keys: ['Cmd', 'K'], description: 'Format SQL' },
        { keys: ['Cmd', '/'], description: 'Toggle line comment' },
        { keys: ['Cmd', 'D'], description: 'Duplicate line' },
        { keys: ['Cmd', 'F'], description: 'Find in editor' },
        { keys: ['Cmd', 'H'], description: 'Find and replace' },
      ]
    },
    {
      category: 'Tab Management',
      items: [
        { keys: ['Cmd', 'T'], description: 'New tab' },
        { keys: ['Cmd', 'W'], description: 'Close current tab' },
        { keys: ['Double-click'], description: 'Rename tab (on tab name)' },
      ]
    },
    {
      category: 'Navigation',
      items: [
        { keys: ['Cmd', 'B'], description: 'Toggle schema explorer' },
        { keys: ['Cmd', 'H'], description: 'Toggle query history' },
        { keys: ['?'], description: 'Show keyboard shortcuts' },
      ]
    },
    {
      category: 'Schema Explorer',
      items: [
        { keys: ['Click table'], description: 'Insert table name' },
        { keys: ['Click column'], description: 'Insert column name' },
        { keys: ['Tab'], description: 'Autocomplete from schema' },
      ]
    }
  ];

  // Detect OS for correct modifier key display
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const modifierKey = isMac ? 'Cmd' : 'Ctrl';

  const formatKeys = (keys) => {
    return keys.map(key => key === 'Cmd' ? modifierKey : key).join(' + ');
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h3 style={styles.title}>Keyboard Shortcuts</h3>
          <button
            onClick={onClose}
            style={styles.closeButton}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* Shortcuts Content */}
        <div style={styles.content}>
          {shortcuts.map((category, categoryIndex) => (
            <div key={categoryIndex} style={styles.category}>
              <h4 style={styles.categoryTitle}>{category.category}</h4>
              <div style={styles.shortcutList}>
                {category.items.map((shortcut, itemIndex) => (
                  <div key={itemIndex} style={styles.shortcutItem}>
                    <div style={styles.keys}>
                      {formatKeys(shortcut.keys).split(' + ').map((key, keyIndex, array) => (
                        <span key={keyIndex}>
                          <kbd style={styles.key}>{key}</kbd>
                          {keyIndex < array.length - 1 && <span style={styles.plus}>+</span>}
                        </span>
                      ))}
                    </div>
                    <div style={styles.description}>{shortcut.description}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <p style={styles.footerText}>
            Press <kbd style={styles.footerKey}>?</kbd> anytime to show this help
          </p>
          <button
            onClick={onClose}
            style={styles.closeFooterButton}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '1rem',
  },
  modal: {
    backgroundColor: 'var(--surface-ground)',
    borderRadius: '8px',
    maxWidth: '700px',
    width: '100%',
    maxHeight: '90vh',
    overflow: 'auto',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1.5rem',
    borderBottom: '1px solid var(--surface-border)',
    backgroundColor: 'var(--surface-section)',
  },
  title: {
    margin: 0,
    fontSize: '1.25rem',
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
  content: {
    padding: '1.5rem',
  },
  category: {
    marginBottom: '2rem',
  },
  categoryTitle: {
    fontSize: '0.95rem',
    fontWeight: '600',
    color: 'var(--text-color)',
    marginBottom: '1rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    opacity: 0.8,
  },
  shortcutList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  shortcutItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.75rem',
    backgroundColor: 'var(--surface-section)',
    borderRadius: '4px',
    transition: 'background-color 0.2s',
  },
  keys: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
    minWidth: '200px',
  },
  key: {
    display: 'inline-block',
    padding: '0.25rem 0.5rem',
    backgroundColor: 'var(--surface-ground)',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    fontSize: '0.85rem',
    fontFamily: 'monospace',
    color: 'var(--text-color)',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)',
    minWidth: '35px',
    textAlign: 'center',
  },
  plus: {
    color: 'var(--text-color-secondary)',
    fontSize: '0.85rem',
    margin: '0 0.25rem',
  },
  description: {
    color: 'var(--text-color-secondary)',
    fontSize: '0.9rem',
    flex: 1,
    textAlign: 'right',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1rem 1.5rem',
    borderTop: '1px solid var(--surface-border)',
    backgroundColor: 'var(--surface-section)',
  },
  footerText: {
    margin: 0,
    fontSize: '0.85rem',
    color: 'var(--text-color-secondary)',
  },
  footerKey: {
    display: 'inline-block',
    padding: '0.15rem 0.4rem',
    backgroundColor: 'var(--surface-ground)',
    border: '1px solid var(--surface-border)',
    borderRadius: '3px',
    fontSize: '0.8rem',
    fontFamily: 'monospace',
    color: 'var(--text-color)',
  },
  closeFooterButton: {
    padding: '0.5rem 1.5rem',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: 'var(--primary-color)',
    color: '#fff',
    fontSize: '0.9rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
};
