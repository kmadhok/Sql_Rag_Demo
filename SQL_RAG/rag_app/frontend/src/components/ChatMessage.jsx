import { useMemo } from "react";
import Stack from "@mui/material/Stack";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

function MessageContainer({ align, children }) {
  return (
    <Stack direction="row" justifyContent={align === "end" ? "flex-end" : "flex-start"}>
      {children}
    </Stack>
  );
}

function UsageChips({ usage }) {
  if (!usage) {
    return null;
  }

  const chips = [
    usage.total_tokens != null && {
      label: `Tokens: ${usage.total_tokens.toLocaleString()}`,
    },
    usage.retrieval_time != null && {
      label: `Retrieval: ${usage.retrieval_time.toFixed(2)}s`,
    },
    usage.generation_time != null && {
      label: `Generation: ${usage.generation_time.toFixed(2)}s`,
    },
    usage.documents_retrieved != null && {
      label: `Docs: ${usage.documents_retrieved}`,
    },
    usage.search_method && {
      label: `Search: ${usage.search_method}`,
    },
  ].filter(Boolean);

  if (chips.length === 0) {
    return null;
  }

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap">
      {chips.map((chip, idx) => (
        <Chip key={idx} label={chip.label} size="small" variant="outlined" />
      ))}
    </Stack>
  );
}

function SourcesAccordion({ sources }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Accordion variant="outlined" sx={{ mt: 2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography>
          Source Chunks ({sources.length})
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={2}>
          {sources.map((source, index) => (
            <Box key={index}>
              <Typography variant="subtitle2" gutterBottom>
                Chunk {index + 1} — {source.metadata?.description || "Source"}
              </Typography>
              <Typography component="pre" sx={{ whiteSpace: "pre-wrap" }}>
                {source.content}
              </Typography>
              {source.metadata && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {Object.entries(source.metadata)
                    .filter(([, value]) => value)
                    .map(([key, value]) => `${key}: ${value}`)
                    .join(" • ")}
                </Typography>
              )}
            </Box>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

function ExecutionStatus({ execution }) {
  if (!execution) {
    return null;
  }

  if (execution.status === "loading") {
    return (
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 2 }}>
        <CircularProgress size={18} />
        <Typography variant="body2">Executing...</Typography>
      </Stack>
    );
  }

  if (execution.status === "error") {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {execution.error || "Execution failed."}
      </Alert>
    );
  }

  if (execution.status === "success" && execution.result) {
    const { result } = execution;
    return (
      <Paper variant="outlined" sx={{ mt: 2, p: 1.5 }}>
        <Typography variant="subtitle2" gutterBottom>
          Execution Summary
        </Typography>
        <Stack spacing={0.25}>
          {result.bytes_processed != null && (
            <Typography variant="body2">
              Bytes processed: {result.bytes_processed.toLocaleString()}
            </Typography>
          )}
          {result.bytes_billed != null && (
            <Typography variant="body2">
              Bytes billed: {result.bytes_billed.toLocaleString()}
            </Typography>
          )}
          {result.total_rows != null && (
            <Typography variant="body2">
              Total rows: {result.total_rows.toLocaleString()}
            </Typography>
          )}
          {result.execution_time != null && (
            <Typography variant="body2">
              Execution time: {result.execution_time.toFixed(2)}s
            </Typography>
          )}
          {result.cache_hit != null && (
            <Typography variant="body2">
              Cache hit: {result.cache_hit ? "Yes" : "No"}
            </Typography>
          )}
          {result.job_id && (
            <Typography variant="caption" color="text.secondary">
              Job ID: {result.job_id}
            </Typography>
          )}
        </Stack>
        {result.data && result.data.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="subtitle2">Sample rows</Typography>
            <Typography component="pre" sx={{ whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto" }}>
              {JSON.stringify(result.data.slice(0, 5), null, 2)}
            </Typography>
          </Box>
        )}
      </Paper>
    );
  }

  return null;
}

function ChatMessage({ message, onExecute }) {
  const isUser = message.role === "user";
  const alignment = isUser ? "end" : "start";
  const bubbleSx = useMemo(() => {
    if (isUser) {
      return {
        backgroundColor: "primary.main",
        color: "primary.contrastText",
      };
    }
    return {
      backgroundColor: "background.paper",
      color: "text.primary",
    };
  }, [isUser]);

  return (
    <MessageContainer align={alignment}>
      <Paper
        elevation={0}
        sx={{
          ...bubbleSx,
          px: 2,
          py: 1.5,
          borderRadius: 3,
          maxWidth: "80%",
          border: isUser ? "none" : "1px solid",
          borderColor: isUser ? "transparent" : "divider",
        }}
      >
        <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
          {message.content}
        </Typography>

        {!isUser && message.sql && (
          <Box sx={{ mt: 2 }}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              spacing={1}
            >
              <Typography variant="subtitle2">Generated SQL</Typography>
              <Tooltip title="Copy SQL to clipboard">
                <IconButton
                  size="small"
                  onClick={() => navigator.clipboard.writeText(message.sql || "")}
                >
                  <ContentCopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
            <Paper
              variant="outlined"
              sx={{
                mt: 1,
                p: 1.5,
                backgroundColor: "background.default",
                color: "text.primary",
              }}
            >
              <Typography component="pre" sx={{ whiteSpace: "pre-wrap", fontFamily: "monospace", m: 0 }}>
                {message.sql}
              </Typography>
            </Paper>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <Button
                size="small"
                variant="contained"
                onClick={() => onExecute?.(message.id, { dryRun: false })}
                disabled={message.execution?.status === "loading"}
              >
                Execute
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => onExecute?.(message.id, { dryRun: true })}
                disabled={message.execution?.status === "loading"}
              >
                Dry run
              </Button>
            </Stack>
          </Box>
        )}

        {!isUser && message.usage && (
          <Box sx={{ mt: 2 }}>
            <UsageChips usage={message.usage} />
          </Box>
        )}

        {!isUser && <ExecutionStatus execution={message.execution} />}

        {!isUser && <SourcesAccordion sources={message.sources} />}
      </Paper>
    </MessageContainer>
  );
}

export default ChatMessage;
