// TypeScript interfaces for API communication

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

export interface SQLExecuteRequest {
  sql: string;
  dryRun?: boolean;
  maxBytesBilled?: number;
  sessionId?: string;
}

export interface SQLExecuteResponse {
  success: boolean;
  totalRows: number;
  cost: number;
  bytesProcessed: number;
  executionTime: number;
  data?: any[];
  errorMessage?: string;
  columnTypes?: Record<string, string>;
}