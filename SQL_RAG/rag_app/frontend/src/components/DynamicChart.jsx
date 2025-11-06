import { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  Legend,
} from 'recharts';
import { getSavedQuery } from '../services/ragClient.js';
import { aggregateData, AGGREGATION_TYPES } from '../utils/chartDataTransformers.js';
import Card from './Card.jsx';
import chartDebugger from '../utils/chartDebugger.js';

const COLORS = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#14B8A6', '#F97316'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl">
        <p className="typography-caption text-blue-400">{label}</p>
        <p className="typography-body">{payload[0].value.toLocaleString()}</p>
      </div>
    );
  }
  return null;
};

/**
 * DynamicChart - Renders a chart visualization based on saved query data and configuration
 *
 * @param {Object} props
 * @param {string} props.savedQueryId - ID of the saved query to visualize
 * @param {Object} props.chartConfig - Chart configuration object
 * @param {string} props.chartConfig.chartType - Type of chart ('bar' or 'column')
 * @param {string} props.chartConfig.xColumn - Column name for X-axis (categorical)
 * @param {string} props.chartConfig.yColumn - Column name for Y-axis (numeric, optional for count)
 * @param {string} props.chartConfig.aggregation - Aggregation type ('count', 'sum', 'avg', 'min', 'max')
 * @param {string} props.title - Optional chart title override
 * @param {Function} props.onError - Optional error callback
 */
export default function DynamicChart({ savedQueryId, chartConfig, title, onError }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queryData, setQueryData] = useState(null);
  const [chartData, setChartData] = useState([]);

  // Component mount/unmount logging
  useEffect(() => {
    chartDebugger.lifecycle(savedQueryId, 'MOUNT', {
      chartConfig,
      title,
    });

    return () => {
      chartDebugger.lifecycle(savedQueryId, 'UNMOUNT');
    };
  }, [savedQueryId, chartConfig, title]);

  // Fetch saved query data
  useEffect(() => {
    if (!savedQueryId) {
      chartDebugger.warn('FETCH', 'No savedQueryId provided', { savedQueryId });
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      chartDebugger.info('FETCH', `Loading saved query: ${savedQueryId}`);

      try {
        const data = await getSavedQuery(savedQueryId);

        chartDebugger.success('FETCH', `Loaded query data for: ${savedQueryId}`, {
          hasData: !!data,
          hasDataPreview: !!data?.data_preview,
          dataPreviewLength: data?.data_preview?.length || 0,
          question: data?.question,
          rowCount: data?.row_count,
        });

        setQueryData(data);
      } catch (err) {
        const errorMsg = err.message || 'Failed to load query data';

        chartDebugger.error('FETCH', `Failed to load query: ${savedQueryId}`, {
          error: err,
          errorMessage: errorMsg,
          chartConfig,
        });

        setError(errorMsg);
        if (onError) {
          onError(errorMsg);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [savedQueryId, onError]);

  // Transform data when query data or config changes
  useEffect(() => {
    if (!queryData || !queryData.data_preview || !chartConfig) {
      chartDebugger.warn('TRANSFORM', `Missing data for transformation`, {
        hasQueryData: !!queryData,
        hasDataPreview: !!queryData?.data_preview,
        hasChartConfig: !!chartConfig,
        savedQueryId,
      });
      setChartData([]);
      return;
    }

    try {
      const { xColumn, yColumn, aggregation = 'count' } = chartConfig;

      chartDebugger.info('TRANSFORM', `Starting data transformation for: ${savedQueryId}`, {
        xColumn,
        yColumn,
        aggregation,
        inputRows: queryData.data_preview.length,
        chartType: chartConfig.chartType,
      });

      if (!xColumn) {
        chartDebugger.warn('TRANSFORM', `No xColumn specified for: ${savedQueryId}`, {
          chartConfig,
        });
        setChartData([]);
        return;
      }

      const aggregated = aggregateData(
        queryData.data_preview,
        xColumn,
        yColumn,
        aggregation,
        10 // Top 10 results
      );

      chartDebugger.success('TRANSFORM', `Data transformed for: ${savedQueryId}`, {
        outputRows: aggregated.length,
        sample: aggregated.slice(0, 3),
      });

      setChartData(aggregated);
    } catch (err) {
      chartDebugger.error('TRANSFORM', `Failed to transform data for: ${savedQueryId}`, {
        error: err,
        chartConfig,
        dataPreviewLength: queryData?.data_preview?.length,
      });

      console.error('Error transforming chart data:', err);
      setChartData([]);
    }
  }, [queryData, chartConfig, savedQueryId]);

  // Loading state
  if (loading) {
    chartDebugger.info('RENDER', `Showing loading state for: ${savedQueryId}`);
    return (
      <Card className="h-64 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse">
            <div className="h-4 w-32 bg-gray-700 rounded mb-2 mx-auto"></div>
            <div className="h-3 w-24 bg-gray-800 rounded mx-auto"></div>
          </div>
        </div>
      </Card>
    );
  }

  // Error state
  if (error) {
    chartDebugger.error('RENDER', `Displaying error state for: ${savedQueryId}`, {
      error,
      savedQueryId,
      chartConfig,
    });
    return (
      <Card className="h-64 flex items-center justify-center">
        <div className="text-center">
          <h3 className="typography-body text-red-400 mb-2">Error Loading Chart</h3>
          <p className="typography-caption text-gray-500">{error}</p>
        </div>
      </Card>
    );
  }

  // Empty state
  if (!chartData || chartData.length === 0) {
    chartDebugger.warn('RENDER', `No chart data available for: ${savedQueryId}`, {
      hasChartData: !!chartData,
      chartDataLength: chartData?.length || 0,
      chartConfig,
      queryData: queryData ? {
        hasDataPreview: !!queryData.data_preview,
        dataPreviewLength: queryData.data_preview?.length || 0,
      } : null,
    });
    return (
      <Card className="h-64 flex items-center justify-center">
        <div className="text-center">
          <h3 className="typography-body text-gray-400 mb-2">No Data Available</h3>
          <p className="typography-caption text-gray-600">
            {chartConfig?.xColumn
              ? `Unable to generate chart for "${chartConfig.xColumn}"`
              : 'Select columns to visualize'}
          </p>
        </div>
      </Card>
    );
  }

  const chartTitle = title || `${chartConfig?.aggregation || 'Count'} by ${chartConfig?.xColumn || 'Category'}`;
  const chartType = chartConfig?.chartType || 'column';

  // Log successful chart render
  chartDebugger.success('RENDER', `Rendering ${chartType} chart for: ${savedQueryId}`, {
    chartTitle,
    chartType,
    dataPoints: chartData.length,
    xColumn: chartConfig.xColumn,
    yColumn: chartConfig.yColumn,
    aggregation: chartConfig.aggregation,
  });

  // Render appropriate chart based on type
  const renderChart = () => {
    switch (chartType) {
      case 'bar':
        // Horizontal bar chart
        return (
          <ResponsiveContainer width="100%" height={Math.max(250, chartData.length * 30)}>
            <BarChart
              data={chartData}
              layout="horizontal"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <YAxis
                dataKey="name"
                type="category"
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
                width={100}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );

      case 'column':
        // Vertical column chart (default)
        return (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="name"
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <YAxis
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        // Line chart for trends and time-series
        return (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="name"
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <YAxis
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="value"
                stroke={COLORS[0]}
                strokeWidth={2}
                dot={{ fill: COLORS[0], r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'area':
        // Area chart for cumulative trends
        return (
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="name"
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <YAxis
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke={COLORS[0]}
                fill={COLORS[0]}
                fillOpacity={0.3}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'pie':
        // Pie chart for proportional data (limit to top 8)
        const pieData = chartData.slice(0, 8).map((item, index) => ({
          ...item,
          fill: COLORS[index % COLORS.length],
        }));
        const total = pieData.reduce((sum, item) => sum + item.value, 0);

        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={(entry) => {
                  const percent = ((entry.value / total) * 100).toFixed(1);
                  return `${entry.name}: ${percent}%`;
                }}
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'donut':
        // Donut chart (pie with inner radius)
        const donutData = chartData.slice(0, 8).map((item, index) => ({
          ...item,
          fill: COLORS[index % COLORS.length],
        }));
        const donutTotal = donutData.reduce((sum, item) => sum + item.value, 0);

        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={donutData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                label={(entry) => {
                  const percent = ((entry.value / donutTotal) * 100).toFixed(1);
                  return `${entry.name}: ${percent}%`;
                }}
              >
                {donutData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        // Scatter chart for correlation (requires both X and Y to be numeric)
        // For scatter, we use raw data points instead of aggregated data
        const scatterData = queryData?.data_preview?.slice(0, 100).map((row) => ({
          x: parseFloat(row[chartConfig.xColumn]) || 0,
          y: parseFloat(row[chartConfig.yColumn]) || 0,
          name: row[chartConfig.xColumn],
        })) || [];

        return (
          <ResponsiveContainer width="100%" height={250}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid stroke="#374151" />
              <XAxis
                type="number"
                dataKey="x"
                name={chartConfig.xColumn}
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={chartConfig.yColumn}
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl">
                        <p className="typography-caption text-blue-400">
                          {chartConfig.xColumn}: {payload[0].value}
                        </p>
                        <p className="typography-caption text-green-400">
                          {chartConfig.yColumn}: {payload[1]?.value}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter
                name="Data Points"
                data={scatterData}
                fill={COLORS[0]}
              />
            </ScatterChart>
          </ResponsiveContainer>
        );

      default:
        // Fallback to column chart
        return (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="name"
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <YAxis
                stroke="#9CA3AF"
                tick={{ fill: '#9CA3AF', fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <Card>
      <h3 className="typography-subheading mb-4 capitalize">{chartTitle}</h3>
      {renderChart()}
    </Card>
  );
}
