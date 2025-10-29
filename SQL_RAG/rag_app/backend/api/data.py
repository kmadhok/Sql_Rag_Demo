"""
Data API endpoints for SQL RAG application
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])

# Response models
class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    description: Optional[str] = None

class TableSchema(BaseModel):
    name: str
    columns: List[ColumnSchema]
    row_count: int
    description: Optional[str] = None

class DatabaseSchema(BaseModel):
    tables: List[TableSchema]
    total_tables: int
    database_name: str

@router.get("/schema")
async def get_database_schema():
    """Get database schema information"""
    try:
        # Mock schema data
        mock_schema = DatabaseSchema(
            database_name="demo_database",
            total_tables=3,
            tables=[
                TableSchema(
                    name="users",
                    columns=[
                        ColumnSchema(name="id", type="INTEGER", nullable=False, description="User ID"),
                        ColumnSchema(name="name", type="VARCHAR", nullable=False, description="User name"),
                        ColumnSchema(name="email", type="VARCHAR", nullable=False, description="User email"),
                        ColumnSchema(name="created_at", type="TIMESTAMP", nullable=False, description="Account creation date")
                    ],
                    row_count=1000,
                    description="User accounts information"
                ),
                TableSchema(
                    name="orders",
                    columns=[
                        ColumnSchema(name="id", type="INTEGER", nullable=False, description="Order ID"),
                        ColumnSchema(name="user_id", type="INTEGER", nullable=False, description="User ID reference"),
                        ColumnSchema(name="product_name", type="VARCHAR", nullable=False, description="Product name"),
                        ColumnSchema(name="amount", type="DECIMAL", nullable=False, description="Order amount"),
                        ColumnSchema(name="order_date", type="TIMESTAMP", nullable=False, description="Order date")
                    ],
                    row_count=5000,
                    description="Customer orders"
                ),
                TableSchema(
                    name="products",
                    columns=[
                        ColumnSchema(name="id", type="INTEGER", nullable=False, description="Product ID"),
                        ColumnSchema(name="name", type="VARCHAR", nullable=False, description="Product name"),
                        ColumnSchema(name="category", type="VARCHAR", nullable=False, description="Product category"),
                        ColumnSchema(name="price", type="DECIMAL", nullable=False, description="Product price"),
                        ColumnSchema(name="in_stock", type="BOOLEAN", nullable=False, description="Stock availability")
                    ],
                    row_count=100,
                    description="Product catalog"
                )
            ]
        )
        return mock_schema
    except Exception as e:
        logger.error(f"Error fetching schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tables")
async def get_table_names():
    """Get list of table names"""
    try:
        table_names = ["users", "orders", "products"]
        return {"tables": table_names, "count": len(table_names)}
    except Exception as e:
        logger.error(f"Error fetching table names: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queries")
async def get_demo_queries(
    search: Optional[str] = Query(None, description="Search queries"),
    limit: int = Query(50, description="Maximum number of queries to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    min_joins: Optional[int] = Query(None, description="Minimum number of joins"),
    has_aggregation: Optional[bool] = Query(None, description="Has aggregation functions"),
    has_window_function: Optional[bool] = Query(None, description="Has window functions"),
    has_subquery: Optional[bool] = Query(None, description="Has subqueries")
):
    """Get demo SQL queries with advanced filtering"""
    try:
        # Enhanced demo query data based on original app
        demo_queries = [
            {
                "id": "1",
                "title": "Get all users",
                "description": "Retrieve all user records", 
                "sql": "SELECT * FROM users LIMIT 1000;",
                "category": "Basic",
                "complexity": "Easy",
                "tables": ["users"],
                "join_count": 0,
                "has_aggregation": False,
                "has_subquery": False,
                "has_window_function": False,
                "execution_time": 0.02,
                "difficulty_score": 1.2,
                "performance_rating": 9.5,
                "author": "System",
                "validated": True,
                "tags": ["basic", "select", "users"],
                "created_at": "2024-01-01T00:00:00Z",
                "usage_count": 45
            },
            {
                "id": "2",
                "title": "Count users by date",
                "description": "Count users created per day with growth analysis",
                "sql": "SELECT DATE(created_at) as signup_date, COUNT(*) as daily_users FROM users GROUP BY DATE(created_at) ORDER BY signup_date DESC;",
                "category": "Analytics",
                "complexity": "Medium",
                "tables": ["users"],
                "join_count": 0,
                "has_aggregation": True,
                "has_subquery": False,
                "has_window_function": False,
                "execution_time": 0.15,
                "difficulty_score": 4.5,
                "performance_rating": 7.8,
                "author": "System",
                "validated": True,
                "tags": ["analytics", "aggregation", "growth"],
                "created_at": "2024-01-02T00:00:00Z",
                "usage_count": 62
            },
            {
                "id": "3",
                "title": "Top selling products",
                "description": "Get top selling products by order count with revenue",
                "sql": "SELECT p.name, p.category, COUNT(o.id) as order_count, SUM(o.amount) as total_revenue FROM products p JOIN orders o ON p.name = o.product_name GROUP BY p.name, p.category ORDER BY total_revenue DESC LIMIT 10;",
                "category": "Revenue",
                "complexity": "Hard",
                "tables": ["products", "orders"],
                "join_count": 1,
                "has_aggregation": True,
                "has_subquery": False,
                "has_window_function": False,
                "execution_time": 0.45,
                "difficulty_score": 7.2,
                "performance_rating": 6.5,
                "author": "System",
                "validated": True,
                "tags": ["revenue", "joins", "analytics"],
                "created_at": "2024-01-03T00:00:00Z",
                "usage_count": 89
            },
            {
                "id": "4",
                "title": "Customer lifetime value",
                "description": "Calculate customer lifetime value with segmentation",
                "sql": "SELECT u.name, u.email, COUNT(o.id) as total_orders, SUM(o.amount) as total_spent, AVG(o.amount) as avg_order_value FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) >= 1 ORDER BY total_spent DESC;",
                "category": "Analytics",
                "complexity": "Hard",
                "tables": ["users", "orders"],
                "join_count": 1,
                "has_aggregation": True,
                "has_subquery": False,
                "has_window_function": False,
                "execution_time": 0.8,
                "difficulty_score": 7.8,
                "performance_rating": 6.2,
                "author": "System",
                "validated": True,
                "tags": ["clv", "analytics", "segmentation"],
                "created_at": "2024-01-04T00:00:00Z",
                "usage_count": 34
            },
            {
                "id": "5",
                "title": "Monthly revenue trends",
                "description": "Monthly revenue analysis with aggregations",
                "sql": "SELECT DATE_TRUNC('month', order_date) as month, SUM(amount) as monthly_revenue, COUNT(*) as order_count FROM orders WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) GROUP BY DATE_TRUNC('month', order_date) ORDER BY month DESC;",
                "category": "Revenue",
                "complexity": "Medium",
                "tables": ["orders"],
                "join_count": 0,
                "has_aggregation": True,
                "has_subquery": False,
                "has_window_function": False,
                "execution_time": 0.6,
                "difficulty_score": 6.5,
                "performance_rating": 7.0,
                "author": "System",
                "validated": True,
                "tags": ["revenue", "trends", "analytics"],
                "created_at": "2024-01-05T00:00:00Z",
                "usage_count": 56
            }
        ]
        
        # Apply filters
        filtered_queries = demo_queries.copy()
        
        # Search filter
        if search:
            search_lower = search.lower()
            filtered_queries = [
                q for q in filtered_queries 
                if any(search_lower in str(q.get(k, '')).lower() for k in ['title', 'description', 'sql', 'category', 'tags'])
            ]
        
        # Category filter
        if category:
            filtered_queries = [q for q in filtered_queries if q.get('category') == category]
        
        # Complexity filter
        if complexity:
            filtered_queries = [q for q in filtered_queries if q.get('complexity') == complexity]
        
        # Join count filter
        if min_joins is not None:
            filtered_queries = [q for q in filtered_queries if q.get('join_count', 0) >= min_joins]
        
        # Aggregation filter
        if has_aggregation is not None:
            filtered_queries = [q for q in filtered_queries if q.get('has_aggregation') == has_aggregation]
        
        # Window function filter
        if has_window_function is not None:
            filtered_queries = [q for q in filtered_queries if q.get('has_window_function') == has_window_function]
        
        # Subquery filter
        if has_subquery is not None:
            filtered_queries = [q for q in filtered_queries if q.get('has_subquery') == has_subquery]
        
        # Sort by usage_count (most used first) then by difficulty_score
        filtered_queries.sort(key=lambda x: (x.get('usage_count', 0), -x.get('difficulty_score', 0)), reverse=True)
        
        # Limit results
        limited_queries = filtered_queries[:limit]
        
        return {
            "queries": limited_queries,
            "count": len(limited_queries),
            "total_count": len(filtered_queries),
            "filters_applied": {
                "search": search,
                "category": category,
                "complexity": complexity,
                "min_joins": min_joins,
                "has_aggregation": has_aggregation,
                "has_window_function": has_window_function,
                "has_subquery": has_subquery
            }
        }
    except Exception as e:
        logger.error(f"Error fetching demo queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))