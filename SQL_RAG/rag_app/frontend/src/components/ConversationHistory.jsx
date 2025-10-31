import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";

function ConversationHistory({ conversation, onClear }) {
  if (!conversation || conversation.length === 0) {
    return null;
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography variant="h6">Conversation</Typography>
        <Button size="small" onClick={onClear}>
          Clear
        </Button>
      </Stack>
      <Divider sx={{ mb: 1 }} />
      <Stack spacing={1} maxHeight={240} overflow="auto">
        {conversation.map((msg, index) => (
          <Paper
            key={`${msg.role}-${index}`}
            variant="outlined"
            sx={{ p: 1.5, backgroundColor: msg.role === "assistant" ? "action.hover" : "inherit" }}
          >
            <Typography variant="caption" color="text.secondary">
              {msg.role === "assistant" ? "Assistant" : "User"}
            </Typography>
            <Typography component="p" sx={{ whiteSpace: "pre-wrap", mt: 0.5 }}>
              {msg.content}
            </Typography>
          </Paper>
        ))}
      </Stack>
    </Paper>
  );
}

export default ConversationHistory;
