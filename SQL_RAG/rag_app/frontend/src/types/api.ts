export enum AgentType {
  NORMAL = 'normal',
  CREATE = 'create',
  EXPLAIN = 'explain',
  SCHEMA = 'schema',
  LONGANSWER = 'longanswer'
}

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
  sessionId: string;
  timestamp: string | Date;
  agentUsed?: AgentType;
  sqlQuery?: string;
  sqlResult?: string | Record<string, any>;
  sources: Source[];
  tokenUsage: TokenUsage;
  contextUtilization?: number;
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

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date | string;
  sqlQuery?: string;
  sqlResult?: string | Record<string, any>;
  sources?: Source[];
  tokenUsage?: TokenUsage;
  contextUtilization?: number;
  agentUsed?: AgentType;
}

export interface Conversation {
  id: string;
  userId?: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, any>;
}

// Database and Query Catalog Types
export interface Column {
  name: string;
  type: string;
  nullable: boolean;
  description?: string;
}

export interface TableSchema {
  name: string;
  columns: Column[];
  row_count: number;
  description?: string;
}

export interface DatabaseSchema {
  tables: TableSchema[];
  total_tables: number;
  database_name: string;
}

export interface QueryItem {
  id: string;
  title: string;
  description: string;
  sql: string;
  category: string;
  complexity: 'Easy' | 'Medium' | 'Hard';
  tags?: string[];
  usage_count?: number;
  last_used?: string;
}

export interface ExecuteSQLRequest {
  sql: string;
  dryRun?: boolean;
  sessionId?: string;
}

export interface ExecuteSQLResponse {
  success: boolean;
  data?: any[];
  columns?: string[];
  rowCount?: number;
  executionTime?: number;
  error?: string;
  timestamp: string;
}

// Analytics Types
export interface AnalyticsData {
  queryStats: QueryStats;
  sessionStats: SessionStats;
  performanceMetrics: PerformanceMetrics;
}

export interface QueryStats {
  totalQueries: number;
  averageExecutionTime: number;
  successRate: number;
  popularQueries: QueryItem[];
}

export interface SessionStats {
  totalSessions: number;
  averageMessagesPerSession: number;
  sessionDuration: number;
  topUsers: any[];
}

export interface PerformanceMetrics {
  currentLoad: number;
  responseTime: number;
  errorRate: number;
  uptime: number;
}