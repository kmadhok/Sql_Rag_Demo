import { useState, useEffect } from 'react';
import { getSavedQuery } from '../services/ragClient.js';
import { isNumericColumn, AGGREGATION_TYPES } from '../utils/chartDataTransformers.js';
import Button from './Button.jsx';
import DynamicChart from './DynamicChart.jsx';

/**
 * ChartConfigPanel - Modal panel for editing existing chart configuration
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether panel is visible
 * @param {string} props.savedQueryId - ID of the saved query being visualized
 * @param {string} props.queryQuestion - Natural language question for context
 * @param {Object} props.chartConfig - Current chart configuration
 * @param {Function} props.onSave - Callback when config is saved (newConfig)
 * @param {Function} props.onClose - Callback when panel is closed
 */
export default function ChartConfigPanel({
  isOpen,
  savedQueryId,
  queryQuestion,
  chartConfig: initialConfig,
  onSave,
  onClose,
}) {
  const [chartConfig, setChartConfig] = useState(initialConfig || {
    chartType: 'column',
    xColumn: '',
    yColumn: '',
    aggregation: 'count',
  });

  const [queryData, setQueryData] = useState(null);
  const [availableColumns, setAvailableColumns] = useState([]);
  const [numericColumns, setNumericColumns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Update local config when initial config changes
  useEffect(() => {
    if (initialConfig) {
      setChartConfig(initialConfig);
    }
  }, [initialConfig]);

  // Load query data
  useEffect(() => {
    if (!isOpen || !savedQueryId) {
      return;
    }

    const loadQuery = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getSavedQuery(savedQueryId);
        setQueryData(data);

        // Extract columns
        if (data.data_preview && data.data_preview.length > 0) {
          const cols = Object.keys(data.data_preview[0]);
          setAvailableColumns(cols);

          // Detect numeric columns
          const numeric = cols.filter((col) =>
            isNumericColumn(data.data_preview, col)
          );
          setNumericColumns(numeric);
        }
      } catch (err) {
        setError(err.message || 'Failed to load query data');
      } finally {
        setLoading(false);
      }
    };

    loadQuery();
  }, [isOpen, savedQueryId]);

  const handleSave = () => {
    if (!chartConfig.xColumn) {
      return;
    }

    onSave({ ...chartConfig });
    onClose();
  };

  const hasChanges = JSON.stringify(chartConfig) !== JSON.stringify(initialConfig);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h2 className="typography-heading">Configure Chart</h2>
            <p className="typography-caption text-gray-400 mt-1">
              {queryQuestion}
            </p>
          </div>
          <button onClick={onClose} className="icon-button" aria-label="Close panel">
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

        {/* Modal Body */}
        <div className="modal-body">
          {loading ? (
            <div className="text-center py-8">
              <p className="typography-body text-gray-400">Loading query data...</p>
            </div>
          ) : error ? (
            <div className="surface-panel-light border-l-4 border-red-500 p-4">
              <p className="typography-body text-red-400">{error}</p>
            </div>
          ) : (
            <div className="space-y-lg">
              {/* Chart Type */}
              <div>
                <label className="typography-subheading block mb-2">Chart Type</label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() =>
                      setChartConfig((prev) => ({ ...prev, chartType: 'column' }))
                    }
                    className={`chart-type-button ${
                      chartConfig.chartType === 'column' ? 'active' : ''
                    }`}
                  >
                    <span>📊 Column</span>
                  </button>
                  <button
                    onClick={() =>
                      setChartConfig((prev) => ({ ...prev, chartType: 'bar' }))
                    }
                    className={`chart-type-button ${
                      chartConfig.chartType === 'bar' ? 'active' : ''
                    }`}
                  >
                    <span>📉 Bar</span>
                  </button>
                  <button
                    onClick={() =>
                      setChartConfig((prev) => ({ ...prev, chartType: 'line' }))
                    }
                    className={`chart-type-button ${
                      chartConfig.chartType === 'line' ? 'active' : ''
                    }`}
                  >
                    <span>📈 Line</span>
                  </button>
                  <button
                    onClick={() =>
                      setChartConfig((prev) => ({ ...prev, chartType: 'area' }))
                    }
                    className={`chart-type-button ${
                      chartConfig.chartType === 'area' ? 'active' : ''
                    }`}
                  >
                    <span>📊 Area</span>
                  </button>
                  <button
                    onClick={() =>
                      setChartConfig((prev) => ({ ...prev, chartType: 'pie' }))
                    }
                    className={`chart-type-button ${
                      chartConfig.chartType === 'pie' ? 'active' : ''
                    }`}
                  >
                    <span>🥧 Pie</span>
                  </button>
                  <button
                    onClick={() =>
                      setChartConfig((prev) => ({ ...prev, chartType: 'scatter' }))
                    }
                    className={`chart-type-button ${
                      chartConfig.chartType === 'scatter' ? 'active' : ''
                    }`}
                  >
                    <span>⚫ Scatter</span>
                  </button>
                </div>
              </div>

              {/* X-Axis Column */}
              <div>
                <label className="typography-subheading block mb-2">
                  X-Axis (Category)
                </label>
                <select
                  value={chartConfig.xColumn}
                  onChange={(e) =>
                    setChartConfig((prev) => ({ ...prev, xColumn: e.target.value }))
                  }
                  className="input-field w-full"
                >
                  <option value="">-- Select column --</option>
                  {availableColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Aggregation Type */}
              <div>
                <label className="typography-subheading block mb-2">Aggregation</label>
                <select
                  value={chartConfig.aggregation}
                  onChange={(e) =>
                    setChartConfig((prev) => ({ ...prev, aggregation: e.target.value }))
                  }
                  className="input-field w-full"
                >
                  <option value={AGGREGATION_TYPES.COUNT}>Count</option>
                  <option value={AGGREGATION_TYPES.SUM}>Sum</option>
                  <option value={AGGREGATION_TYPES.AVG}>Average</option>
                  <option value={AGGREGATION_TYPES.MIN}>Minimum</option>
                  <option value={AGGREGATION_TYPES.MAX}>Maximum</option>
                </select>
              </div>

              {/* Y-Axis Column (for non-count aggregations) */}
              {chartConfig.aggregation !== 'count' && (
                <div>
                  <label className="typography-subheading block mb-2">
                    Y-Axis (Value)
                  </label>
                  <select
                    value={chartConfig.yColumn}
                    onChange={(e) =>
                      setChartConfig((prev) => ({ ...prev, yColumn: e.target.value }))
                    }
                    className="input-field w-full"
                  >
                    <option value="">-- Select column --</option>
                    {numericColumns.map((col) => (
                      <option key={col} value={col}>
                        {col}
                      </option>
                    ))}
                  </select>
                  {numericColumns.length === 0 && (
                    <p className="typography-caption text-yellow-400 mt-2">
                      No numeric columns detected. Consider using COUNT aggregation.
                    </p>
                  )}
                </div>
              )}

              {/* Live Preview */}
              {chartConfig.xColumn && (
                <div>
                  <h4 className="typography-subheading mb-3">Preview</h4>
                  <DynamicChart
                    savedQueryId={savedQueryId}
                    chartConfig={chartConfig}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={
              !chartConfig.xColumn ||
              (chartConfig.aggregation !== 'count' && !chartConfig.yColumn) ||
              !hasChanges
            }
          >
            {hasChanges ? 'Save Changes' : 'No Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}
