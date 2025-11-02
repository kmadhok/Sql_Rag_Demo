import { useState, useEffect } from 'react';
import { getSavedQuery } from '../services/ragClient.js';
import { isNumericColumn, AGGREGATION_TYPES } from '../utils/chartDataTransformers.js';
import Button from './Button.jsx';
import DynamicChart from './DynamicChart.jsx';

/**
 * AddVisualizationModal - Modal dialog for adding new chart to dashboard
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is visible
 * @param {Array} props.savedQueries - List of available saved queries
 * @param {Function} props.onAdd - Callback when chart is added (chartConfig)
 * @param {Function} props.onClose - Callback when modal is closed
 */
export default function AddVisualizationModal({ isOpen, savedQueries, onAdd, onClose }) {
  const [step, setStep] = useState(1); // 1: Select Query, 2: Configure Chart
  const [selectedQueryId, setSelectedQueryId] = useState('');
  const [queryData, setQueryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [chartConfig, setChartConfig] = useState({
    chartType: 'column',
    xColumn: '',
    yColumn: '',
    aggregation: 'count',
  });

  const [availableColumns, setAvailableColumns] = useState([]);
  const [numericColumns, setNumericColumns] = useState([]);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setSelectedQueryId('');
      setQueryData(null);
      setError(null);
      setChartConfig({
        chartType: 'column',
        xColumn: '',
        yColumn: '',
        aggregation: 'count',
      });
    }
  }, [isOpen]);

  // Load query data when selected
  useEffect(() => {
    if (!selectedQueryId) {
      setQueryData(null);
      setAvailableColumns([]);
      setNumericColumns([]);
      return;
    }

    const loadQuery = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getSavedQuery(selectedQueryId);
        setQueryData(data);

        // Extract column names
        if (data.data_preview && data.data_preview.length > 0) {
          const cols = Object.keys(data.data_preview[0]);
          setAvailableColumns(cols);

          // Detect numeric columns
          const numeric = cols.filter((col) =>
            isNumericColumn(data.data_preview, col)
          );
          setNumericColumns(numeric);

          // Auto-select first column for X-axis
          if (cols.length > 0 && !chartConfig.xColumn) {
            setChartConfig((prev) => ({ ...prev, xColumn: cols[0] }));
          }
        }
      } catch (err) {
        setError(err.message || 'Failed to load query');
      } finally {
        setLoading(false);
      }
    };

    loadQuery();
  }, [selectedQueryId]);

  const handleNext = () => {
    if (step === 1 && selectedQueryId) {
      setStep(2);
    }
  };

  const handleBack = () => {
    if (step === 2) {
      setStep(1);
    }
  };

  const handleAdd = () => {
    if (!selectedQueryId || !chartConfig.xColumn) {
      return;
    }

    const selectedQuery = savedQueries.find((q) => q.id === selectedQueryId);

    onAdd({
      savedQueryId: selectedQueryId,
      queryQuestion: selectedQuery?.question || 'Untitled',
      chartConfig: { ...chartConfig },
    });

    onClose();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <h2 className="typography-heading">Add Visualization</h2>
          <button onClick={onClose} className="icon-button" aria-label="Close modal">
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
          {/* Step 1: Select Saved Query */}
          {step === 1 && (
            <div className="space-y-lg">
              <div>
                <label className="typography-subheading block mb-2">
                  Select Saved Query
                </label>
                <select
                  value={selectedQueryId}
                  onChange={(e) => setSelectedQueryId(e.target.value)}
                  className="input-field w-full"
                  disabled={loading}
                >
                  <option value="">-- Choose a query --</option>
                  {savedQueries.map((query) => (
                    <option key={query.id} value={query.id}>
                      {query.question} ({query.row_count} rows)
                    </option>
                  ))}
                </select>
              </div>

              {loading && (
                <div className="text-center py-4">
                  <p className="typography-body text-gray-400">Loading query data...</p>
                </div>
              )}

              {error && (
                <div className="surface-panel-light border-l-4 border-red-500 p-3">
                  <p className="typography-body text-red-400">{error}</p>
                </div>
              )}

              {queryData && (
                <div className="surface-panel-light rounded-lg p-4">
                  <h4 className="typography-subheading mb-2">Query Preview</h4>
                  <p className="typography-caption text-gray-400 mb-3">
                    {queryData.row_count} rows, {availableColumns.length} columns
                  </p>
                  <div className="space-y-1">
                    <p className="typography-caption font-semibold">Available Columns:</p>
                    <div className="flex flex-wrap gap-2">
                      {availableColumns.map((col) => (
                        <span key={col} className="badge-soft text-xs">
                          {col}
                          {numericColumns.includes(col) && ' (numeric)'}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Configure Chart */}
          {step === 2 && (
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
                      No numeric columns detected. You may need to use COUNT aggregation.
                    </p>
                  )}
                </div>
              )}

              {/* Live Preview */}
              {chartConfig.xColumn && (
                <div>
                  <h4 className="typography-subheading mb-3">Preview</h4>
                  <DynamicChart
                    savedQueryId={selectedQueryId}
                    chartConfig={chartConfig}
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          {step === 1 && (
            <>
              <Button variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleNext}
                disabled={!selectedQueryId || loading}
              >
                Next
              </Button>
            </>
          )}

          {step === 2 && (
            <>
              <Button variant="secondary" onClick={handleBack}>
                Back
              </Button>
              <Button
                variant="primary"
                onClick={handleAdd}
                disabled={!chartConfig.xColumn || (chartConfig.aggregation !== 'count' && !chartConfig.yColumn)}
              >
                Add to Dashboard
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
