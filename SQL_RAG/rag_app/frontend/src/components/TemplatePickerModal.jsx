import { useState } from 'react';
import Button from './Button.jsx';
import { DASHBOARD_TEMPLATES } from '../utils/dashboardTemplates.js';

/**
 * TemplatePickerModal - Modal for selecting dashboard template
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is visible
 * @param {Function} props.onSelect - Callback when template is selected (templateId, name)
 * @param {Function} props.onClose - Callback to close modal
 */
export default function TemplatePickerModal({ isOpen, onSelect, onClose }) {
  const [selectedTemplate, setSelectedTemplate] = useState('blank');
  const [dashboardName, setDashboardName] = useState('');

  if (!isOpen) return null;

  const handleCreate = () => {
    const name = dashboardName.trim() || 'New Dashboard';
    onSelect(selectedTemplate, name);
    // Reset state
    setSelectedTemplate('blank');
    setDashboardName('');
  };

  const handleCancel = () => {
    setSelectedTemplate('blank');
    setDashboardName('');
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div
        className="modal-content"
        style={{ maxWidth: '720px' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <h3 className="typography-heading">Create New Dashboard</h3>
          <button onClick={handleCancel} className="modal-close">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M5 5l10 10M15 5l-10 10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Dashboard Name Input */}
          <div style={{ marginBottom: 'var(--space-lg)' }}>
            <label className="typography-label">Dashboard Name</label>
            <input
              type="text"
              value={dashboardName}
              onChange={(e) => setDashboardName(e.target.value)}
              placeholder="e.g., Sales Overview, Analytics Dashboard"
              className="input-field"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreate();
                if (e.key === 'Escape') handleCancel();
              }}
            />
          </div>

          {/* Template Selection */}
          <div>
            <label className="typography-label">Choose Template</label>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                gap: 'var(--space-md)',
                marginTop: 'var(--space-sm)',
              }}
            >
              {DASHBOARD_TEMPLATES.map((template) => (
                <button
                  key={template.id}
                  onClick={() => setSelectedTemplate(template.id)}
                  className={`template-card ${
                    selectedTemplate === template.id ? 'active' : ''
                  }`}
                >
                  <div className="template-icon">{template.icon}</div>
                  <div className="template-name">{template.name}</div>
                  <div className="template-description">{template.description}</div>
                  {selectedTemplate === template.id && (
                    <div className="template-selected-badge">Selected</div>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <Button variant="secondary" onClick={handleCancel}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleCreate}>
            Create Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
