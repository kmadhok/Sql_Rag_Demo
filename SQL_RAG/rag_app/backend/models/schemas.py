# Pydantic models for SQL RAG application

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union, Literal
from enum import Enum
from datetime import datetime
import json

# Agent types for specialized processing
class AgentType(str, Enum):
    CREATE = "create"
    EXPLAIN = "explain"
    LONGANSWER = "longanswer"
    SCHEMA = "schema"
    NORMAL = "normal"

# Search and filtering options
class FilterOptions(BaseModel):
    tables: Optional[List[str]] = None
    has_joins: Optional[bool] = None
    has_descriptions: Optional[bool] = None
    min_join_count: Optional[int] = Field(None, ge=0)
    max_join_count: Optional[int] = Field(None, ge=0)
    
class SortOptions(BaseModel):
    field: Literal["created_at", "relevance", "complexity"] = "created_at"
    direction: Literal["asc", "desc"] = "desc"

# Core chat request/response models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's question or request")
    agent_type: Optional[AgentType] = None
    conversation_context: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    stream: bool = True
    max_results: int = Field(10, ge=1, le=50)
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

class ChatResponse(BaseModel):
    message: str
    sql_query: Optional[str] = None
    sql_executed: bool = False
    sql_result: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, Any]] = []
    token_usage: Optional[Dict[str, int]] = None
    context_utilization: Optional[float] = Field(None, ge=0.0, le=1.0)
    agent_used: Optional[AgentType] = None
    session_id: str
    timestamp: datetime
    processing_time: Optional[float] = Field(None, ge=0.0)
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# SQL execution models
class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="SQL query to execute")
    dry_run: bool = False
    max_bytes_billed: int = Field(100000000, ge=0, description="Maximum bytes to bill")
    session_id: Optional[str] = None
    
    @validator('sql')
    def validate_sql(cls, v):
        basic_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        if not any(keyword in v.upper() for keyword in basic_keywords):
            raise ValueError('Invalid SQL query - no recognized SQL keywords found')
        return v.strip()

class SQLExecuteResponse(BaseModel):
    success: bool
    total_rows: int = Field(0, ge=0)
    cost: float = Field(0.0, ge=0.0)
    bytes_processed: int = Field(0, ge=0)
    execution_time: float = Field(0.0, ge=0.0)
    data: Optional[List[Dict[str, Any]]] = None
    column_types: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    query_id: Optional[str] = None
    warnings: List[str] = []

# Database schema models
class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    description: Optional[str] = None
    mode: str = "nullable"

class TableInfo(BaseModel):
    name: str
    description: Optional[str] = None
    columns: List[ColumnInfo]
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None

class DatabaseSchema(BaseModel):
    project_id: str
    dataset_id: str
    tables: List[TableInfo]
    relationships: List[Dict[str, Any]] = []
    last_updated: datetime = Field(default_factory=datetime.now)

# Query catalog models
class JoinInfo(BaseModel):
    type: str
    left_table: str
    left_column: str
    right_table: str
    right_column: str
    condition: Optional[str] = None
    cardinality: Optional[str] = None

class QueryItem(BaseModel):
    id: int
    query: str
    description: Optional[str] = None
    tables: List[str]
    joins: List[JoinInfo] = []
    tags: List[str] = []
    complexity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None
    token_count: Optional[int] = Field(None, ge=0)
    
class QueryCatalogResponse(BaseModel):
    queries: List[QueryItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    filters: Optional[FilterOptions] = None
    sort: Optional[SortOptions] = None

# Conversation management models
class ConversationMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    sql_query: Optional[str] = None
    sql_result: Optional[Dict[str, Any]] = None
    sources: List[Dict[str, Any]] = []
    agent_used: Optional[AgentType] = None
    token_usage: Optional[Dict[str, int]] = None
    context_utilization: Optional[float] = None
    processing_time: Optional[float] = None

class Conversation(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    messages: List[ConversationMessage] = []
    created_at: datetime
    updated_at: datetime
    total_messages: int = 0
    total_tokens: int = 0

# Analytics and metrics models
class AnalyticsSummary(BaseModel):
    total_queries: int
    queries_with_descriptions: int
    queries_with_sql_execution: int
    total_conversations: int
    active_users_24h: int
    total_sql_executions: int
    total_bytes_processed: int
    total_cost: float = 0.0
    average_response_time: float = 0.0
    top_tables: List[Dict[str, Any]] = []
    agent_usage: Dict[AgentType, int] = {}

# API response wrappers
class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class PaginatedResponse(BaseModel):
    items: List[Any]
    pagination: Dict[str, Any]
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.now)

# WebSocket message models
class WebSocketMessage(BaseModel):
    type: Literal["query", "response", "error", "status"]
    data: Union[ChatRequest, ChatResponse, Dict[str, Any]]
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

# Health check models
class HealthStatus(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    services: Dict[str, bool] = {}
    uptime_seconds: float = 0.0
    error_count: int = 0