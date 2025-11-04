import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import Button from './Button.jsx';
import Card, { StatCard } from './Card.jsx';
import ChartCard from './ChartCard.jsx';
import AddVisualizationModal from './AddVisualizationModal.jsx';
import ChartConfigPanel from './ChartConfigPanel.jsx';
import DashboardSelector from './DashboardSelector.jsx';
import ExportMenu from './ExportMenu.jsx';
import { exportAsPNG, exportAsPDF, exportAsJSON } from '../utils/exportDashboard.js';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

/* Empty State */
function EmptyDashboardState({ onAddChart }) {
  return (
    <div className="text-center py-16 surface-panel-light rounded-lg border border-gray-700 border-dashed">
      <div className="max-w-md mx-auto">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          className="mx-auto mb-4 opacity-30"
        >
          <rect x="8" y="8" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="2" />
          <rect x="36" y="8" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="2" />
          <rect x="8" y="36" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="2" />
          <rect x="36" y="36" width="20" height="20" rx="4" stroke="currentColor" strokeWidth="2" />
        </svg>
        <h3 className="typography-heading mb-3">Your Dashboard is Empty</h3>
        <p className="typography-body text-gray-400 mb-6">
          Add your first visualization to get started. You can create charts from saved queries.
        </p>
        <Button variant="primary" onClick={onAddChart}>
          + Add Visualization
        </Button>
      </div>
    </div>
  );
}

/* Main Dashboard Component */
export default function Dashboard({
  savedQueries,
  onRefresh,
  onGoToChat,
  currentDashboard,
  onSaveDashboard,
  dashboards,
  activeDashboardId,
  onSelectDashboard,
  onCreateDashboard,
  onRenameDashboard,
  onDuplicateDashboard,
  onDeleteDashboard,
}) {
  // Layout state
  const [layout, setLayout] = useState([]);
  const [chartItems, setChartItems] = useState([]);

  // Modal states
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  // Auto-save debounce
  const [saveTimeout, setSaveTimeout] = useState(null);

  // Export state
  const [isExporting, setIsExporting] = useState(false);
  const dashboardRef = useRef(null);

  // Load dashboard from currentDashboard prop
  useEffect(() => {
    if (currentDashboard && currentDashboard.layout_items) {
      const items = currentDashboard.layout_items.map((item) => ({
        i: item.i,
        savedQueryId: item.saved_query_id || item.savedQueryId,
        queryQuestion: item.query_question || item.queryQuestion,
        chartConfig: item.chart_config || item.chartConfig,
      }));

      setChartItems(items);

      const gridLayout = currentDashboard.layout_items.map((item) => ({
        i: item.i,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
      }));

      setLayout(gridLayout);
    }
  }, [currentDashboard]);

  // Stats calculations
  const stats = useMemo(() => {
    const totalQueries = savedQueries?.length || 0;
    const totalRows =
      savedQueries?.reduce((sum, q) => sum + (q.row_count ?? 0), 0) || 0;
    const recentQueries =
      savedQueries?.filter((q) => {
        const createdAt = new Date(q.created_at);
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        return createdAt > weekAgo;
      }).length || 0;

    return { totalQueries, totalRows, recentQueries };
  }, [savedQueries]);

  // Handle layout change (drag/resize)
  const handleLayoutChange = useCallback((newLayout) => {
    setLayout(newLayout);

    // Auto-save after 500ms of inactivity
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }

    const timeout = setTimeout(() => {
      saveDashboard(newLayout, chartItems);
    }, 500);

    setSaveTimeout(timeout);
  }, [saveTimeout, chartItems]);

  // Save dashboard
  const saveDashboard = useCallback((layoutToSave = layout, chartItemsToSave = chartItems) => {
    if (!layoutToSave || layoutToSave.length === 0) {
      return;
    }

    const layoutItems = layoutToSave.map((gridItem) => {
      const chartItem = chartItemsToSave.find((c) => c.i === gridItem.i);
      return {
        i: gridItem.i,
        x: gridItem.x,
        y: gridItem.y,
        w: gridItem.w,
        h: gridItem.h,
        saved_query_id: chartItem?.savedQueryId || '',
        query_question: chartItem?.queryQuestion || '',
        chart_config: chartItem?.chartConfig || {},
      };
    });

    if (onSaveDashboard) {
      onSaveDashboard({ layout_items: layoutItems });
    }
  }, [layout, chartItems, onSaveDashboard]);

  // Add new chart
  const handleAddChart = useCallback((chartData) => {
    const itemId = `chart-${Date.now()}`;

    // Find next available Y position
    const maxY = layout.reduce((max, item) => Math.max(max, item.y + item.h), 0);

    const newChartItem = {
      i: itemId,
      savedQueryId: chartData.savedQueryId,
      queryQuestion: chartData.queryQuestion,
      chartConfig: chartData.chartConfig,
    };

    const newLayoutItem = {
      i: itemId,
      x: 0,
      y: maxY,
      w: 6,
      h: 2,
      minW: 3,
      minH: 2,
    };

    // Calculate updated arrays before setting state
    const updatedChartItems = [...chartItems, newChartItem];
    const updatedLayout = [...layout, newLayoutItem];

    setChartItems(updatedChartItems);
    setLayout(updatedLayout);

    // Save immediately with the updated arrays
    setTimeout(() => {
      saveDashboard(updatedLayout, updatedChartItems);
    }, 100);
  }, [layout, chartItems, saveDashboard]);

  // Remove chart
  const handleRemoveChart = useCallback((itemId) => {
    // Calculate updated arrays before setting state
    const updatedChartItems = chartItems.filter((item) => item.i !== itemId);
    const updatedLayout = layout.filter((item) => item.i !== itemId);

    setChartItems(updatedChartItems);
    setLayout(updatedLayout);

    // Save immediately with the updated arrays
    setTimeout(() => {
      saveDashboard(updatedLayout, updatedChartItems);
    }, 100);
  }, [layout, chartItems, saveDashboard]);

  // Configure chart
  const handleConfigureChart = useCallback((itemId) => {
    const item = chartItems.find((c) => c.i === itemId);
    if (item) {
      setEditingItem(item);
      setIsConfigPanelOpen(true);
    }
  }, [chartItems]);

  // Save chart configuration
  const handleSaveChartConfig = useCallback((newConfig) => {
    if (!editingItem) return;

    // Calculate updated chartItems before setting state
    const updatedChartItems = chartItems.map((item) =>
      item.i === editingItem.i
        ? { ...item, chartConfig: newConfig }
        : item
    );

    setChartItems(updatedChartItems);

    // Save immediately with updated chartItems
    setTimeout(() => {
      saveDashboard(layout, updatedChartItems);
    }, 100);

    setEditingItem(null);
  }, [editingItem, chartItems, layout, saveDashboard]);

  // Export handlers
  const handleExportPNG = useCallback(async () => {
    if (!dashboardRef.current) return;

    setIsExporting(true);
    const dashboardName = currentDashboard?.name || 'dashboard';
    const result = await exportAsPNG(dashboardRef.current, dashboardName);
    setIsExporting(false);

    if (!result.success) {
      alert(`Failed to export as PNG: ${result.error}`);
    }
  }, [currentDashboard]);

  const handleExportPDF = useCallback(async () => {
    if (!dashboardRef.current) return;

    setIsExporting(true);
    const dashboardName = currentDashboard?.name || 'dashboard';
    const result = await exportAsPDF(dashboardRef.current, dashboardName, 'landscape');
    setIsExporting(false);

    if (!result.success) {
      alert(`Failed to export as PDF: ${result.error}`);
    }
  }, [currentDashboard]);

  const handleExportJSON = useCallback(async () => {
    const dashboardName = currentDashboard?.name || 'dashboard';
    const result = exportAsJSON(currentDashboard, dashboardName);

    if (!result.success) {
      alert(`Failed to export as JSON: ${result.error}`);
    }
  }, [currentDashboard]);

  return (
    <div ref={dashboardRef} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <DashboardSelector
            dashboards={dashboards || []}
            activeDashboardId={activeDashboardId}
            onSelect={onSelectDashboard}
            onCreate={onCreateDashboard}
            onRename={onRenameDashboard}
            onDuplicate={onDuplicateDashboard}
            onDelete={onDeleteDashboard}
          />
          <p className="typography-caption" style={{ marginTop: 'var(--space-sm)' }}>
            Drag and resize charts to customize your view
          </p>
        </div>
        <div className="flex gap-3">
          <ExportMenu
            onExportPNG={handleExportPNG}
            onExportPDF={handleExportPDF}
            onExportJSON={handleExportJSON}
            isExporting={isExporting}
          />
          <Button variant="secondary" onClick={onRefresh}>
            Refresh
          </Button>
          <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
            + Add Visualization
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="dashboard-grid">
        <StatCard
          title="Total Queries"
          value={stats.totalQueries.toString()}
          change={
            stats.recentQueries > 0 ? `+${stats.recentQueries} this week` : undefined
          }
          changeType={stats.recentQueries > 0 ? 'positive' : 'neutral'}
        />
        <StatCard
          title="Total Rows"
          value={stats.totalRows.toLocaleString()}
          change={stats.totalRows > 0 ? 'Across all queries' : undefined}
        />
        <StatCard
          title="Charts"
          value={chartItems.length.toString()}
          change="Active visualizations"
          changeType={chartItems.length > 0 ? 'positive' : 'neutral'}
        />
      </div>

      {/* Chart Grid */}
      {chartItems.length === 0 ? (
        <EmptyDashboardState onAddChart={() => setIsAddModalOpen(true)} />
      ) : (
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: layout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={100}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".drag-handle"
          isDraggable
          isResizable
          compactType="vertical"
          preventCollision={false}
        >
          {chartItems.map((item) => (
            <div key={item.i} data-grid={layout.find((l) => l.i === item.i)}>
              <ChartCard
                itemId={item.i}
                savedQueryId={item.savedQueryId}
                queryQuestion={item.queryQuestion}
                chartConfig={item.chartConfig}
                onConfigure={handleConfigureChart}
                onRemove={handleRemoveChart}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      )}

      {/* Add Visualization Modal */}
      <AddVisualizationModal
        isOpen={isAddModalOpen}
        savedQueries={savedQueries || []}
        onAdd={handleAddChart}
        onClose={() => setIsAddModalOpen(false)}
      />

      {/* Chart Configuration Panel */}
      {editingItem && (
        <ChartConfigPanel
          isOpen={isConfigPanelOpen}
          savedQueryId={editingItem.savedQueryId}
          queryQuestion={editingItem.queryQuestion}
          chartConfig={editingItem.chartConfig}
          onSave={handleSaveChartConfig}
          onClose={() => {
            setIsConfigPanelOpen(false);
            setEditingItem(null);
          }}
        />
      )}
    </div>
  );
}
