import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Collapse from "@mui/material/Collapse";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Slider from "@mui/material/Slider";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import RefreshIcon from "@mui/icons-material/Refresh";

const DEFAULTS = {
  k: 20,
  gemini_mode: false,
  hybrid_search: false,
  auto_adjust_weights: true,
  query_rewriting: false,
  sql_validation: true,
};

function QueryForm({
  isLoading,
  defaultQuestion,
  defaults = DEFAULTS,
  onSubmit,
  onReset,
}) {
  const [question, setQuestion] = useState(defaultQuestion);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [form, setForm] = useState({ ...DEFAULTS, ...defaults });

  const handleToggle = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.checked }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }
    await onSubmit({
      question: question.trim(),
      ...form,
    });
    setQuestion("");
  };

  const resetForm = () => {
    setQuestion(defaultQuestion);
    setForm({ ...DEFAULTS });
    onReset?.();
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        p: 2,
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        backgroundColor: "background.paper",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="h6" component="h2">
          Ask a Question
        </Typography>
        <Tooltip title="Reset form">
          <IconButton size="small" onClick={resetForm}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <TextField
        label="Question"
        multiline
        minRows={4}
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="e.g., How many orders did we receive last month?"
      />

      <Box sx={{ display: "flex", gap: 1 }}>
        <Button
          type="submit"
          variant="contained"
          disabled={isLoading}
        >
          {isLoading ? "Generating..." : "Generate SQL"}
        </Button>
        <Button
          variant="outlined"
          onClick={() => setShowAdvanced((prev) => !prev)}
        >
          {showAdvanced ? "Hide advanced" : "Show advanced"}
        </Button>
      </Box>

      <Collapse in={showAdvanced}>
        <Box
          sx={{
            mt: 2,
            p: 2,
            borderRadius: 2,
            border: "1px dashed",
            borderColor: "divider",
            display: "grid",
            gap: 2,
          }}
        >
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Documents to retrieve (k = {form.k})
            </Typography>
            <Slider
              value={form.k}
              min={1}
              max={50}
              step={1}
              onChange={(_, value) =>
                setForm((prev) => ({ ...prev, k: value }))
              }
              valueLabelDisplay="auto"
            />
          </Box>

          <FormControlLabel
            control={
              <Switch
                checked={form.gemini_mode}
                onChange={handleToggle("gemini_mode")}
              />
            }
            label="Gemini mode (1M context)"
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.hybrid_search}
                onChange={handleToggle("hybrid_search")}
              />
            }
            label="Hybrid search (vector + keyword)"
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.auto_adjust_weights}
                onChange={handleToggle("auto_adjust_weights")}
              />
            }
            label="Auto adjust weights"
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.query_rewriting}
                onChange={handleToggle("query_rewriting")}
              />
            }
            label="Query rewriting"
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.sql_validation}
                onChange={handleToggle("sql_validation")}
              />
            }
            label="Schema-strict SQL validation"
          />
        </Box>
      </Collapse>
    </Box>
  );
}

export default QueryForm;
