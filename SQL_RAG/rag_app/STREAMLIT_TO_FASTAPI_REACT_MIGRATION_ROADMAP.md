# Complete Streamlit to FastAPI + React Migration Roadmap 🐕

## 📋 Overview & Migration Strategy

This roadmap provides a comprehensive migration plan from Streamlit to a modern FastAPI + React architecture, preserving all functionality while improving scalability and user experience.

### 🎯 Migration Goals
- ✅ Preserve all 5 Streamlit pages with enhanced UX
- ✅ Maintain feature parity (agents, conversation, SQL execution, etc.)
- ✅ Add real-time streaming via WebSockets
- ✅ Implement responsive design for mobile/tablet
- ✅ Production-ready deployment setup

### 📁 Project Structure
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;
sql-rag-app/
├── backend/                    # FastAPI backend
│   ├── app.py                 # Main FastAPI app
│   ├── api/                   # API routers
│   │   ├── chat.py           # Chat endpoints
│   │   ├── data.py           # Data endpoints  
│   │   └── sql.py            # SQL endpoints
│   ├── models/               # Pydantic models
│   │   └── schemas.py        # Request/Response schemas
│   ├── services/             # Business logic
│   │   ├── rag_service.py    # RAG processing
│   │   ├── sql_service.py    # SQL execution
│   │   └── websocket_service.py # WebSocket handling
│   └── requirements.txt
├── frontend/                   # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   │   ├── common/       # Common UI components
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── chat/         # Chat-specific components
│   │   │   │   ├── ChatInterface.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── SQLHighlighter.tsx
│   │   │   │   └── AgentSelector.tsx
│   │   │   ├── data/         # Data display components
│   │   │   │   ├── SchemasTree.tsx
│   │   │   │   ├── QueryCatalog.tsx
│   │   │   │   ├── DataTable.tsx
│   │   │   │   └── AnalyticsCharts.tsx
│   │   │   └── search/       # Search components
│   │   │       ├── SearchBar.tsx
│   │   │       ├── FilterPanel.tsx
│   │   │       └── QueryCard.tsx
│   │   ├── pages/           # Page components
│   │   │   ├── IntroductionPage.tsx
│   │   │   ├── SearchPage.tsx
│   │   │   ├── DataPage.tsx
│   │   │   ├── AnalyticsPage.tsx
│   │   │   └── ChatPage.tsx
│   │   ├── hooks/           # Custom hooks
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useChat.ts
│   │   │   ├── useApi.ts
│   │   │   └── useLocalStorage.ts
│   │   ├── services/        # API services
│   │   │   ├── api.ts       # Base API client
│   │   │   ├── chatService.ts
│   │   │   ├── dataService.ts
│   │   │   └── websocketService.ts
│   │   ├── store/           # State management
│   │   │   ├── index.ts     # Store configuration
│   │   │   ├── chatSlice.ts
│   │   │   ├── dataSlice.ts
│   │   │   └── uiSlice.ts
│   │   ├── types/           # TypeScript types
│   │   │   ├── api.ts       # API types
│   │   │   ├── chat.ts      # Chat types
│   │   │   └── data.ts      # Data types
│   │   ├── utils/           # Utility functions
│   │   │   ├── constants.ts
│   │   │   ├── helpers.ts
│   │   │   └── formatters.ts
│   │   ├── styles/          # CSS/Styled-components
│   │   │   ├── globals.css
│   │   │   └── theme.ts
│   │   ├── App.tsx          # Main app component
│   │   └── index.tsx        # Entry point
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml         # Development setup
└── README.md
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;

## Backend API Endpoints

### Chat Endpoints (`/api/chat`):
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;python
# POST /api/chat/query
@app.post("/api/chat/query")
async def chat_query(request: ChatRequest):
    """Main chat endpoint with RAG + SQL extraction"""
    result = await rag_service.process_query(
        question=request.message,
        agent_type=request.agent_type,
        conversation_context=request.conversation_context
    )
    return result

# POST /api/chat/execute-sql  
@app.post("/api/chat/execute-sql")
async def execute_sql(request: SQLExecuteRequest):
    """Execute extracted SQL"""
    result = await sql_service.execute_query(
        sql=request.sql,
        dry_run=request.dry_run
    )
    return result

# GET /api/chat/history
@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history"""
    return await chat_service.get_history(session_id)

# WebSocket endpoint for streaming responses
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """Real-time chat streaming"""
    await websocket_service.handle_connection(websocket, session_id)
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;

### Data Endpoints (`/api/data`):
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;python
# GET /api/data/schema
@app.get("/api/data/schema")
async def get_schema():
    """Get database schema"""
    return await data_service.get_schema()

# GET /api/data/analytics
@app.get("/api/data/analytics")
async def get_analytics():
    """Get catalog analytics"""
    return await data_service.get_analytics()

# GET /api/data/queries
@app.get("/api/data/queries")
async def get_queries(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    filters: Optional[str] = None
):
    """Get query catalog with pagination and filtering"""
    return await data_service.get_queries(search, page, page_size, filters)
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;

### Enhanced Pydantic Models

```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;python
# models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime

class AgentType(str, Enum):
    CREATE = "create"
    EXPLAIN = "explain" 
    LONGANSWER = "longanswer"
    SCHEMA = "schema"
    NORMAL = "normal"

class FilterOptions(BaseModel):
    tables: Optional[List[str]] = None
    has_joins: Optional[bool] = None
    has_descriptions: Optional[bool] = None
    min_join_count: Optional[int] = None
    max_join_count: Optional[int] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    agent_type: Optional[AgentType] = None
    conversation_context: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    stream: bool = True

class ChatResponse(BaseModel):
    message: str
    sql_query: Optional[str] = None
    sql_executed: bool = False
    sql_result: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, Any]] = []
    token_usage: Dict[str, int] = {}
    context_utilization: Optional[float] = None
    agent_used: Optional[AgentType] = None
    session_id: str
    timestamp: datetime
    processing_time: Optional[float] = None

class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    dry_run: bool = False
    max_bytes_billed: int = 100000000
    session_id: Optional[str] = None

class SQLExecuteResponse(BaseModel):
    success: bool
    total_rows: int
    cost: float
    bytes_processed: int
    execution_time: float
    data: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    column_types: Optional[Dict[str, str]] = None

class QueryCatalogItem(BaseModel):
    id: int
    query: str
    description: Optional[str] = None
    tables: List[str]
    joins: List[Dict[str, Any]]
    tags: List[str] = []
    created_at: Optional[datetime] = None
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;

## 🎨 React Frontend Implementation

### TypeScript Interfaces

```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;typescript
// frontend/src/types/api.ts
export interface ChatRequest {
  message: string;
  agentType?: AgentType;
  conversationContext?: string;
  sessionId?: string;
  userId?: string;
  stream?: boolean;
}

export interface ChatResponse {
  message: string;
  sqlQuery?: string;
  sqlExecuted: boolean;
  sqlResult?: Record<string, any>;
  sources: Source[];
  tokenUsage: TokenUsage;
  contextUtilization?: number;
  agentUsed?: AgentType;
  sessionId: string;
  timestamp: string;
  processingTime?: number;
}

export interface Source {
  content: string;
  metadata: Record<string, any>;
  score: number;
}

export interface TokenUsage {
  prompt: number;
  completion: number;
  total: number;
}

export enum AgentType {
  CREATE = 'create',
  EXPLAIN = 'explain',
  LONGANSWER = 'longanswer', 
  SCHEMA = 'schema',
  NORMAL = 'normal'
}

// frontend/src/types/chat.ts
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sqlQuery?: string;
  sqlResult?: any;
  sources?: Source[];
  tokenUsage?: TokenUsage;
  contextUtilization?: number;
  agentUsed?: AgentType;
  isStreaming?: boolean;
}

export interface Conversation {
  sessionId: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

// frontend/src/types/data.ts
export interface TableSchema {
  name: string;
  columns: Column[];
  relationships: Relationship[];
}

export interface Column {
  name: string;
  type: string;
  nullable: boolean;
  description?: string;
}

export interface Relationship {
  type: 'one-to-one' | 'one-to-many' | 'many-to-many';
  sourceTable: string;
  sourceColumn: string;
  targetTable: string;
  targetColumn: string;
}

export interface QueryItem {
  id: number;
  query: string;
  description?: string;
  tables: string[];
  joins: JoinInfo[];
  tags: string[];
  createdAt?: string;
}

export interface JoinInfo {
  type: string;
  leftTable: string;
  leftColumn: string;
  rightTable: string;
  rightColumn: string;
  condition?: string;
}
```

### Redux Toolkit State Management

```typescript
// frontend/src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import chatSlice from './chatSlice';
import dataSlice from './dataSlice';
import uiSlice from './uiSlice';

export const store = configureStore({
  reducer: {
    chat: chatSlice,
    data: dataSlice,
    ui: uiSlice,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// frontend/src/store/chatSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Message, Conversation, ChatRequest } from '../types/chat';
import { chatService } from '../services/chatService';

interface ChatState {
  conversations: Record<string, Conversation>;
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  agentType: AgentType;
}

const initialState: ChatState = {
  conversations: {},
  currentSessionId: null,
  isLoading: false,
  error: null,
  agentType: AgentType.NORMAL,
};

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (request: ChatRequest) => {
    const response = await chatService.sendMessage(request);
    return response;
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setAgentType: (state, action: PayloadAction<AgentType>) => {
      state.agentType = action.payload;
    },
    setCurrentSession: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setAgentType, setCurrentSession } = chatSlice.actions;
export default chatSlice.reducer;