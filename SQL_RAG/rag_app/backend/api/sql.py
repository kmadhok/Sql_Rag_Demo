"""
SQL execution endpoints for SQL RAG application
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)

# Create router without prefix (will be added in app.py)
router = APIRouter(tags=["sql"])

# Request/Response models
class ExecuteSQLRequest(BaseModel):
    sql: str
    dry_run: bool = False
    session_id: Optional[str] = None

class ExecuteSQLResponse(BaseModel):
    success: bool
    data: Optional[list] = None
    columns: Optional[list] = None
    row_count: Optional[int] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None
    timestamp: datetime

# Mock data for testing
MOCK_RESULTS = {
    "SELECT * FROM users LIMIT 5": {
        "data": [
            [1, "John Doe", "john@example.com", "2024-01-15"],
            [2, "Jane Smith", "jane@example.com", "2024-01-16"],
            [3, "Bob Johnson", "bob@example.com", "2024-01-17"],
            [4, "Alice Brown", "alice@example.com", "2024-01-18"],
            [5, "Charlie Wilson", "charlie@example.com", "2024-01-19"]
        ],
        "columns": ["id", "name", "email", "created_at"],
        "row_count": 5
    },
    "SELECT COUNT(*) as user_count FROM users": {
        "data": [[1000]],
        "columns": ["user_count"],
        "row_count": 1
    },
    "SELECT * FROM orders LIMIT 3": {
        "data": [
            [101, 1, "Laptop", 999.99, "2024-01-20"],
            [102, 2, "Mouse", 29.99, "2024-01-20"],
            [103, 1, "Keyboard", 79.99, "2024-01-21"]
        ],
        "columns": ["id", "user_id", "product_name", "amount", "order_date"],
        "row_count": 3
    }
}

def validate_sql_safety(sql: str) -> bool:
    """Basic SQL injection protection - only allow SELECT statements"""
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith('SELECT'):
        return False
    # Block dangerous keywords
    dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    return True

@router.post("/execute", response_model=ExecuteSQLResponse)
async def execute_sql(
    request: ExecuteSQLRequest,
    background_tasks: BackgroundTasks
):
    """Execute a SQL query"""
    try:
        # Validate SQL safety
        if not validate_sql_safety(request.sql):
            raise HTTPException(
                status_code=400, 
                detail="Only SELECT queries are allowed for security reasons"
            )
        
        # Log the query execution
        background_tasks.add_task(
            logger.info, 
            f"Executed SQL (dry_run={request.dry_run}): {request.sql}"
        )
        
        # For demo purposes, return mock results
        # In production, this would execute against your actual database
        if request.sql in MOCK_RESULTS:
            mock_result = MOCK_RESULTS[request.sql]
            return ExecuteSQLResponse(
                success=True,
                data=mock_result["data"],
                columns=mock_result["columns"],
                row_count=mock_result["row_count"],
                execution_time=0.05,  # Mock execution time
                timestamp=datetime.now()
            )
        else:
            # For unknown queries, return a generic result
            return ExecuteSQLResponse(
                success=True,
                data=[["Mock data for query"]],
                columns=["result"],
                row_count=1,
                execution_time=0.1,
                timestamp=datetime.now()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        return ExecuteSQLResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now()
        )

@router.get("/validate")
async def validate_query(sql: str):
    """Validate if a SQL query is safe to execute"""
    try:
        is_safe = validate_sql_safety(sql)
        return {
            "valid": is_safe,
            "message": "Query is safe to execute" if is_safe else "Query contains potentially dangerous operations"
        }
    except Exception as e:
        logger.error(f"Error validating SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_execution_history(limit: int = 50):
    """Get SQL execution history"""
    try:
        # Mock history data
        history = [
            {
                "id": "1",
                "sql": "SELECT * FROM users LIMIT 5",
                "execution_time": 0.05,
                "row_count": 5,
                "timestamp": "2024-01-20T10:30:00Z",
                "success": True
            },
            {
                "id": "2", 
                "sql": "SELECT COUNT(*) FROM users",
                "execution_time": 0.02,
                "row_count": 1,
                "timestamp": "2024-01-20T10:25:00Z",
                "success": True
            },
            {
                "id": "3",
                "sql": "SELECT * FROM orders WHERE user_id = 1",
                "execution_time": 0.08,
                "row_count": 3,
                "timestamp": "2024-01-20T10:20:00Z",
                "success": True
            }
        ]
        
        return {
            "history": history[:limit],
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error fetching SQL history: {e}")
        raise HTTPException(status_code=500, detail=str(e))