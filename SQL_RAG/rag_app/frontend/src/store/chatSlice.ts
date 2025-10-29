import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest, ChatResponse, ExecuteSQLResponse } from '../types/api';
import { chatService } from '../services/chatService';
import { dataService } from '../services/dataService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: string;
  messages: Message[];
  sqlResults: ExecuteSQLResponse | null;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: 'normal',
  messages: [],
  sqlResults: null,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

export const executeSQL = createAsyncThunk(
  'chat/executeSQL',
  async (request: { sql: string; dryRun?: boolean }) => {
    const response = await dataService.executeQuery({
      sql: request.sql,
      dryRun: request.dryRun
    });
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<string>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
    addMessage: (state, action: PayloadAction<Message>) => {
      state.messages.push(action.payload);
    },
    clearMessages: (state) => {
      state.messages = [];
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isLoading = false;
        // Convert ChatResponse to Message
        const timestampStr = typeof action.payload.timestamp === 'string' 
          ? action.payload.timestamp 
          : new Date(action.payload.timestamp).toISOString();
          
        const message: Message = {
          id: timestampStr || Date.now().toString(),
          content: action.payload.message,
          role: 'assistant',
          timestamp: action.payload.timestamp,
          sqlQuery: action.payload.sqlQuery,
          sqlResult: action.payload.sqlResult,
          sources: action.payload.sources,
          tokenUsage: action.payload.tokenUsage,
          contextUtilization: action.payload.contextUtilization,
          agentUsed: action.payload.agentUsed,
        };
        state.messages.push(message);
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to send message';
      })
      .addCase(executeSQL.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(executeSQL.fulfilled, (state, action) => {
        state.isLoading = false;
        state.sqlResults = action.payload;
      })
      .addCase(executeSQL.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to execute SQL';
      });
  },
});

export const { setAgentType, setCurrentSession, addMessage, clearMessages, clearError } = chatSlice.actions;
export default chatSlice.reducer;