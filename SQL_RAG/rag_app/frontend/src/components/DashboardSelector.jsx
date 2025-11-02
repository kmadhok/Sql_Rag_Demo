import { useState } from 'react';
import Button from './Button.jsx';

/**
 * DashboardSelector - Dropdown for managing multiple dashboards
 *
 * @param {Object} props
 * @param {Array} props.dashboards - List of available dashboards
 * @param {string} props.activeDashboardId - Currently active dashboard ID
 * @param {Function} props.onSelect - Callback when dashboard is selected
 * @param {Function} props.onCreate - Callback to create new dashboard
 * @param {Function} props.onRename - Callback to rename dashboard
 * @param {Function} props.onDuplicate - Callback to duplicate dashboard
 * @param {Function} props.onDelete - Callback to delete dashboard
 */
export default function DashboardSelector({
  dashboards,
  activeDashboardId,
  onSelect,
  onCreate,
  onRename,
  onDuplicate,
  onDelete,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [renaming, setRenaming] = useState(null);
  const [renamValue, setRenameValue] = useState('');

  const activeDashboard = dashboards.find(d => d.id === activeDashboardId);

  const handleRenameStart = (dashboard) => {
    setRenaming(dashboard.id);
    setRenameValue(dashboard.name);
  };

  const handleRenameSave = () => {
    if (renaming && renamValue.trim()) {
      onRename(renaming, renamValue.trim());
      setRenaming(null);
      setRenameValue('');
    }
  };

  const handleRenameCancel = () => {
    setRenaming(null);
    setRenameValue('');
  };

  const handleDelete = (dashboardId) => {
    if (confirm('Are you sure you want to delete this dashboard? This cannot be undone.')) {
      onDelete(dashboardId);
      setIsOpen(false);
    }
  };

  const handleDuplicate = (dashboardId) => {
    onDuplicate(dashboardId);
    setIsOpen(false);
  };

  return (
    <div className="dashboard-selector-wrapper">
      {/* Selected Dashboard Display */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="dashboard-selector-button"
        >
          <span className="typography-subheading">
            {activeDashboard?.name || 'Select Dashboard'}
          </span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}
          >
            <path
              d="M4 6l4 4 4-4"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {/* Create New Dashboard Button */}
        <Button
          variant="secondary"
          size="sm"
          onClick={onCreate}
        >
          + New Dashboard
        </Button>
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown Content */}
          <div className="dashboard-selector-dropdown">
            <div className="dashboard-selector-header">
              <span className="typography-caption">My Dashboards</span>
              <span className="badge-soft">{dashboards.length}</span>
            </div>

            <div className="dashboard-selector-list">
              {dashboards.map((dashboard) => (
                <div
                  key={dashboard.id}
                  className={`dashboard-selector-item ${
                    dashboard.id === activeDashboardId ? 'active' : ''
                  }`}
                >
                  {renaming === dashboard.id ? (
                    /* Rename Mode */
                    <div className="flex items-center gap-2 w-full">
                      <input
                        type="text"
                        value={renamValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleRenameSave();
                          if (e.key === 'Escape') handleRenameCancel();
                        }}
                        className="input-field flex-1 text-sm py-1"
                        autoFocus
                        onBlur={handleRenameSave}
                      />
                    </div>
                  ) : (
                    /* Normal Mode */
                    <>
                      <button
                        onClick={() => {
                          onSelect(dashboard.id);
                          setIsOpen(false);
                        }}
                        className="flex-1 text-left"
                      >
                        <div className="typography-body text-sm font-medium">
                          {dashboard.name}
                        </div>
                        <div className="typography-caption">
                          {dashboard.chart_count || 0} charts • Updated{' '}
                          {new Date(dashboard.updated_at).toLocaleDateString()}
                        </div>
                      </button>

                      {/* Action Buttons */}
                      <div className="flex items-center gap-1">
                        {/* Rename */}
                        <button
                          onClick={() => handleRenameStart(dashboard)}
                          className="icon-button"
                          title="Rename dashboard"
                        >
                          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                            <path
                              d="M9.5 2.5l2 2-6 6H3.5v-2l6-6z"
                              stroke="currentColor"
                              strokeWidth="1.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>

                        {/* Duplicate */}
                        <button
                          onClick={() => handleDuplicate(dashboard.id)}
                          className="icon-button"
                          title="Duplicate dashboard"
                        >
                          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                            <rect
                              x="4"
                              y="4"
                              width="8"
                              height="8"
                              rx="1"
                              stroke="currentColor"
                              strokeWidth="1.5"
                            />
                            <path
                              d="M2 10V3a1 1 0 011-1h7"
                              stroke="currentColor"
                              strokeWidth="1.5"
                              strokeLinecap="round"
                            />
                          </svg>
                        </button>

                        {/* Delete (disabled for active dashboard) */}
                        {dashboards.length > 1 && dashboard.id !== activeDashboardId && (
                          <button
                            onClick={() => handleDelete(dashboard.id)}
                            className="icon-button icon-button-danger"
                            title="Delete dashboard"
                          >
                            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                              <path
                                d="M2 4h10M5 4V2.5a1 1 0 011-1h2a1 1 0 011 1V4m1 0v8a1 1 0 01-1 1H5a1 1 0 01-1-1V4h6z"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>

            {dashboards.length === 0 && (
              <div className="text-center py-8">
                <p className="typography-caption text-gray-500">No dashboards yet</p>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    onCreate();
                    setIsOpen(false);
                  }}
                  className="mt-3"
                >
                  Create Your First Dashboard
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
