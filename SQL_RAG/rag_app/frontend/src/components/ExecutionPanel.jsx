import { useState } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Alert from "@mui/material/Alert";

function SummaryItem({ label, value }) {
  if (value === undefined || value === null) {
    return null;
  }
  return (
    <Typography variant="body2">
      <strong>{label}:</strong> {value}
    </Typography>
  );
}

function ExecutionPanel({ sql, onExecute, executionState }) {
  const [dryRun, setDryRun] = useState(false);
  const [maxBytesBilled, setMaxBytesBilled] = useState(100_000_000);

  if (!sql) {
    return null;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onExecute({ sql, dryRun, maxBytesBilled });
  };

  const { isLoading, error, data } = executionState;

  return (
    <Paper
      variant="outlined"
      component="form"
      onSubmit={handleSubmit}
      sx={{ p: 2, mb: 2 }}
    >
      <Typography variant="h6" gutterBottom>
        Execute SQL
      </Typography>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <FormControlLabel
          control={
            <Switch
              checked={dryRun}
              onChange={(event) => setDryRun(event.target.checked)}
            />
          }
          label="Dry run (estimate cost only)"
        />

        <TextField
          label="Max bytes billed"
          type="number"
          value={maxBytesBilled}
          onChange={(event) =>
            setMaxBytesBilled(Number(event.target.value) || 0)
          }
          InputProps={{ inputProps: { min: 10_000_000, step: 10_000_000 } }}
        />

        <Button
          type="submit"
          variant="contained"
          disabled={isLoading}
        >
          {isLoading ? "Running..." : dryRun ? "Dry run" : "Execute"}
        </Button>

        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}

        {data && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Execution Summary
            </Typography>
            <SummaryItem label="Success" value={data.success ? "Yes" : "No"} />
            <SummaryItem label="Bytes processed" value={data.bytes_processed?.toLocaleString()} />
            <SummaryItem label="Bytes billed" value={data.bytes_billed?.toLocaleString()} />
            <SummaryItem label="Total rows" value={data.total_rows?.toLocaleString()} />
            <SummaryItem label="Execution time" value={data.execution_time ? `${data.execution_time.toFixed(2)}s` : undefined} />
            <SummaryItem label="Cache hit" value={data.cache_hit != null ? (data.cache_hit ? "Yes" : "No") : undefined} />
            <SummaryItem label="Job ID" value={data.job_id} />
            {data.data && data.data.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Sample rows</Typography>
                <Typography component="pre" sx={{ whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(data.data.slice(0, 5), null, 2)}
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </Box>
    </Paper>
  );
}

export default ExecutionPanel;
