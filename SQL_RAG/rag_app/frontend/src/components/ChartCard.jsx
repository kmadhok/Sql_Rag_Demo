import { useState, useEffect } from 'react';
import DynamicChart from './DynamicChart.jsx';
import Button from './Button.jsx';
import chartDebugger from '../utils/chartDebugger.js';

/**
 * ChartCard - Draggable/resizable wrapper for chart visualizations
 * Used within react-grid-layout to create dashboard grid items
 *
 * @param {Object} props
 * @param {string} props.itemId - Unique identifier for the grid item
 * @param {string} props.savedQueryId - ID of the saved query to visualize
 * @param {string} props.queryQuestion - The natural language question (for display)
 * @param {Object} props.chartConfig - Chart configuration (type, columns, aggregation)
 * @param {Function} props.onConfigure - Callback when configure button clicked
 * @param {Function} props.onRemove - Callback when remove button clicked
 * @param {boolean} props.isDragging - Whether the card is currently being dragged
 */
export default function ChartCard({
  itemId,
  savedQueryId,
  queryQuestion,
  chartConfig,
  onConfigure,
  onRemove,
  isDragging = false,
}) {
  const [isHovered, setIsHovered] = useState(false);

  // Log ChartCard lifecycle
  useEffect(() => {
    chartDebugger.lifecycle(itemId, 'CARD_MOUNT', {
      savedQueryId,
      queryQuestion,
      chartConfig,
    });

    return () => {
      chartDebugger.lifecycle(itemId, 'CARD_UNMOUNT');
    };
  }, [itemId, savedQueryId, queryQuestion, chartConfig]);

  // Enhanced error handler with detailed context
  const handleChartError = (err) => {
    chartDebugger.error('CARD', `Chart error in card: ${itemId}`, {
      itemId,
      savedQueryId,
      queryQuestion,
      chartConfig,
      error: err,
    });

    console.error(`Chart ${itemId} error:`, err);
  };

  return (
    <div
      className={`chart-card-wrapper h-full ${isDragging ? 'dragging' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Card Header with Drag Handle and Actions */}
      <div className="chart-card-header surface-panel-light border-b border-gray-700 p-3 rounded-t-lg">
        <div className="flex items-start justify-between gap-3">
          {/* Left side: Drag handle + Title */}
          <div className="flex items-start gap-2 flex-1 min-w-0">
            {/* Drag Handle */}
            <div
              className="drag-handle cursor-grab active:cursor-grabbing flex-shrink-0 pt-1"
              title="Drag to reorder"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className={`transition-opacity ${isHovered ? 'opacity-100' : 'opacity-30'}`}
              >
                <circle cx="4" cy="4" r="1.5" fill="currentColor" />
                <circle cx="4" cy="8" r="1.5" fill="currentColor" />
                <circle cx="4" cy="12" r="1.5" fill="currentColor" />
                <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                <circle cx="12" cy="8" r="1.5" fill="currentColor" />
                <circle cx="12" cy="12" r="1.5" fill="currentColor" />
              </svg>
            </div>

            {/* Title */}
            <div className="flex-1 min-w-0">
              <h4 className="typography-body text-sm font-medium truncate">
                {queryQuestion || 'Unnamed Chart'}
              </h4>
              {chartConfig?.xColumn && (
                <p className="typography-caption text-gray-500 truncate">
                  {chartConfig.aggregation || 'count'} by {chartConfig.xColumn}
                  {chartConfig.yColumn && ` (${chartConfig.yColumn})`}
                </p>
              )}
            </div>
          </div>

          {/* Right side: Action Buttons (visible on hover) */}
          <div
            className={`flex items-center gap-1 transition-opacity ${
              isHovered ? 'opacity-100' : 'opacity-0'
            }`}
          >
            {/* Configure Button */}
            {onConfigure && (
              <button
                onClick={() => onConfigure(itemId)}
                className="icon-button"
                title="Configure chart"
                aria-label="Configure chart"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path
                    d="M8 10a2 2 0 100-4 2 2 0 000 4z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M13 8a4.978 4.978 0 01-.465 2.1l1.11 1.11a1 1 0 01-1.414 1.414l-1.11-1.11A5 5 0 113.465 5.9l-1.11-1.11A1 1 0 012.77 3.38l1.11 1.11A4.978 4.978 0 018 3a5 5 0 015 5z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            )}

            {/* Remove Button */}
            {onRemove && (
              <button
                onClick={() => onRemove(itemId)}
                className="icon-button icon-button-danger"
                title="Remove chart"
                aria-label="Remove chart"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path
                    d="M4 4l8 8M12 4l-8 8"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Chart Content */}
      <div className="chart-card-content p-3">
        <DynamicChart
          savedQueryId={savedQueryId}
          chartConfig={chartConfig}
          onError={handleChartError}
        />
      </div>
    </div>
  );
}
