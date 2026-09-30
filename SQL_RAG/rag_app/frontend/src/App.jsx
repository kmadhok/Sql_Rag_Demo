import { useEffect, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import TemplatePickerModal from "./components/TemplatePickerModal.jsx";
import { applyTemplate } from "./utils/dashboardTemplates.js";
import { applyTheme } from "./utils/themes.js";
import TopBar from "./workspace/TopBar.jsx";
import AskWorkspace from "./workspace/AskWorkspace.jsx";
import { useAsk } from "./workspace/useAsk.js";
import {
  listSavedQueries,
  createDashboard,
  listDashboards,
  getDashboard,
  updateDashboard,
  duplicateDashboard,
  deleteDashboard,
} from "./services/ragClient.js";

function App() {
  const [view, setView] = useState("ask");
  const [savedQueries, setSavedQueries] = useState([]);
  const [dashboards, setDashboards] = useState([]);
  const [currentDashboard, setCurrentDashboard] = useState(null);
  const [dashboardId, setDashboardId] = useState(null);
  const [isTemplatePickerOpen, setIsTemplatePickerOpen] = useState(false);
  const askState = useAsk({ onSaved: (saved) => setSavedQueries((prev) => [saved, ...prev]) });

  // The workspace is dark-only; keep the dashboard's theme variables in sync with it.
  useEffect(() => {
    applyTheme("dark");
  }, []);

  const refreshSavedQueries = async () => {
    try {
      const list = await listSavedQueries();
      setSavedQueries(list);
    } catch (err) {
      console.error("Failed to load saved queries", err);
    }
  };

  const loadAllDashboards = async () => {
    try {
      const allDashboards = await listDashboards();
      setDashboards(allDashboards);

      if (allDashboards.length > 0) {
        // Load the most recently updated dashboard
        const dashboardToLoad = allDashboards[0];
        const dashboard = await getDashboard(dashboardToLoad.id);
        setCurrentDashboard(dashboard);
        setDashboardId(dashboard.id);
      } else {
        // Create a new default dashboard
        const newDashboard = await createDashboard({
          name: "My Dashboard",
          layout_items: [],
        });
        setCurrentDashboard(newDashboard);
        setDashboardId(newDashboard.id);
        setDashboards([newDashboard]);
      }
    } catch (err) {
      console.error("Failed to load dashboards", err);
      // Create a fallback empty dashboard
      setCurrentDashboard({ layout_items: [] });
    }
  };

  const handleSaveDashboard = async (dashboardData) => {
    if (!dashboardId) {
      // Create new dashboard
      try {
        const newDashboard = await createDashboard({
          name: "My Dashboard",
          ...dashboardData,
        });
        setCurrentDashboard(newDashboard);
        setDashboardId(newDashboard.id);
        // Update dashboards list
        setDashboards((prev) => [newDashboard, ...prev]);
      } catch (err) {
        console.error("Failed to create dashboard", err);
      }
    } else {
      // Update existing dashboard
      try {
        const updated = await updateDashboard(dashboardId, dashboardData);
        setCurrentDashboard(updated);
        // Update dashboards list
        setDashboards((prev) =>
          prev.map((d) => (d.id === dashboardId ? updated : d))
        );
      } catch (err) {
        console.error("Failed to update dashboard", err);
      }
    }
  };

  const handleSelectDashboard = async (id) => {
    try {
      const dashboard = await getDashboard(id);
      setCurrentDashboard(dashboard);
      setDashboardId(id);
    } catch (err) {
      console.error("Failed to load dashboard", err);
    }
  };

  const handleCreateDashboard = () => {
    setIsTemplatePickerOpen(true);
  };

  const handleTemplateSelect = async (templateId, dashboardName) => {
    try {
      // Apply template to get layout items
      const layoutItems = applyTemplate(templateId);

      const newDashboard = await createDashboard({
        name: dashboardName,
        layout_items: layoutItems,
      });
      setCurrentDashboard(newDashboard);
      setDashboardId(newDashboard.id);
      setDashboards((prev) => [newDashboard, ...prev]);
      setIsTemplatePickerOpen(false);
    } catch (err) {
      console.error("Failed to create dashboard", err);
      alert("Failed to create dashboard. Please try again.");
    }
  };

  const handleRenameDashboard = async (id, newName) => {
    try {
      const updated = await updateDashboard(id, { name: newName });
      setDashboards((prev) =>
        prev.map((d) => (d.id === id ? { ...d, name: newName } : d))
      );
      if (id === dashboardId) {
        setCurrentDashboard(updated);
      }
    } catch (err) {
      console.error("Failed to rename dashboard", err);
      alert("Failed to rename dashboard. Please try again.");
    }
  };

  const handleDuplicateDashboard = async (id) => {
    try {
      const duplicated = await duplicateDashboard(id);
      setDashboards((prev) => [duplicated, ...prev]);
      // Switch to the duplicated dashboard
      setCurrentDashboard(duplicated);
      setDashboardId(duplicated.id);
    } catch (err) {
      console.error("Failed to duplicate dashboard", err);
      alert("Failed to duplicate dashboard. Please try again.");
    }
  };

  const handleDeleteDashboard = async (id) => {
    try {
      await deleteDashboard(id);
      const updatedDashboards = dashboards.filter((d) => d.id !== id);
      setDashboards(updatedDashboards);

      // If deleted dashboard was active, switch to first available
      if (id === dashboardId) {
        if (updatedDashboards.length > 0) {
          const nextDashboard = await getDashboard(updatedDashboards[0].id);
          setCurrentDashboard(nextDashboard);
          setDashboardId(nextDashboard.id);
        } else {
          // No dashboards left, create a new one
          const newDashboard = await createDashboard({
            name: "My Dashboard",
            layout_items: [],
          });
          setCurrentDashboard(newDashboard);
          setDashboardId(newDashboard.id);
          setDashboards([newDashboard]);
        }
      }
    } catch (err) {
      console.error("Failed to delete dashboard", err);
      alert("Failed to delete dashboard. Please try again.");
    }
  };

  useEffect(() => {
    refreshSavedQueries();
    loadAllDashboards();
  }, []);

  return (
    <div className="flex h-dvh flex-col bg-canvas text-zinc-200">
      <TopBar view={view} onViewChange={setView} savedCount={savedQueries.length} />

      {view === "ask" ? (
        <AskWorkspace ask={askState} />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
          <Dashboard
            savedQueries={savedQueries}
            onRefresh={refreshSavedQueries}
            onGoToChat={() => setView("ask")}
            currentDashboard={currentDashboard}
            onSaveDashboard={handleSaveDashboard}
            dashboards={dashboards}
            activeDashboardId={dashboardId}
            onSelectDashboard={handleSelectDashboard}
            onCreateDashboard={handleCreateDashboard}
            onRenameDashboard={handleRenameDashboard}
            onDuplicateDashboard={handleDuplicateDashboard}
            onDeleteDashboard={handleDeleteDashboard}
          />
        </div>
      )}

      <TemplatePickerModal
        isOpen={isTemplatePickerOpen}
        onSelect={handleTemplateSelect}
        onClose={() => setIsTemplatePickerOpen(false)}
      />
    </div>
  );
}

export default App;
