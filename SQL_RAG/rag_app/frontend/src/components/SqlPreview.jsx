import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Skeleton from "@mui/material/Skeleton";
import Paper from "@mui/material/Paper";

function SqlPreview({ answer, sql, error, isLoading }) {
  if (isLoading) {
    return (
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">LLM Answer</Typography>
        <Skeleton variant="rectangular" height={120} sx={{ my: 2 }} />
        <Skeleton variant="rectangular" height={120} />
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!answer && !sql) {
    return (
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography color="text.secondary">
          Submit a question to see results.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mb: 2 }}>
      {answer && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            LLM Answer
          </Typography>
          <Typography component="pre" sx={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
            {answer}
          </Typography>
        </Paper>
      )}

      {sql && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Generated SQL
          </Typography>
          <Typography component="pre" sx={{ whiteSpace: "pre-wrap", fontFamily: "monospace" }}>
            {sql}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

export default SqlPreview;
