import { useState, useEffect } from "react";
import ChatHistory from "./components/ChatHistory.jsx";
import ChatInput from "./components/ChatInput.jsx";
import Introduction from "./components/Introduction.jsx";
import DataOverview from "./components/DataOverview.jsx";
import Dashboard from "./components/Dashboard.jsx";
import Button from "./components/Button.jsx";
import TemplatePickerModal from "./components/TemplatePickerModal.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import { applyTemplate } from "./utils/dashboardTemplates.js";
import { initializeTheme } from "./utils/themes.js";
import { extractSql } from "./utils/sqlExtractor.js";
import {
  runQuerySearch,
  executeSql,
  runQuickAnswer,
  saveQuery,
  listSavedQueries,
  createDashboard,
  listDashboards,
  getDashboard,
  updateDashboard,
  duplicateDashboard,
  deleteDashboard,
} from "./services/ragClient.js";

const DEFAULT_OPTIONS = {
  k: 20,
  gemini_mode: false,
  hybrid_search: false,
  auto_adjust_weights: true,
  query_rewriting: false,
  sql_validation: true,
};

function isStructuredQuery(prompt) {
  return /@create/i.test(prompt);
}

function serializeHistory(messages) {
  return messages
    .map((msg) => {
      const prefix = msg.role === "assistant" ? "Assistant" : "User";
      return `${prefix}: ${msg.content.replace(/\s+/g, " ").trim()}`;
    })
    .join("\n");
}

function TabPanel({ value, current, className = "", children }) {
  const isActive = value === current;
  return (
    <div
      className={`flex flex-col flex-1 ${isActive ? "" : "hidden"} ${className}`.trim()}
      aria-hidden={!isActive}
    >
      {isActive ? children : null}
    </div>
  );
}

/**
 * Clean Tab Navigation - No Icons
 */
const TabNavigation = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'intro', label: 'Introduction' },
    { id: 'data', label: 'Data' },
    { id: 'chat', label: 'Chat' },
    { id: 'dashboard', label: 'Dashboard' },
  ];

  return (
    <nav className="tab-nav">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          type="button"
          className={`tab-button ${activeTab === tab.id ? "active" : ""}`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
};

function App() {
  const [conversation, setConversation] = useState([]);
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("intro");
  const [savedQueries, setSavedQueries] = useState([]);
  const [dashboards, setDashboards] = useState([]);
  const [currentDashboard, setCurrentDashboard] = useState(null);
  const [dashboardId, setDashboardId] = useState(null);
  const [isTemplatePickerOpen, setIsTemplatePickerOpen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(() => initializeTheme());

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

  const handleSend = async (question, overrides) => {
    const trimmed = question.trim();
    if (!trimmed) {
      return;
    }

    const userMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content: trimmed,
    };

    const conversationWithUser = [...conversation, userMessage];
    setConversation(conversationWithUser);
    setIsLoading(true);
    setError(null);

    try {
      const structured = isStructuredQuery(trimmed);

      if (structured) {
        const payload = {
          llm_model: "gemini-2.5-pro",
          question: trimmed,
          ...DEFAULT_OPTIONS,
          ...options,
          ...overrides,
          agent_type: "create",
          conversation_context: serializeHistory(conversationWithUser),
        };

        const result = await runQuerySearch(payload);

        // Prefer cleaned_sql from backend (LLM-extracted), fallback to regular extraction
        const sqlToStore = result.cleaned_sql || result.sql || extractSql(result.answer);

        const assistantMessage = {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: result.answer || "(No answer returned)",
          sql: sqlToStore,
          rawAnswer: result.answer,  // Keep raw answer for reference
          usage: result.usage || null,
          sources: result.sources || [],
          payload,
          question: trimmed,
        };

        setConversation((prev) => [...prev, assistantMessage]);
      } else {
        const quickAnswer = await runQuickAnswer({
          question: trimmed,
          conversation_context: serializeHistory(conversationWithUser),
          llm_model: "gemini-2.5-flash",
          k: overrides?.k ?? options.k ?? DEFAULT_OPTIONS.k,
        });

        // Extract SQL from answer if not provided separately
        const answerText = quickAnswer.answer || quickAnswer.message || "(No answer returned)";
        const sqlToStore = quickAnswer.sql || extractSql(answerText);

        const assistantMessage = {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: answerText,
          usage: quickAnswer.usage || null,
          sources: quickAnswer.sources || [],
          sql: sqlToStore,
          mode: "concise",
          question: trimmed,
        };

        setConversation((prev) => [...prev, assistantMessage]);
      }
    } catch (err) {
      setError(err.message || "Failed to generate response.");
      setConversation((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          role: "assistant",
          content: `Error: ${err.message || "Generation failed."}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecute = async (messageId, { dryRun, sql }) => {
    const message = conversation.find((msg) => msg.id === messageId);
    if (!message) {
      return;
    }

    // Use SQL from parameter (extracted by ChatMessage) or message.sql
    const sqlToExecute = sql || message.sql;
    if (!sqlToExecute) {
      console.error("No SQL found to execute");
      return;
    }

    setConversation((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              execution: {
                status: "loading",
                dryRun,
                result: undefined,
                saving: "idle",
                savedQueryId: msg.execution?.savedQueryId,
                savedError: undefined,
                sql: sqlToExecute,
              },
            }
          : msg
      )
    );

    try {
      const response = await executeSql({
        sql: sqlToExecute,
        dry_run: dryRun,
        max_bytes_billed: 100_000_000,
      });

      // Transform backend response (flat structure) to match frontend expectations (nested structure)
      const transformedResult = {
        data: response.data || [],
        columns: response.data && response.data.length > 0
          ? Object.keys(response.data[0])
          : [],
        row_count: response.total_rows || 0,
        job_id: response.job_id,
        bytes_processed: response.bytes_processed,
        bytes_billed: response.bytes_billed,
        execution_time: response.execution_time,
        cache_hit: response.cache_hit,
        dry_run: response.dry_run,
      };

      setConversation((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                execution: {
                  status: "success",
                  result: transformedResult,
                  saving: "idle",
                  savedQueryId: msg.execution?.savedQueryId,
                  savedError: undefined,
                },
              }
            : msg
        )
      );
    } catch (err) {
      setConversation((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                execution: {
                  status: "error",
                  error: err.message || "Execution failed.",
                },
              }
            : msg
        )
      );
    }
  };

  const handleSaveToDashboard = async (messageId) => {
    const message = conversation.find((msg) => msg.id === messageId);

    // Get SQL from message or execution
    const sqlToSave = message?.sql || message?.execution?.sql;

    if (!sqlToSave || message.execution?.status !== "success") {
      return;
    }

    setConversation((prev) =>
      prev.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              execution: {
                ...msg.execution,
                saving: "pending",
                savedError: undefined,
              },
            }
          : msg
      )
    );

    try {
      const payload = {
        question: message.question || message.content,
        sql: sqlToSave,
        data: message.execution.result?.data || [],
      };
      const saved = await saveQuery(payload);
      setConversation((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
              execution: {
                ...msg.execution,
                saving: "idle",
                savedQueryId: saved.id,
                savedError: undefined,
              },
            }
          : msg
        )
      );
      setSavedQueries((prev) => [saved, ...prev]);
    } catch (err) {
      setConversation((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
              execution: {
                ...msg.execution,
                saving: "idle",
                savedError: err.message || "Failed to save",
              },
            }
          : msg
        )
      );
    }
  };

  return (
    <div className="min-h-screen text-white">
      {/* Clean Header */}
      <header className="app-header">
        <div className="container" style={{ padding: "16px 20px" }}>
          <div className="flex justify-between items-center">
            <div>
              <h1 className="typography-heading" style={{ marginBottom: 0 }}>SQL RAG</h1>
              <p className="typography-caption" style={{ marginBottom: 0 }}>Data Assistant</p>
            </div>
            
            {/* Header Actions - No icons */}
            <div className="flex space-x-sm">
              <ThemeToggle
                currentTheme={currentTheme}
                onToggle={setCurrentTheme}
              />
              <Button variant="secondary" size="sm">
                Settings
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container" style={{ padding: "32px 20px 48px" }}>
        {/* Hero Section - Clean */}
        <div className="hero-intro animate-fade-in-up">
          <h2 className="typography-hero">
            Explore Data with Natural Language
          </h2>
          <p className="typography-body" style={{ maxWidth: "580px", margin: "0 auto var(--space-lg)" }}>
            Ask questions and get instant SQL queries. Your AI-powered data assistant.
          </p>
        </div>

        {/* Navigation Tabs - Clean */}
        <div className="animate-fade-in-up stagger-1" style={{ marginBottom: "28px" }}>
          <TabNavigation activeTab={tab} onTabChange={setTab} />
        </div>

        {/* Tab Content */}
        <div className="animate-fade-in-up stagger-2" style={{ gap: "20px", display: "flex", flexDirection: "column" }}>
          <TabPanel value="intro" current={tab}>
            <div className="surface-panel-light p-6 md:p-8">
              <Introduction />
            </div>
          </TabPanel>

          <TabPanel value="data" current={tab}>
            <div className="surface-panel p-6 md:p-8">
              <DataOverview />
            </div>
          </TabPanel>

          <TabPanel value="chat" current={tab} className="min-h-[520px]">
            <div className="surface-panel flex flex-col h-full p-4 md:p-6">
              <div className="flex-1 overflow-hidden mb-3">
                <ChatHistory
                  conversation={conversation}
                  error={error}
                  onExecute={handleExecute}
                  onSave={handleSaveToDashboard}
                />
              </div>
              <div className="shrink-0">
                <ChatInput
                  onSend={handleSend}
                  isLoading={isLoading}
                  options={options}
                  onOptionsChange={setOptions}
                />
              </div>
            </div>
          </TabPanel>

          <TabPanel value="dashboard" current={tab}>
            <div className="surface-panel-light p-6 md:p-8">
              <Dashboard
                savedQueries={savedQueries}
                onRefresh={refreshSavedQueries}
                onGoToChat={() => setTab("chat")}
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
          </TabPanel>
        </div>
      </main>

      {/* Clean Footer */}
      <footer className="app-footer" style={{ marginTop: "56px" }}>
        <div className="container" style={{ padding: "18px 20px" }}>
          <p className="typography-caption" style={{ textAlign: "center", marginBottom: 0 }}>
            Powered by AI • Built with React &amp; FastAPI
          </p>
        </div>
      </footer>

      {/* Template Picker Modal */}
      <TemplatePickerModal
        isOpen={isTemplatePickerOpen}
        onSelect={handleTemplateSelect}
        onClose={() => setIsTemplatePickerOpen(false)}
      />
    </div>
  );
}

export default App;
