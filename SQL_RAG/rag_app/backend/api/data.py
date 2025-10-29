"""
Data API endpoints for SQL RAG application
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

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

# Create router without prefix (will be added in app.py)
router = APIRouter(tags=["data"])

# Mock data for testing
MOCK_DATABASE_SCHEMA = DatabaseSchema(
    tables=[
        TableSchema(
            name="users",
            columns=[
                ColumnSchema(name="id", type="INTEGER", nullable=False, description="User ID"),
                ColumnSchema(name="name", type="VARCHAR", nullable=False, description="User name"),
                ColumnSchema(name="email", type="VARCHAR", nullable=False, description="User email"),
                ColumnSchema(name="created_at", type="TIMESTAMP", nullable=False, description="Account creation date"),
            ],
            row_count=1000,
            description="User accounts table"
        ),
        TableSchema(
            name="orders",
            columns=[
                ColumnSchema(name="id", type="INTEGER", nullable=False, description="Order ID"),
                ColumnSchema(name="user_id", type="INTEGER", nullable=False, description="User ID reference"),
                ColumnSchema(name="product_name", type="VARCHAR", nullable=False, description="Product name"),
                ColumnSchema(name="amount", type="DECIMAL", nullable=False, description="Order amount"),
                ColumnSchema(name="order_date", type="TIMESTAMP", nullable=False, description="Order date"),
            ],
            row_count=5000,
            description="Customer orders table"
        ),
        TableSchema(
            name="products",
            columns=[
                ColumnSchema(name="id", type="INTEGER", nullable=False, description="Product ID"),
                ColumnSchema(name="name", type="VARCHAR", nullable=False, description="Product name"),
                ColumnSchema(name="category", type="VARCHAR", nullable=False, description="Product category"),
                ColumnSchema(name="price", type="DECIMAL", nullable=False, description="Product price"),
                ColumnSchema(name="in_stock", type="BOOLEAN", nullable=False, description="Stock availability"),
            ],
            row_count=200,
            description="Products catalog table"
        ),
    ],
    total_tables=3,
    database_name="demo_ecommerce"
)

@router.get("/schema", response_model=DatabaseSchema)
async def get_database_schema():
    """Get the database schema"""
    try:
        # For demo purposes, return mock data
        # In production, this would query BigQuery or your database
        return MOCK_DATABASE_SCHEMA
    except Exception as e:
        logger.error(f"Error fetching database schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tables/{table_name}", response_model=TableSchema)
async def get_table_schema(table_name: str):
    """Get schema for a specific table"""
    try:
        # Find table in mock data
        for table in MOCK_DATABASE_SCHEMA.tables:
            if table.name.lower() == table_name.lower():
                return table
        
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching table schema for {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tables")
async def get_table_names():
    """Get list of all table names"""
    try:
        table_names = [table.name for table in MOCK_DATABASE_SCHEMA.tables]
        return {"tables": table_names, "count": len(table_names)}
    except Exception as e:
        logger.error(f"Error fetching table names: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queries")
async def get_demo_queries(
    search: Optional[str] = Query(None, description="Search queries"),
    limit: int = Query(50, description="Maximum number of queries to return")
):
    """Get demo SQL queries"""
    try:
        # Mock query data
        demo_queries = [
            {
                "id": "1",
                "title": "Get all users",
                "description": "Retrieve all user records", 
                "sql": "SELECT * FROM users",
                "category": "Basic",
                "complexity": "Easy"
            },
            {
                "id": "2",
                "title": "Count users by date",
                "description": "Count users created per day",
                "sql": "SELECT DATE(created_at) as date, COUNT(*) as count FROM users GROUP BY DATE(created_at)",
                "category": "Analytics",
                "complexity": "Medium"
            },
            {
                "id": "3",
                "title": "Top selling products",
                "description": "Get top selling products by order count",
                "sql": "SELECT p.name, COUNT(o.id) as order_count FROM products p JOIN orders o WHERE p.name = o.product_name GROUP BY p.name ORDER BY order_count DESC LIMIT 10",
                "category": "Analytics",
                "complexity": "Hard"
            },
        ]
        
        # Filter by search term if provided
        if search:
            search_lower = search.lower()
            demo_queries = [
                q for q in demo_queries 
                if search_lower in q["title"].lower() or 
                   search_lower in q["description"].lower() or
                   search_lower in q["sql"].lower()
            ]
        
        # Limit results
        demo_queries = demo_queries[:limit]
        
        return {
            "queries": demo_queries,
            "count": len(demo_queries)
        }
    except Exception as e:
        logger.error(f"Error fetching demo queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))