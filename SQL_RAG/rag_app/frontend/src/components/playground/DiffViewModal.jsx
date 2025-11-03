export default function DiffViewModal({ diffData, onApply, onClose }) {
  if (!diffData) return null;

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h3 style={styles.title}>AI Fixed Your Query</h3>
          <button
            onClick={onClose}
            style={styles.closeButton}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* Diagnosis Section */}
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <span style={styles.icon}>📋</span>
            <strong style={styles.sectionTitle}>What was wrong:</strong>
          </div>
          <p style={styles.diagnosisText}>{diffData.diagnosis}</p>
        </div>

        {/* Changes Section */}
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <span style={styles.icon}>🔧</span>
            <strong style={styles.sectionTitle}>Changes made:</strong>
          </div>
          <p style={styles.changesText}>{diffData.changes}</p>
        </div>

        {/* Diff View */}
        <div style={styles.diffContainer}>
          <div style={styles.diffColumn}>
            <h4 style={styles.diffHeader}>Original</h4>
            <pre style={styles.diffContent}>{diffData.original}</pre>
          </div>
          <div style={styles.diffDivider}></div>
          <div style={styles.diffColumn}>
            <h4 style={{...styles.diffHeader, ...styles.diffHeaderFixed}}>Fixed</h4>
            <pre style={{...styles.diffContent, ...styles.diffContentFixed}}>
              {diffData.fixed}
            </pre>
          </div>
        </div>

        {/* Actions */}
        <div style={styles.actions}>
          <button
            onClick={onClose}
            style={styles.secondaryButton}
          >
            Keep Original
          </button>
          <button
            onClick={() => onApply(diffData.fixed)}
            style={styles.primaryButton}
          >
            Apply Fix
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
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '1rem',
  },
  modal: {
    backgroundColor: 'var(--surface-ground)',
    borderRadius: '8px',
    maxWidth: '900px',
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
  section: {
    padding: '1.5rem',
    borderBottom: '1px solid var(--surface-border)',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  icon: {
    fontSize: '1.2rem',
  },
  sectionTitle: {
    fontSize: '1rem',
    color: 'var(--text-color)',
  },
  diagnosisText: {
    margin: 0,
    marginLeft: '1.7rem',
    color: 'var(--text-color-secondary)',
    lineHeight: '1.5',
  },
  changesText: {
    margin: 0,
    marginLeft: '1.7rem',
    color: 'var(--text-color-secondary)',
    lineHeight: '1.5',
  },
  diffContainer: {
    display: 'grid',
    gridTemplateColumns: '1fr 1px 1fr',
    gap: 0,
    padding: '1.5rem',
    borderBottom: '1px solid var(--surface-border)',
  },
  diffColumn: {
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  diffDivider: {
    width: '1px',
    backgroundColor: 'var(--surface-border)',
    margin: '0 1rem',
  },
  diffHeader: {
    margin: '0 0 0.75rem 0',
    fontSize: '0.9rem',
    fontWeight: '600',
    color: 'var(--text-color-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  diffHeaderFixed: {
    color: 'var(--primary-color)',
  },
  diffContent: {
    margin: 0,
    padding: '1rem',
    backgroundColor: 'var(--surface-section)',
    borderRadius: '4px',
    fontSize: '0.85rem',
    fontFamily: 'monospace',
    lineHeight: '1.5',
    overflow: 'auto',
    color: 'var(--text-color)',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  diffContentFixed: {
    borderLeft: '3px solid var(--primary-color)',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '1rem',
    padding: '1.5rem',
  },
  secondaryButton: {
    padding: '0.75rem 1.5rem',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    backgroundColor: 'var(--surface-ground)',
    color: 'var(--text-color)',
    fontSize: '1rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  primaryButton: {
    padding: '0.75rem 1.5rem',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: 'var(--primary-color)',
    color: '#fff',
    fontSize: '1rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
};
