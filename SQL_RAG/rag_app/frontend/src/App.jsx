import { useState } from "react";
import Container from "@mui/material/Container";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import ChatHistory from "./components/ChatHistory.jsx";
import ChatInput from "./components/ChatInput.jsx";
import Introduction from "./components/Introduction.jsx";
import DataOverview from "./components/DataOverview.jsx";
import { runQuerySearch, executeSql } from "./services/ragClient.js";

const DEFAULT_OPTIONS = {
  k: 20,
  gemini_mode: false,
  hybrid_search: false,
  auto_adjust_weights: true,
  query_rewriting: false,
  sql_validation: true,
};

function serializeHistory(messages) {
  return messages
    .map((msg) => {
      const prefix = msg.role === "assistant" ? "Assistant" : "User";
      return `${prefix}: ${msg.content.replace(/\s+/g, " ").trim()}`;
    })
    .join("\n");
}

function TabPanel({ value, current, children, sx }) {
  return (
    <Box
      role="tabpanel"
      hidden={value !== current}
      sx={{
        display: value === current ? "flex" : "none",
        flexDirection: "column",
        flexGrow: 1,
        ...sx,
      }}
    >
      {value === current && children}
    </Box>
  );
}

function App() {
  const [conversation, setConversation] = useState([]);
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("intro");

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
      const payload = {
        question: trimmed,
        ...DEFAULT_OPTIONS,
        ...options,
        ...overrides,
        agent_type: "chat",
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
      };

      setConversation((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message || "Failed to generate response.");
      setConversation((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          role: "assistant",
          content: `⚠️ ${err.message || "Generation failed."}`,
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
              execution: { status: "loading", dryRun },
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

  return (
    <Container
      maxWidth="md"
      sx={{
        minHeight: "100vh",
        py: 4,
        display: "flex",
        flexDirection: "column",
        gap: 3,
      }}
    >
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          SQL RAG Demo
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Explore the dataset, ask questions in natural language, and review or
          execute the generated SQL.
        </Typography>
      </Box>

      <Tabs
        value={tab}
        onChange={(_, value) => setTab(value)}
        aria-label="SQL RAG sections"
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab value="intro" label="Introduction" />
        <Tab value="data" label="Data" />
        <Tab value="chat" label="Chat" />
      </Tabs>

      <TabPanel value="intro" current={tab} sx={{ gap: 2 }}>
        <Introduction />
      </TabPanel>

      <TabPanel value="data" current={tab} sx={{ gap: 2 }}>
        <DataOverview />
      </TabPanel>

      <TabPanel value="chat" current={tab} sx={{ gap: 2, flexGrow: 1 }}>
        <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
          <ChatHistory
            conversation={conversation}
            error={error}
            onExecute={handleExecute}
          />
        </Box>

        <ChatInput
          onSend={handleSend}
          isLoading={isLoading}
          options={options}
          onOptionsChange={setOptions}
        />
      </TabPanel>
    </Container>
  );
}

export default App;
