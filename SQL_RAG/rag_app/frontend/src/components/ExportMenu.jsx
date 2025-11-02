import { useState, useRef } from 'react';
import Button from './Button.jsx';

/**
 * ExportMenu - Dropdown menu for exporting dashboard
 *
 * @param {Object} props
 * @param {Function} props.onExportPNG - Callback for PNG export
 * @param {Function} props.onExportPDF - Callback for PDF export
 * @param {Function} props.onExportJSON - Callback for JSON export
 * @param {boolean} props.isExporting - Loading state during export
 */
export default function ExportMenu({ onExportPNG, onExportPDF, onExportJSON, isExporting }) {
  const [isOpen, setIsOpen] = useState(false);
  const fileInputRef = useRef(null);

  const handleExport = async (format) => {
    setIsOpen(false);

    switch (format) {
      case 'png':
        await onExportPNG();
        break;
      case 'pdf':
        await onExportPDF();
        break;
      case 'json':
        await onExportJSON();
        break;
      default:
        break;
    }
  };

  const exportOptions = [
    {
      id: 'png',
      label: 'Export as PNG',
      icon: '🖼️',
      description: 'High-quality image file',
    },
    {
      id: 'pdf',
      label: 'Export as PDF',
      icon: '📄',
      description: 'Portable document format',
    },
    {
      id: 'json',
      label: 'Export as JSON',
      icon: '📦',
      description: 'Dashboard configuration',
    },
  ];

  return (
    <div className="export-menu-wrapper">
      <Button
        variant="secondary"
        onClick={() => setIsOpen(!isOpen)}
        disabled={isExporting}
      >
        {isExporting ? 'Exporting...' : 'Export'}
      </Button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown Menu */}
          <div className="export-menu-dropdown">
            {exportOptions.map((option) => (
              <button
                key={option.id}
                onClick={() => handleExport(option.id)}
                className="export-menu-item"
                disabled={isExporting}
              >
                <span className="export-menu-icon">{option.icon}</span>
                <div className="export-menu-content">
                  <div className="export-menu-label">{option.label}</div>
                  <div className="export-menu-description">{option.description}</div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
