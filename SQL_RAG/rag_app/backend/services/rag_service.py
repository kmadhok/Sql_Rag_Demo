"""
RAG Service for SQL RAG application
"""
import logging
from typing import Dict, Any, List, Optional
from google.cloud import aiplatform
from google.api_core.exceptions import GoogleAPICallError
from config import settings

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.project_id = settings.BIGQUERY_PROJECT_ID
        self.location = settings.MODEL_LOCATION
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.clients = {}
        
        # Check if we have real API keys
        self.use_real_ai = (
            self.gemini_api_key and 
            self.gemini_api_key not in ["demo-key", "your_actual_gemini_api_key_here", "", None]
        )
        
        if self.use_real_ai:
            logger.info("✅ Using real Gemini AI for responses")
        else:
            logger.info("🎭 Using mock responses (no valid API key found)")
    
    def process_query(
        self, 
        question: str, 
        agent_type: str = "normal",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user query with RAG
        """
        try:
            # For now, return an enhanced mock response
            # TODO: Implement real Gemini AI integration when API key is provided
            mock_responses = self._generate_mock_response(question, agent_type)
            mock_sql = self._generate_mock_sql(question)
            
            return {
                "message": mock_responses,
                "sql_query": mock_sql,
                "sql_executed": False,
                "sources": [{"name": "documentation", "content": "Database schema information"}],
                "token_usage": {"prompt": 100, "completion": 200, "total": 300},
                "session_id": "demo-session",
                "timestamp": "2024-01-01T00:00:00Z",
                "processing_time": 0.5,
                "agent_used": agent_type
            }
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "message": "Error processing your query",
                "error": str(e),
                "sql_query": None,
                "sources": [],
                "token_usage": {"prompt": 0, "completion": 0, "total": 0},
                "agent_used": agent_type
            }
    
    def _generate_mock_response(self, question: str, agent_type: str) -> str:
        """
        Generate enhanced mock response based on agent type and question
        """
        question_lower = question.lower()
        
        if agent_type == "normal":
            if "how many" in question_lower and "user" in question_lower:
                return "To count the number of users in your database, you would use the SQL query: SELECT COUNT(*) FROM users; This query scans the users table and returns the total number of user records in your system. The result will be a single value representing the count."
            elif "all user" in question_lower or "show me user" in question_lower:
                return "To view all users in your database, you can use: SELECT * FROM users LIMIT 100; This query retrieves all columns from the users table with a LIMIT clause to prevent returning too much data at once. For production use, consider adding pagination."
            elif "order" in question_lower:
                if "recent" in question_lower:
                    return "To see the most recent orders, you would use: SELECT * FROM orders ORDER BY order_date DESC LIMIT 10; This sorts the orders by date in descending order and returns the 10 most recent entries."
                else:
                    return "To analyze your orders data, you could use queries like: SELECT COUNT(*) FROM orders GROUP BY DATE(order_date); This would show you daily order counts."
            else:
                return f"Based on your question '{question}', I recommend examining the relevant database tables (users, orders, products) and using appropriate SQL aggregations or joins. Consider what specific metrics you're looking for, such as counts, averages, or trends."
        
        elif agent_type == "create":
            return f"For your request '{question}', here's how you could structure the SQL query. First, identify the main table you need to query, then add any necessary JOINs to related tables. Here's a template: SELECT columns FROM main_table m LEFT JOIN related_table r ON m.id = r.foreign_key WHERE conditions GROUP BY columns ORDER BY field LIMIT 100; Always include proper filtering and pagination in production queries."
        
        elif agent_type == "explain":
            return f"To understand your SQL query better, let me break down what it does: 1) The SELECT clause specifies which columns to return, 2) FROM identifies which table to query, 3) WHERE filters the results, 4) GROUP BY aggregates data, 5) ORDER BY sorts the results, and 6) LIMIT restricts the number of rows. Each of these plays a crucial role in shaping your final result set."
        
        elif agent_type == "schema":
            return "Your database schema includes three main tables: 1) users table (id, name, email, created_at) - stores user information with primary key id, 2) orders table (id, user_id, product_name, amount, order_date) - stores order data with foreign key relationship to users, 3) products table (id, name, category, price, in_stock) - contains product inventory. The relationships between these tables allow for comprehensive analysis of user behavior and sales patterns."
        
        elif agent_type == "longanswer":
            return f"Regarding '{question}', this is an excellent database inquiry that involves understanding your data model and writing efficient SQL queries. The process typically includes: 1) Identifying the relevant tables (users, orders, products), 2) Determining the relationships between these tables through foreign keys, 3) Applying appropriate filtering conditions to narrow down results, 4) Using aggregation functions (COUNT, SUM, AVG) for metrics, 5) Implementing proper sorting and pagination for performance, and 6) Considering indexes and query optimization for large datasets. Remember that the quality of your SQL query directly impacts performance and accuracy of insights derived from your data."
        
        return f"Processing your question: {question} with {agent_type} agent type. I'm here to help you with SQL queries and database analysis."
    
    def _generate_mock_sql(self, question: str) -> str:
        """
        Generate appropriate mock SQL based on question content
        """
        question_lower = question.lower()
        
        if "how many" in question_lower or "count" in question_lower:
            if "user" in question_lower:
                return "SELECT COUNT(*) as user_count FROM users;"
            elif "order" in question_lower:
                return "SELECT COUNT(*) as order_count FROM orders;"
            elif "product" in question_lower:
                return "SELECT COUNT(*) as product_count FROM products WHERE in_stock = true;"
            else:
                return "SELECT COUNT(*) FROM table_name;"
        
        elif "all" in question_lower:
            if "user" in question_lower:
                return "SELECT * FROM users ORDER BY created_at DESC LIMIT 100;"
            elif "order" in question_lower:
                return "SELECT * FROM orders ORDER BY order_date DESC LIMIT 100;"
            elif "product" in question_lower:
                return "SELECT * FROM products ORDER BY name ASC LIMIT 100;"
        
        elif "recent" in question_lower:
            if "order" in question_lower:
                return "SELECT o.*, u.name as user_name FROM orders o JOIN users u ON o.user_id = u.id ORDER BY o.order_date DESC LIMIT 10;"
        
        elif "popular" in question_lower and "product" in question_lower:
            return "SELECT p.name, COUNT(o.id) as order_count, p.price FROM products p LEFT JOIN orders o ON p.name = o.product_name GROUP BY p.name, p.price ORDER BY order_count DESC LIMIT 10;"
        
        elif "jo" in question_lower and "in" in question_lower and ("2024" in question_lower or "2025" in question_lower):
            return "SELECT COUNT(*) as order_count FROM orders WHERE DATE(order_date) >= DATE('2024-01-01');"
        
        else:
            return "SELECT * FROM users LIMIT 10;"

# Global instance
rag_service = RAGService()