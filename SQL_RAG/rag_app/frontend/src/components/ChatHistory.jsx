import { useEffect, useRef } from "react";
import Stack from "@mui/material/Stack";
import Alert from "@mui/material/Alert";
import ChatMessage from "./ChatMessage.jsx";

function ChatHistory({ conversation, error, onExecute, onSave }) {
  const bottomRef = useRef(null);
  const previousLengthRef = useRef(conversation.length);

  useEffect(() => {
    const previousLength = previousLengthRef.current;
    if (conversation.length > previousLength) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    previousLengthRef.current = conversation.length;
  }, [conversation]);

  return (
    <Stack spacing={2} sx={{ flexGrow: 1, overflowY: "auto", pb: 2 }}>
      {conversation.length === 0 && !error && (
        <Alert severity="info">
          Ask a question to start the conversation. Follow-up questions will
          automatically include previous context.
        </Alert>
      )}
      {conversation.map((message) => (
        <ChatMessage
          key={message.id}
          message={message}
          onExecute={onExecute}
          onSave={onSave}
        />
      ))}
      {error && <Alert severity="error">{error}</Alert>}
      <div ref={bottomRef} />
    </Stack>
  );
}

export default ChatHistory;
