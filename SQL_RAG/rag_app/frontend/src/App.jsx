import { useState, useEffect } from "react";
import ChatHistory from "./components/ChatHistory.jsx";
import ChatInput from "./components/ChatInput.jsx";
import Introduction from "./components/Introduction.jsx";
import DataOverview from "./components/DataOverview.jsx";
import Dashboard from "./components/Dashboard.jsx";
import Button from "./components/Button.jsx";
import {
  runQuerySearch,
  executeSql,
  runQuickAnswer,
  saveQuery,
  listSavedQueries,
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
  
  const refreshSavedQueries = async () => {
    try {
      const list = await listSavedQueries();
      setSavedQueries(list);
    } catch (err) {
      console.error("Failed to load saved queries", err);
    }
  };

  useEffect(() => {
    refreshSavedQueries();
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

        const assistantMessage = {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: result.answer || "(No answer returned)",
          sql: result.sql || null,
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

        const assistantMessage = {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: quickAnswer.answer || quickAnswer.message || "(No answer returned)",
          usage: quickAnswer.usage || null,
          sources: quickAnswer.sources || [],
          sql: quickAnswer.sql || null,
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

  const handleExecute = async (messageId, { dryRun }) => {
    const message = conversation.find((msg) => msg.id === messageId);
    if (!message || !message.sql) {
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
              },
            }
          : msg
      )
    );

    try {
      const result = await executeSql({
        sql: message.sql,
        dry_run: dryRun,
        max_bytes_billed: 100_000_000,
      });

      setConversation((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                execution: {
                  status: "success",
                  result,
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
    if (!message?.sql || message.execution?.status !== "success") {
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
        sql: message.sql,
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
    </div>
  );
}

export default App;
