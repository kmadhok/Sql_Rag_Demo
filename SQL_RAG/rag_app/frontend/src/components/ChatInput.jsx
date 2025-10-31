import { useState } from "react";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Collapse from "@mui/material/Collapse";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Slider from "@mui/material/Slider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Divider from "@mui/material/Divider";
import Button from "@mui/material/Button";
import SettingsIcon from "@mui/icons-material/Settings";
import SendIcon from "@mui/icons-material/Send";

const DEFAULT_OPTIONS = {
  k: 20,
  gemini_mode: false,
  hybrid_search: false,
  auto_adjust_weights: true,
  query_rewriting: false,
  sql_validation: true,
};

function ChatInput({ onSend, isLoading, options, onOptionsChange }) {
  const [message, setMessage] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const mergedOptions = { ...DEFAULT_OPTIONS, ...options };

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isLoading) {
      return;
    }
    onSend(trimmed, mergedOptions);
    setMessage("");
  };

  const handleToggle = (field) => (event) => {
    const nextOptions = { ...mergedOptions, [field]: event.target.checked };
    onOptionsChange(nextOptions);
  };

  const handleSlider = (_, value) => {
    const nextOptions = { ...mergedOptions, k: value };
    onOptionsChange(nextOptions);
  };

  return (
    <Paper
      component="form"
      onSubmit={handleSubmit}
      elevation={3}
      sx={{ p: 2, borderRadius: 3 }}
    >
      <Stack spacing={1.5}>
        <TextField
          label="Ask a question"
          placeholder="e.g., What was the monthly revenue last quarter?"
          multiline
          minRows={2}
          maxRows={6}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />

        <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="center">
          <Tooltip title={showOptions ? "Hide advanced settings" : "Show advanced settings"}>
            <IconButton onClick={() => setShowOptions((prev) => !prev)}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>

          <Button
            type="submit"
            variant="contained"
            endIcon={<SendIcon />}
            disabled={isLoading || !message.trim()}
          >
            {isLoading ? "Generating" : "Send"}
          </Button>
        </Stack>

        <Collapse in={showOptions}>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              border: "1px dashed",
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <Stack spacing={2}>
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Box>
                    <strong>Documents retrieved</strong>
                  </Box>
                  <Box>{mergedOptions.k}</Box>
                </Stack>
                <Slider
                  value={mergedOptions.k}
                  min={1}
                  max={50}
                  step={1}
                  onChange={handleSlider}
                  valueLabelDisplay="auto"
                />
              </Box>

              <Divider flexItem />

              <FormControlLabel
                control={
                  <Switch
                    checked={mergedOptions.gemini_mode}
                    onChange={handleToggle("gemini_mode")}
                  />
                }
                label="Gemini mode (1M context)"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={mergedOptions.hybrid_search}
                    onChange={handleToggle("hybrid_search")}
                  />
                }
                label="Hybrid search"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={mergedOptions.auto_adjust_weights}
                    onChange={handleToggle("auto_adjust_weights")}
                  />
                }
                label="Auto adjust weights"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={mergedOptions.query_rewriting}
                    onChange={handleToggle("query_rewriting")}
                  />
                }
                label="Query rewriting"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={mergedOptions.sql_validation}
                    onChange={handleToggle("sql_validation")}
                  />
                }
                label="Schema-strict SQL validation"
              />
            </Stack>
          </Box>
        </Collapse>
      </Stack>
    </Paper>
  );
}

export default ChatInput;
