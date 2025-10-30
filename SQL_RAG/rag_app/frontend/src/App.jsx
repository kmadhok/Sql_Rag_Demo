import { useState } from "react";
import Container from "@mui/material/Container";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Link from "@mui/material/Link";
import Grid from "@mui/material/Grid2";

import QueryForm from "./components/QueryForm.jsx";
import SqlPreview from "./components/SqlPreview.jsx";
import SourcesList from "./components/SourcesList.jsx";
import ExecutionPanel from "./components/ExecutionPanel.jsx";
import UsageSummary from "./components/UsageSummary.jsx";
import { useQuerySearch } from "./hooks/useQuerySearch.js";
import { useSqlExecution } from "./hooks/useSqlExecution.js";

function TabPanel({ value, current, children }) {
  if (value !== current) {
    return null;
  }
  return <Box sx={{ pt: 2 }}>{children}</Box>;
}

function App() {
  const [tab, setTab] = useState(0);
  const {
    state: queryState,
    submitQuery,
    resetQuery,
  } = useQuerySearch();
  const {
    state: execState,
    executeSql,
    resetExecution,
  } = useSqlExecution();

  const handleQuestionSubmit = async (payload) => {
    resetExecution();
    await submitQuery(payload);
  };

  const handleExecute = async ({ sql, dryRun, maxBytesBilled }) => {
    await executeSql({ sql, dryRun, maxBytesBilled });
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          SQL RAG Demo
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Ask natural-language questions, review the generated SQL, and execute
          safely against BigQuery. This UI talks to the FastAPI service you just
          deployed.
        </Typography>
      </Box>

      <Tabs
        value={tab}
        onChange={(_, value) => setTab(value)}
        aria-label="query tabs"
      >
        <Tab label="Query Search" />
        <Tab label="Settings" />
      </Tabs>

      <TabPanel value={tab} current={0}>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 5 }}>
            <QueryForm
              isLoading={queryState.isLoading}
              defaultQuestion="Show top customers by lifetime spend"
              defaults={queryState.lastPayload}
              onSubmit={handleQuestionSubmit}
              onReset={() => {
                resetQuery();
                resetExecution();
              }}
            />

            <UsageSummary usage={queryState.data?.usage} />
          </Grid>

          <Grid size={{ xs: 12, md: 7 }}>
            <SqlPreview
              answer={queryState.data?.answer}
              sql={queryState.data?.sql}
              error={queryState.error}
              isLoading={queryState.isLoading}
            />

            <ExecutionPanel
              sql={queryState.data?.sql}
              onExecute={handleExecute}
              executionState={execState}
            />

            <SourcesList sources={queryState.data?.sources} />
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tab} current={1}>
        <Typography variant="body1" paragraph>
          This demo currently uses a single FAISS index (
          <code>{import.meta.env.VITE_VECTOR_STORE_NAME || "default"}</code>) and
          calls the API at{" "}
          <code>{import.meta.env.VITE_API_BASE_URL || "http://localhost:8080"}</code>.
          Edit <code>frontend/.env.local</code> to point at another deployment
          without rebuilding.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Need more controls (hybrid search, rewriting weights, table
          exclusions)? Wire them into <code>QueryForm</code> — the FastAPI
          endpoint already supports the same payloads Streamlit does.
        </Typography>
        <Box sx={{ mt: 3 }}>
          <Link
            href="http://localhost:8080/docs"
            target="_blank"
            rel="noreferrer"
          >
            Open FastAPI docs
          </Link>
        </Box>
      </TabPanel>
    </Container>
  );
}

export default App;
