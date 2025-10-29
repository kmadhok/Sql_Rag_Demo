# Backend Services and API Endpoints

## Core Services

### 1. Backend Services Located in `/backend/services/`
- **ConversationService** (`conversation_service.py`): Manages chat sessions and message history
- **RAGService** (`rag_service.py`): Processes queries using LLM (Gemini) with fallback to mock responses
- **WebSocketManager** (`websocket_service.py`): WebSocket infrastructure (service class available but no endpoints implemented)
- **SQLService** (`sql_service.py`): Handles SQL execution and validation with real BigQuery integration

### 2. API Router Services Located in `/backend/api/`

#### Chat Service (`/api/chat`)
**POST** `/sessions` - Create a new chat session
- Request: `CreateSessionRequest` (user_id: str, title: Optional[str] = None)
- Response: `CreateSessionResponse` (session_id: str, user_id: str, created_at: datetime, title: str)

**GET** `/sessions/{user_id}` - Get all chat sessions for a user
- Response: List of session objects with metadata and message counts

**GET** `/sessions/{session_id}/messages` - Get all messages in a chat session
- Response: List of message objects with content, metadata, and timestamps

**POST** `/` - Send a message to the chat assistant
- Request: `ChatRequest` (session_id: str, message: str, context: Optional[str] = None)
- Response: `ChatResponse` (answer: str, sql_query: Optional[str], sources: List[Dict], token_usage: Dict, agent_used: str)

**DELETE** `/sessions/{session_id}` - Delete a chat session
- Response: Success/failure status

#### Query Search Service (`/api/query-search`)
**POST** `/search` - Execute vector-based query search pipeline
- Request: `QuerySearchRequest`:
  ```json
  {
    "question": "Your question here",
    "k": 5,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }
  ```
- Response: `QuerySearchResponse`:
  ```json
  {
    "question": "User question",
    "answer": "Generated response",
    "sql_query": "Generated SQL",
    "retrieved_documents": [...],
    "schema_injected": "Schema context",
    "validation_passed": true,
    "validation_errors": [],
    "execution_available": true,
    "usage_stats": {
      "retrieval_time": 0.123,
      "generation_time": 2.456,
      "documents_retrieved": 5,
      "tables_retrieved": 3,
      "token_usage": {"prompt": 330, "completion": 1006, "total": 1336}
    },
    "timestamp": "2025-01-01T12:00:00Z",
    "session_id": "query_search_123456",
    "processing_time": 2.579
  }
  ```

**POST** `/execute` - Execute SQL query using real BigQuery integration
- Request: `ExecuteQueryRequest`:
  ```json
  {
    "sql": "SELECT * FROM products LIMIT 10",
    "dry_run": false
  }
  ```
- Response: `ExecuteQueryResponse`:
  ```json
  {
    "success": true,
    "data": [...],
    "columns": [...],
    "row_count": 10,
    "execution_time": 0.156,
    "bytes_processed": 1048576,
    "bytes_billed": 0,
    "job_id": "bigquery_job_123",
    "cache_hit": false,
    "dry_run": false,
    "error_message": null,
    "sql": "Original SQL query",
    "timestamp": "2025-01-01T12:00:00Z"
  }
  ```

#### SQL Service (`/api/sql`)
**POST** `/execute` - Execute a SQL query with validation
- Request: `ExecuteSQLRequest` (sql: str, parameters: Optional[Dict] = None)
- Response: `ExecuteSQLResponse` (success: bool, data: Optional[List], error: Optional[str], execution_time: float)
- Validates SQL safety (SELECT statements only)
- Executes against BigQuery when configured

**GET** `/validate` - Validate if a SQL query is safe to execute
- Query Parameters: sql (string)
- Response: `ValidationResponse` (is_valid: bool, errors: List[str], warnings: List[str])
- Checks for dangerous SQL operations (DROP, DELETE, etc.)

**GET** `/history` - Get SQL execution history
- Query Parameters: limit (int, default=10), user_id (optional)
- Response: List of execution records
- Supports pagination and user filtering

#### Data Service (`/api/`) ⚠️ **PREFIX CORRECTION**
**GET** `/schema` - Get database schema information
- Response: `DatabaseSchemaResponse`:
  ```json
  {
    "tables": [
      {
        "name": "products",
        "columns": [
          {"name": "id", "type": "INT64", "nullable": false},
          {"name": "name", "type": "STRING", "nullable": true}
        ],
        "row_count": 1000
      }
    ],
    "total_tables": 7,
    "database_name": "thelook_ecommerce"
  }
  ```

**GET** `/tables` - Get list of table names
- Response: `TablesResponse` (tables: List[str], total_tables: int, database_name: str)

**GET** `/queries` - Get demo SQL queries with advanced filtering
- Query Parameters:
  - search (string): Filter by search text
  - category (string): Filter by category
  - complexity (string): Filter by complexity level
  - min_joins (int): Minimum number of joins required
  - has_aggregation (bool): Filter for aggregation queries
  - has_window_function (bool): Filter for window functions
  - has_subquery (bool): Filter for subqueries
- Response: `QueriesResponse` (queries: List[QueryMetadata], total_count: int, filtered_count: int)

#### Root Endpoints
**GET** `/` - Root endpoint with HTML welcome page
- Returns HTML page with links to API documentation and health check
- Provides basic service information

**GET** `/health` - Health check endpoint
- Response:
  ```json
  {
    "status": "healthy",
    "service": "RAG SQL Service",
    "version": "1.0.0"
  }
  ```

### 3. CORS Configuration
**Allowed Origins:**
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://frontend:3000`
- `http://localhost:80` (Nginx proxy)
- `http://127.0.0.1:80`
- `http://0.0.0.0:80`
- `FRONTEND_URL` environment variable

**Allowed Methods:** All HTTP methods (`["*"]`)
**Allowed Headers:** All headers (`["*"]`)
**Credentials:** Enabled

### 4. Error Handling
All endpoints return consistent error responses with detailed error information:

**Standard Error Response:**
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-01-01T12:00:00Z",
  "path": "/api/endpoint"
}
```

**Common Error Codes:**
- `VALIDATION_ERROR`: Request validation failed
- `SQL_VALIDATION_ERROR`: SQL query validation failed
- `VECTOR_SEARCH_ERROR`: FAISS vector search failed
- `BIGQUERY_ERROR`: BigQuery execution error
- `LLM_ERROR`: LLM processing error

### 5. Data Models
Complete Pydantic models are defined in `/backend/models/schemas.py`:

**Key Request Models:**
- `QuerySearchRequest`: Vector search request parameters
- `ExecuteQueryRequest`: SQL execution request
- `ChatRequest`: Chat message request
- `CreateSessionRequest`: Session creation request

**Key Response Models:**
- `QuerySearchResponse`: Vector search response with full pipeline results
- `ExecuteQueryResponse`: SQL execution results
- `ChatResponse`: Chat assistant response
- `DatabaseSchemaResponse`: Database schema information

### 6. Environment Configuration
**Required Environment Variables:**
- `GEMINI_API_KEY`: Google Gemini API key for LLM processing
- `BIGQUERY_PROJECT_ID`: Google Cloud project ID for BigQuery
- `MODEL_LOCATION`: BigQuery dataset location (default: us-central1)
- `EMBEDDINGS_PROVIDER`: Embedding provider ("openai" or "ollama")
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI embeddings)

**Optional Environment Variables:**
- `DEBUG`: Enable debug logging ("true"/"false")
- `LOG_LEVEL`: Logging level ("INFO", "DEBUG", "ERROR")
- `FRONTEND_URL`: Frontend URL for CORS

### 7. Authentication
Currently, the API does not implement authentication. All endpoints are publicly accessible. JWT token infrastructure exists in the API client but is not enforced on the server.

### 8. Infrastructure Limitations

#### WebSocket Support 
⚠️ **NOT IMPLEMENTED**: While a `WebSocketManager` service class exists, no actual WebSocket endpoints (`@router.websocket()`) are currently defined in the FastAPI application.

## Key Features
1. **Vector Search**: Uses FAISS for similarity search in `/api/query-search/search`
2. **LLM Integration**: RAG service processes queries with Gemini API fallback
3. **SQL Validation**: Built-in SQL safety checks and schema validation
4. **Real BigQuery Integration**: Direct query execution against Google BigQuery
5. **Conversation Management**: Persistent chat sessions with full history
6. **Comprehensive Error Handling**: Detailed error responses with proper HTTP status codes
7. **Pydantic Validation**: Strong request/response validation and serialization
8. **CORS Support**: Configured for frontend integration

## Usage Examples

### Query Search Example
```bash
curl -X POST http://localhost:8001/api/query-search/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me the most expensive products",
    "k": 5,
    "use_gemini": true,
    "schema_injection": true,
    "sql_validation": true
  }'
```

### SQL Execution Example
```bash
curl -X POST http://localhost:8001/api/query-search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT name, retail_price FROM products ORDER BY retail_price DESC LIMIT 3",
    "dry_run": false
  }'
```

### Chat Example
```bash
curl -X POST http://localhost:8001/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_123",
    "message": "What are the top 10 products by sales?"
  }'
```

The backend provides a comprehensive, production-ready API for the React frontend to interact with all RAG functionality, from vector search to real-time SQL execution against BigQuery.