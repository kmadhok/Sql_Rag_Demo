import { useState } from 'react';

/**
 * Modal for saving a query from Playground to the saved queries database
 */
export default function SaveQueryModal({ sql, onSave, onClose }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!name.trim()) {
      setError('Query name is required');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await onSave({
        name: name.trim(),
        description: description.trim(),
        sql: sql,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save query');
      setIsSaving(false);
    }
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h3 style={styles.title}>Save Query</h3>
          <button
            onClick={onClose}
            style={styles.closeButton}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div style={styles.content}>
            {/* Query Name */}
            <div style={styles.field}>
              <label style={styles.label}>
                Query Name <span style={styles.required}>*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Top 10 Products by Revenue"
                style={styles.input}
                autoFocus
                disabled={isSaving}
              />
            </div>

            {/* Description */}
            <div style={styles.field}>
              <label style={styles.label}>Description (Optional)</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this query does..."
                style={{ ...styles.input, ...styles.textarea }}
                rows={3}
                disabled={isSaving}
              />
            </div>

            {/* SQL Preview */}
            <div style={styles.field}>
              <label style={styles.label}>SQL Query</label>
              <pre style={styles.sqlPreview}>
                {sql.length > 200 ? sql.substring(0, 200) + '...' : sql}
              </pre>
            </div>

            {/* Error Message */}
            {error && (
              <div style={styles.errorMessage}>
                ⚠️ {error}
              </div>
            )}
          </div>

          {/* Actions */}
          <div style={styles.actions}>
            <button
              type="button"
              onClick={onClose}
              style={styles.secondaryButton}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              style={styles.primaryButton}
              disabled={isSaving || !name.trim()}
            >
              {isSaving ? 'Saving...' : 'Save Query'}
            </button>
          </div>
        </form>
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
    maxWidth: '540px',
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
  field: {
    marginBottom: '1.25rem',
  },
  label: {
    display: 'block',
    marginBottom: '0.5rem',
    fontSize: '0.9rem',
    fontWeight: '500',
    color: 'var(--text-color)',
  },
  required: {
    color: '#ef4444',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    fontSize: '0.95rem',
    backgroundColor: 'var(--surface-section)',
    color: 'var(--text-color)',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  textarea: {
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  sqlPreview: {
    padding: '0.75rem',
    backgroundColor: 'var(--surface-section)',
    border: '1px solid var(--surface-border)',
    borderRadius: '4px',
    fontSize: '0.85rem',
    fontFamily: 'monospace',
    color: 'var(--text-color-secondary)',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    maxHeight: '150px',
    overflow: 'auto',
  },
  errorMessage: {
    padding: '0.75rem',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '4px',
    color: '#ef4444',
    fontSize: '0.9rem',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '1rem',
    padding: '1.5rem',
    borderTop: '1px solid var(--surface-border)',
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
