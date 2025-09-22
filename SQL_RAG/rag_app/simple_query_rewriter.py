#!/usr/bin/env python3
"""
Simple Query Rewriter for SQL RAG System

A lightweight query enhancement system that uses Gemini 2.5 Flash Lite and 
actual database schema to improve search queries for better document retrieval.

Features:
- Schema-aware query enhancement using actual database structure
- Simple Gemini 2.5 Flash Lite integration
- No caching, confidence scoring, or complex fallbacks
- Direct CSV schema parsing for table/column validation
"""

import logging
import csv
import io
from typing import Dict, List, Optional, Set
from pathlib import Path

# Gemini imports
try:
    from gemini_client import GeminiClient
except ImportError:
    GeminiClient = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GEMINI_MODEL = "gemini-2.5-flash-lite"
SCHEMA_CSV_PATH = Path(__file__).parent / "sample_queries_metadata_schema.csv"


class SimpleQueryRewriter:
    """Simplified query rewriter using schema-aware Gemini enhancement"""
    
    def __init__(self, schema_csv_path: Optional[Path] = None):
        """
        Initialize the simple query rewriter
        
        Args:
            schema_csv_path: Path to the schema CSV file
        """
        self.schema_csv_path = schema_csv_path or SCHEMA_CSV_PATH
        self.tables_columns = self._load_schema()
        self.gemini_client = None
        
        # Initialize GeminiClient - let it handle all validation and error handling
        if GeminiClient is not None:
            try:
                self.gemini_client = GeminiClient(model=GEMINI_MODEL)
                logger.info(f"✅ Initialized Gemini client with model: {GEMINI_MODEL}")
            except Exception as e:
                logger.warning(f"Gemini client initialization failed: {e}")
                self.gemini_client = None
        else:
            logger.warning("GeminiClient not available - query rewriting disabled")
    
    def _load_schema(self) -> Dict[str, List[str]]:
        """
        Load database schema from CSV file
        
        Returns:
            Dictionary mapping table names to lists of column names
        """
        tables_columns = {}
        
        if not self.schema_csv_path.exists():
            logger.warning(f"Schema CSV not found: {self.schema_csv_path}")
            return tables_columns
        
        try:
            with open(self.schema_csv_path, 'r', encoding='utf-8') as f:
                # Skip empty lines at the beginning
                lines = f.readlines()
                non_empty_lines = [line for line in lines if line.strip()]
                
                if not non_empty_lines:
                    logger.warning("Schema CSV is empty")
                    return tables_columns
                
                # Parse CSV from non-empty lines
                csv_content = ''.join(non_empty_lines)
                reader = csv.DictReader(io.StringIO(csv_content))
                
                for row in reader:
                    table_id = row.get('tableid', '').strip()
                    column_name = row.get('columnnames', '').strip()
                    
                    if not table_id or not column_name:
                        continue
                    
                    # Extract table name from project.dataset.table_name format
                    if '.' in table_id:
                        table_name = table_id.split('.')[-1]
                    else:
                        table_name = table_id
                    
                    if table_name not in tables_columns:
                        tables_columns[table_name] = []
                    
                    if column_name not in tables_columns[table_name]:
                        tables_columns[table_name].append(column_name)
            
            logger.info(f"✅ Loaded schema: {len(tables_columns)} tables, {sum(len(cols) for cols in tables_columns.values())} columns")
            
        except Exception as e:
            logger.error(f"Failed to load schema CSV: {e}")
        
        return tables_columns
    
    def _build_schema_context(self) -> str:
        """Build schema context string for the LLM prompt"""
        if not self.tables_columns:
            return "No database schema available."
        
        schema_lines = ["Available database tables and columns:"]
        
        for table_name, columns in sorted(self.tables_columns.items()):
            schema_lines.append(f"  {table_name}: {', '.join(sorted(columns))}")
        
        return "\n".join(schema_lines)
    
    def _build_enhancement_prompt(self, user_query: str, schema_context: str) -> str:
        """Build the prompt for query enhancement"""
        
#         prompt = f"""You are helping improve a search query for finding relevant SQL examples in a database documentation system.

# User's original query: "{user_query}"

# {schema_context}

# Your task: Enhance the user's query to better match SQL examples that would be relevant to their question. Consider:

# 1. Add specific table names and column names from the schema when relevant
# 2. Include SQL terminology that would appear in relevant code examples  
# 3. Add synonyms and related concepts that developers might use
# 4. Keep the original intent but make it more specific to the database structure
# 5. Focus on what SQL patterns, joins, or operations they might be looking for

# Return only the enhanced search query, this should be natural text and not a SQL query, no explanations or formatting:"""

        prompt = f"""
        You rewrite user search queries so they better match relevant SQL examples in our docs.

        User query: "{user_query}"

        Schema snapshot (tables, columns, types):
        {schema_context}

        Rewrite goals (in priority order):
        1) Ground to this schema: only mention table/column names that appear in the schema snapshot. Do not invent names.
        2) Add retrieval-friendly detail: include exact table/column strings and precise SQL concepts likely present in examples
        (e.g., JOIN, GROUP BY, WINDOW, CTE, WHERE, aggregation).
        3) Expand business terms to canonical metric/column names when clear (e.g., revenue→sales_amount; customer→customers.customer_id).
        4) Clarify relationships and filters in words (e.g., "join orders to order_items on order_id"; "filter on order_date last 30 days").
        5) Include 2–4 concise synonyms or developer phrasings that might appear in code/comments.
        6) Exclude noisy targets if obvious (e.g., “exclude test/staging/sample tables”).

        Constraints:
        - Natural language only (no SQL).
        - 40–60 words, single line.
        - If no strong schema matches, keep generic and avoid fabricated names.

        Return ONLY the enhanced search query.
        """

        return prompt
    
    def rewrite_query(self, query: str) -> Dict[str, any]:
        """
        Rewrite query for improved SQL document retrieval
        
        Args:
            query: Original user query
            
        Returns:
            Dictionary containing rewrite results
        """
        if not query or not query.strip():
            return {
                'original_query': query,
                'rewritten_query': query,
                'query_changed': False,
                'method': 'empty_query',
                'error': None
            }
        
        # If GeminiClient is not available, return original query
        if not self.gemini_client:
            return {
                'original_query': query,
                'rewritten_query': query,
                'query_changed': False,
                'method': 'gemini_unavailable',
                'error': 'GeminiClient not available or failed to initialize'
            }
        
        try:
            # Build schema context
            schema_context = self._build_schema_context()
            
            # Build enhancement prompt
            prompt = self._build_enhancement_prompt(query, schema_context)
            
            # Get enhanced query from Gemini
            enhanced_query = self.gemini_client.invoke(prompt)
            
            if not enhanced_query or not enhanced_query.strip():
                return {
                    'original_query': query,
                    'rewritten_query': query,
                    'query_changed': False,
                    'method': 'empty_response',
                    'error': 'Empty response from Gemini'
                }
            
            enhanced_query = enhanced_query.strip()
            query_changed = enhanced_query.lower() != query.lower()
            
            return {
                'original_query': query,
                'rewritten_query': enhanced_query,
                'query_changed': query_changed,
                'method': 'gemini_enhanced',
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return {
                'original_query': query,
                'rewritten_query': query,
                'query_changed': False,
                'method': 'error_fallback',
                'error': str(e)
            }
    
    def get_schema_info(self) -> Dict[str, any]:
        """Get information about the loaded schema"""
        return {
            'schema_loaded': bool(self.tables_columns),
            'table_count': len(self.tables_columns),
            'total_columns': sum(len(cols) for cols in self.tables_columns.values()),
            'tables': list(self.tables_columns.keys())
        }


def create_simple_query_rewriter(schema_csv_path: Optional[Path] = None) -> SimpleQueryRewriter:
    """Factory function to create a SimpleQueryRewriter instance"""
    return SimpleQueryRewriter(schema_csv_path=schema_csv_path)


def test_simple_query_rewriter():
    """Test the simplified query rewriter"""
    print("🔄 Testing Simple Query Rewriter")
    print("=" * 50)
    
    rewriter = create_simple_query_rewriter()
    
    # Show schema info
    schema_info = rewriter.get_schema_info()
    print(f"Schema Info:")
    print(f"  Tables loaded: {schema_info['table_count']}")
    print(f"  Total columns: {schema_info['total_columns']}")
    print(f"  Sample tables: {', '.join(schema_info['tables'][:5])}{'...' if len(schema_info['tables']) > 5 else ''}")
    
    # Test queries
    test_queries = [
        "How do I find when employeeds were hired?",
        "Show customer orders",
        "Calculate total sales",
        "Find inventory levels",
        "Which suppliers are in the database?"
    ]
    
    print(f"\nTesting query enhancement:")
    print("-" * 30)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        
        result = rewriter.rewrite_query(query)
        
        print(f"   Original: {result['original_query']}")
        print(f"   Enhanced: {result['rewritten_query']}")
        print(f"   Changed: {result['query_changed']}")
        print(f"   Method: {result['method']}")
        
        if result['error']:
            print(f"   Error: {result['error']}")


if __name__ == "__main__":
    test_simple_query_rewriter()