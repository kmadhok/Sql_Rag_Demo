import { useEffect, useRef } from "react";
import Stack from "@mui/material/Stack";
import Alert from "@mui/material/Alert";
import ChatMessage from "./ChatMessage.jsx";

function ChatHistory({ conversation, error, onExecute, onSave }) {
  const bottomRef = useRef(null);
  const previousLengthRef = useRef(conversation.length);
  const containerRef = useRef(null);

  useEffect(() => {
    const previousLength = previousLengthRef.current;
    const hasNewMessage = conversation.length > previousLength;

    if (hasNewMessage && containerRef.current && bottomRef.current) {
      // Only scroll if user is already near bottom (within 100px)
      const container = containerRef.current;
      const isNearBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight < 100;

      // Or if the last message is from assistant (new response)
      const lastMessage = conversation[conversation.length - 1];
      const isAssistantMessage = lastMessage?.role === 'assistant';

      if (isNearBottom || isAssistantMessage) {
        bottomRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }
    previousLengthRef.current = conversation.length;
  }, [conversation]);

  return (
    <div style={{ maxWidth: '56rem', margin: '0 auto', padding: '0 2rem', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Stack spacing={2} ref={containerRef} sx={{ flexGrow: 1, overflowY: "auto", pb: 2 }}>
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
    </div>
  );
}

export default ChatHistory;
