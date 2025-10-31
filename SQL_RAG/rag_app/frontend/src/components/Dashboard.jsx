import { useEffect, useMemo, useState } from "react";
import Button from "./Button.jsx";
import Card, { StatCard } from "./Card.jsx";
import {
  getSavedQuery,
} from "../services/ragClient.js";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";

function SavedQueryCard({ query, onSelect, isSelected }) {
  const [loading, setLoading] = useState(false);
  
  const handleSelect = async () => {
    if (!onSelect) return;
    
    setLoading(true);
    try {
      await onSelect(query.id);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card 
      hover 
      className={`cursor-pointer transition-all duration-200 ${isSelected ? 'card-active' : 'card-muted'}`}
      onClick={handleSelect}
    >
      <div className="space-y-md">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="typography-subheading text-sm line-clamp-2">
              {query.question}
            </h3>
            <p className="typography-caption mt-1">
              {query.row_count != null ? `${query.row_count.toLocaleString()} rows` : 'Rows unknown'}
            </p>
          </div>
          
          {isSelected && (
            <span className="badge-soft">Active</span>
          )}
        </div>
        
        {/* SQL Preview */}
        {query.sql && (
          <div className="card-muted rounded-lg p-3 border border-transparent">
            <p className="typography-caption font-mono text-xs text-blue-100 line-clamp-3">
              {query.sql}
            </p>
          </div>
        )}
        
        {/* Footer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="badge-soft">
              {(query.row_count ?? query.data_preview?.length ?? 0).toLocaleString()} rows
            </span>
            {query.created_at && (
              <span className="badge-soft">
                {new Date(query.created_at).toLocaleDateString()}
              </span>
            )}
          </div>
          
          <Button variant="secondary" size="sm" onClick={handleSelect} disabled={loading}>
            {loading ? "Loading..." : "View"}
          </Button>
        </div>
      </div>
    </Card>
  );
}

/* Chart Components - Clean */
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl">
        <p className="typography-caption text-blue-400">{label}</p>
        <p className="typography-body">{payload[0].value}</p>
      </div>
    );
  }
  return null;
};

const COLORS = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444'];

function BarChartVisualization({ data, title }) {
  if (!data || data.length === 0) {
    return (
      <Card className="h-64 flex items-center justify-center">
        <div className="text-center">
          <h3 className="typography-body text-gray-500 mb-2">No Data Available</h3>
          <p className="typography-caption text-gray-600">Select a column to visualize</p>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="typography-subheading mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
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
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

/* Empty State - Clean */
function EmptyState({ onGoToChat }) {
  return (
    <div className="text-center py-16 surface-panel-light">
      <h3 className="typography-heading mb-3">No Saved Queries Yet</h3>
      <p className="typography-body max-w-md mx-auto mb-6">
        Start by asking questions in the chat interface and save successful queries to your dashboard.
      </p>
      <Button variant="primary" onClick={onGoToChat}>
        Ask a question
      </Button>
    </div>
  );
}

/* Main Dashboard Component - Clean */
export default function Dashboard({ savedQueries, onRefresh, onGoToChat }) {
  const [selectedQuery, setSelectedQuery] = useState(null);
  const [selectedQueryData, setSelectedQueryData] = useState(null);
  const [viewMode, setViewMode] = useState('grid');
  const [loading, setLoading] = useState(false);
  const [chartColumn, setChartColumn] = useState('');

  // Auto-select the first query when list changes
  useEffect(() => {
    if (savedQueries?.length && !selectedQuery) {
      setSelectedQuery(savedQueries[0].id);
    }
  }, [savedQueries, selectedQuery]);

  // Load selected query details
  useEffect(() => {
    if (!selectedQuery) {
      setSelectedQueryData(null);
      return;
    }

    const loadQuery = async () => {
      setLoading(true);
      try {
        const queryData = await getSavedQuery(selectedQuery);
        const normalized = {
          ...queryData,
          data: queryData.data_preview || [],
          columns: (queryData.data_preview && queryData.data_preview.length > 0)
            ? Object.keys(queryData.data_preview[0])
            : [],
        };
        setSelectedQueryData(normalized);
        setChartColumn((prev) => {
          if (prev && normalized.columns.includes(prev)) {
            return prev;
          }
          return normalized.columns[0] || '';
        });
      } catch (error) {
        console.error('Failed to load query:', error);
        setSelectedQueryData(null);
      } finally {
        setLoading(false);
      }
    };

    loadQuery();
  }, [selectedQuery]);

  // Prepare chart data from selected query
  const chartData = useMemo(() => {
    if (!selectedQueryData?.data?.length || !chartColumn) {
      return null;
    }

    try {
      // Simple aggregation for the selected column
      const counts = {};
      selectedQueryData.data.forEach(row => {
        const value = String(row[chartColumn] || 'Unknown');
        counts[value] = (counts[value] || 0) + 1;
      });

      return Object.entries(counts)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 10); // Top 10
    } catch (error) {
      console.error('Error processing chart data:', error);
      return null;
    }
  }, [selectedQueryData, chartColumn]);

  // Get available columns for chart
  const availableColumns = useMemo(() => {
    if (!selectedQueryData?.columns) return [];
    return selectedQueryData.columns;
  }, [selectedQueryData]);

  // Stats calculations
  const stats = useMemo(() => {
    const totalQueries = savedQueries?.length || 0;
    const totalRows = savedQueries?.reduce((sum, q) => sum + (q.row_count ?? q.data_preview?.length ?? 0), 0) || 0;
    const recentQueries = savedQueries?.filter(q => {
      const createdAt = new Date(q.created_at);
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return createdAt > weekAgo;
    }).length || 0;

    return { totalQueries, totalRows, recentQueries };
  }, [savedQueries]);

  if (!savedQueries?.length) {
    return <EmptyState onGoToChat={onGoToChat} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      {/* Header - Clean */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="typography-heading">Query Dashboard</h2>
          <p className="typography-caption">Manage and visualize your saved SQL queries</p>
        </div>
        <Button variant="secondary" onClick={onRefresh}>
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="dashboard-grid">
        <StatCard
          title="Total Queries"
          value={stats.totalQueries.toString()}
          change={stats.recentQueries > 0 ? `+${stats.recentQueries} this week` : undefined}
          changeType={stats.recentQueries > 0 ? 'positive' : 'neutral'}
        />
        <StatCard
          title="Total Rows"
          value={stats.totalRows.toLocaleString()}
          change={stats.totalRows > 0 ? 'Across all queries' : undefined}
        />
        <StatCard
          title="Recent Activity"
          value={stats.recentQueries.toString()}
          change="Last 7 days"
          changeType={stats.recentQueries > 0 ? 'positive' : 'neutral'}
        />
      </div>

      {/* View Mode Toggle */}
      <div className="flex items-center justify-between">
        <p className="typography-body">{savedQueries.length} saved queries</p>
        <div className="tab-nav" style={{ padding: '4px 6px' }}>
          <div className="flex space-x-sm">
            {['grid', 'list'].map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`tab-button ${viewMode === mode ? "active" : ""}`}
              >
                {mode === 'grid' ? 'Grid' : 'List'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="dashboard-layout">
        {/* Queries List */}
        <div className="lg:col-span-2">
          <div className={viewMode === 'grid' ? 'dashboard-grid' : 'space-y-lg'}>
            {savedQueries.map((query) => (
              <SavedQueryCard
                key={query.id}
                query={query}
                onSelect={setSelectedQuery}
                isSelected={selectedQuery === query.id}
              />
            ))}
          </div>
        </div>

        {/* Selected Query Details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>
          {loading ? (
            <Card className="animate-pulse card-muted">
              <div className="space-y-md">
                <div className="h-4 card-muted rounded w-3/4"></div>
                <div className="h-32 card-muted rounded"></div>
                <div className="h-4 card-muted rounded w-1/2"></div>
              </div>
            </Card>
          ) : selectedQueryData ? (
            <>
              {/* Query Info */}
              <Card className="card-muted">
                <h3 className="typography-subheading mb-4">Query Details</h3>
                <div className="space-y-md">
                  <div>
                    <p className="typography-label">Question</p>
                    <p className="typography-body">{selectedQueryData.question}</p>
                  </div>
                  <div>
                    <p className="typography-label">Rows Returned</p>
                    <p className="typography-body">{selectedQueryData.data?.length || 0}</p>
                  </div>
                  {selectedQueryData.created_at && (
                    <div>
                      <p className="typography-label">Created</p>
                      <p className="typography-body">
                        {new Date(selectedQueryData.created_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </Card>

              {/* Chart Controls */}
              {availableColumns.length > 0 && (
                <Card className="card-muted">
                  <h3 className="typography-subheading mb-4">Visualization</h3>
                  <div className="space-y-md">
                    <div>
                      <label className="typography-label">Column for Chart</label>
                      <select
                        value={chartColumn}
                        onChange={(e) => setChartColumn(e.target.value)}
                        className="input mt-1"
                      >
                        <option value="">Select a column</option>
                        {availableColumns.map((col) => (
                          <option key={col} value={col}>{col}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </Card>
              )}

              {/* Chart */}
              {chartData && (
                <BarChartVisualization 
                  data={chartData} 
                  title={`${chartColumn} Distribution`}
                />
              )}

              {/* Data Table */}
              {selectedQueryData.data?.length > 0 && (
                <Card className="card-muted">
                  <h3 className="typography-subheading mb-4">Data Preview</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="table-header">
                          {(selectedQueryData.columns || []).map((col) => (
                            <th key={col} className="text-left table-cell">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {selectedQueryData.data.slice(0, 5).map((row, idx) => (
                          <tr key={idx} className="table-row">
                            {(selectedQueryData.columns || []).map((col) => (
                              <td key={col} className="table-cell">
                                {row[col]}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {selectedQueryData.data.length > 5 && (
                      <p className="typography-caption text-center mt-3">
                        ... and {selectedQueryData.data.length - 5} more rows
                      </p>
                    )}
                  </div>
                </Card>
              )}
            </>
          ) : (
            <Card className="text-center py-8 card-muted">
              <p className="typography-body">Select a query to view details</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
