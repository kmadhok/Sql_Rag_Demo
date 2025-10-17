#!/usr/bin/env python3
"""
LLM-Based SQL Analyzer

Uses Google Gemini 2.5 Flash with structured outputs to analyze SQL queries
for table and column extraction, replacing complex regex-based parsing.

This approach is more reliable, maintainable, and handles edge cases like CTEs,
aliases, and complex SQL patterns that regex struggles with.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field

# Import Gemini client (reuse existing integration)
try:
    from gemini_client import GeminiClient
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import sys
        sys.path.append('..')
        from gemini_client import GeminiClient
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False
        logging.warning("Gemini client not available for LLM SQL analysis")

logger = logging.getLogger(__name__)

# Pydantic schemas for structured outputs
class TableAlias(BaseModel):
    alias: str = Field(description="Alias name used in the SQL query")
    table: str = Field(description="Actual table name that the alias refers to")


class ColumnRef(BaseModel):
    table: str = Field(description="Actual table name for the column")
    column: str = Field(description="Column name referenced in the SQL query")


class ColumnAlias(BaseModel):
    alias: str = Field(description="Alias name used for the column in the SQL query")
    column: str = Field(description="Actual column name that the alias refers to")


class SQLTableAnalysis(BaseModel):
    """Analysis of tables referenced in SQL queries"""
    actual_tables: List[str] = Field(description="Real database table names (exclude CTEs, temp tables)")
    cte_tables: List[str] = Field(description="Common Table Expression (CTE) names")
    table_aliases: List[TableAlias] = Field(description="List mapping alias to actual table name")
    subquery_tables: List[str] = Field(description="Tables referenced in subqueries")


class SQLColumnAnalysis(BaseModel):
    """Analysis of columns referenced in SQL queries"""
    columns: List[ColumnRef] = Field(description="List of column mappings: [{\"table\": \"users\", \"column\": \"id\"}]")
    column_aliases: List[ColumnAlias] = Field(description="List mapping column alias to actual column name")
    aggregate_columns: List[str] = Field(description="Columns used in aggregate functions")
    computed_columns: List[str] = Field(description="Computed/calculated column expressions")

class CacheStrategy(Enum):
    """Caching strategy for LLM analysis"""
    NONE = "none"
    MEMORY = "memory"
    DISK = "disk"
    BOTH = "both"

@dataclass
class AnalysisResult:
    """Result of LLM SQL analysis"""
    table_analysis: Optional[SQLTableAnalysis]
    column_analysis: Optional[SQLColumnAnalysis]
    cache_hit: bool
    analysis_time: float
    tokens_used: int
    cost_estimate: float

class LLMSQLAnalyzer:
    """
    LLM-based SQL analyzer using Gemini 2.5 Flash for intelligent SQL parsing
    """
    
    def __init__(self, 
                 model: str = os.getenv("LLM_PARSE_MODEL", "gemini-2.5-flash-lite"),
                 cache_strategy: CacheStrategy = CacheStrategy.BOTH,
                 cache_dir: str = "llm_sql_cache",
                 cost_per_1m_tokens: float = 0.075):
        """
        Initialize LLM SQL analyzer
        
        Args:
            model: Gemini model to use for analysis
            cache_strategy: Strategy for caching analysis results
            cache_dir: Directory for disk cache
            cost_per_1m_tokens: Cost per 1M tokens for cost estimation
        """
        self.model = model
        self.cache_strategy = cache_strategy
        self.cache_dir = Path(cache_dir)
        self.cost_per_1m_tokens = cost_per_1m_tokens
        
        # Initialize caches
        self.memory_cache: Dict[str, AnalysisResult] = {}
        
        # Initialize disk cache directory
        if self.cache_strategy in [CacheStrategy.DISK, CacheStrategy.BOTH]:
            self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize Gemini client
        if GEMINI_AVAILABLE:
            self.llm = GeminiClient(model=self.model)
            logger.info(f"🤖 LLM SQL Analyzer initialized with {self.model}")
        else:
            self.llm = None
            logger.warning("⚠️ Gemini client unavailable - LLM SQL analysis disabled")
    
    def _generate_cache_key(self, sql: str, analysis_type: str) -> str:
        """Generate cache key for SQL analysis"""
        content = f"{analysis_type}:{sql.strip().lower()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[AnalysisResult]:
        """Retrieve analysis result from cache"""
        # Check memory cache first
        if self.cache_strategy in [CacheStrategy.MEMORY, CacheStrategy.BOTH]:
            if cache_key in self.memory_cache:
                result = self.memory_cache[cache_key]
                result.cache_hit = True
                logger.debug(f"📋 Cache hit (memory): {cache_key[:8]}...")
                return result
        
        # Check disk cache
        if self.cache_strategy in [CacheStrategy.DISK, CacheStrategy.BOTH]:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    
                    # Reconstruct result
                    result = AnalysisResult(
                        table_analysis=SQLTableAnalysis(**data['table_analysis']) if data.get('table_analysis') else None,
                        column_analysis=SQLColumnAnalysis(**data['column_analysis']) if data.get('column_analysis') else None,
                        cache_hit=True,
                        analysis_time=data.get('analysis_time', 0),
                        tokens_used=data.get('tokens_used', 0),
                        cost_estimate=data.get('cost_estimate', 0)
                    )
                    
                    # Also store in memory cache
                    if self.cache_strategy == CacheStrategy.BOTH:
                        self.memory_cache[cache_key] = result
                    
                    logger.debug(f"💾 Cache hit (disk): {cache_key[:8]}...")
                    return result
                    
                except Exception as e:
                    logger.warning(f"Failed to load cache file {cache_file}: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, result: AnalysisResult):
        """Save analysis result to cache"""
        # Save to memory cache
        if self.cache_strategy in [CacheStrategy.MEMORY, CacheStrategy.BOTH]:
            self.memory_cache[cache_key] = result
        
        # Save to disk cache
        if self.cache_strategy in [CacheStrategy.DISK, CacheStrategy.BOTH]:
            try:
                cache_file = self.cache_dir / f"{cache_key}.json"
                data = {
                    'table_analysis': result.table_analysis.dict() if result.table_analysis else None,
                    'column_analysis': result.column_analysis.dict() if result.column_analysis else None,
                    'analysis_time': result.analysis_time,
                    'tokens_used': result.tokens_used,
                    'cost_estimate': result.cost_estimate
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                logger.debug(f"💾 Cached analysis: {cache_key[:8]}...")
                
            except Exception as e:
                logger.warning(f"Failed to save cache file: {e}")
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count"""
        # Approximation: 1 token ≈ 4 characters for most text
        return len(text) // 4
    
    def _calculate_cost(self, tokens: int) -> float:
        """Calculate estimated cost for token usage"""
        return (tokens / 1_000_000) * self.cost_per_1m_tokens
    
    def extract_tables_from_sql(self, sql: str) -> AnalysisResult:
        """
        Extract actual database tables from SQL using LLM analysis
        
        Args:
            sql: SQL query to analyze
            
        Returns:
            AnalysisResult with table analysis
        """
        if not self.llm:
            logger.warning("LLM not available for table extraction")
            return AnalysisResult(None, None, False, 0, 0, 0)
        
        cache_key = self._generate_cache_key(sql, "tables")
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Build prompt for table extraction
        prompt = f"""Analyze this SQL query and extract table information.

IMPORTANT:
- Only include ACTUAL DATABASE TABLES in 'actual_tables'
- DO NOT include CTEs (Common Table Expressions), temporary tables, or derived tables
- DO NOT include aliases in 'actual_tables' - only real table names
- If you see WITH clauses, those create CTEs - put those names in 'cte_tables'
- 'table_aliases' must be an array of objects: {{"alias": "u", "table": "dataset.users"}}

SQL Query:
```sql
{sql}
```

Return analysis in the specified JSON format."""

        start_time = time.time()
        
        try:
            # Define a Gemini-compatible schema without additionalProperties
            table_schema = {
                "type": "OBJECT",
                "properties": {
                    "actual_tables": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "cte_tables": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "table_aliases": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "alias": {"type": "STRING"},
                                "table": {"type": "STRING"}
                            }
                        }
                    },
                    "subquery_tables": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": [
                    "actual_tables",
                    "cte_tables",
                    "table_aliases",
                    "subquery_tables"
                ]
            }

            # Use structured output with explicit schema dict (no additionalProperties)
            response = self.llm.invoke_structured(
                prompt,
                response_format="json",
                response_schema=table_schema
            )
            
            analysis_time = time.time() - start_time
            tokens_used = self._estimate_tokens(prompt + response)
            cost_estimate = self._calculate_cost(tokens_used)
            
            # Parse the response
            table_analysis = SQLTableAnalysis.parse_raw(response)
            
            result = AnalysisResult(
                table_analysis=table_analysis,
                column_analysis=None,
                cache_hit=False,
                analysis_time=analysis_time,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate
            )
            
            # Cache the result
            self._save_to_cache(cache_key, result)
            
            logger.info(f"🤖 LLM table extraction: {len(table_analysis.actual_tables)} tables, "
                       f"{analysis_time:.2f}s, ~${cost_estimate:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM table extraction failed: {e}")
            return AnalysisResult(None, None, False, time.time() - start_time, 0, 0)
    
    def extract_columns_from_sql(self, sql: str, available_tables: Optional[List[str]] = None) -> AnalysisResult:
        """
        Extract column references from SQL using LLM analysis
        
        Args:
            sql: SQL query to analyze
            available_tables: List of available table names for context
            
        Returns:
            AnalysisResult with column analysis
        """
        if not self.llm:
            logger.warning("LLM not available for column extraction")
            return AnalysisResult(None, None, False, 0, 0, 0)
        
        cache_key = self._generate_cache_key(f"{sql}:{available_tables}", "columns")
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Build prompt for column extraction
        table_context = ""
        if available_tables:
            table_context = f"\nAvailable tables: {', '.join(available_tables)}"
        
        prompt = f"""Analyze this SQL query and extract all column references.

IMPORTANT:
- Map each column to its table (handle aliases properly)
- For qualified columns like 'u.id', map to actual table name like 'users.id'
- For unqualified columns, infer the table from context
- Include ALL column references: SELECT, WHERE, GROUP BY, ORDER BY, JOIN conditions, etc.
- 'columns' must be an array of objects: {{"table": "dataset.users", "column": "id"}}
- 'column_aliases' must be an array of objects: {{"alias": "revenue", "column": "SUM(sale_price)"}}

SQL Query:
```sql
{sql}
```{table_context}

Return analysis in the specified JSON format with columns as list of {{"table": "table_name", "column": "column_name"}}."""

        start_time = time.time()
        
        try:
            # Define a Gemini-compatible schema without additionalProperties
            column_schema = {
                "type": "OBJECT",
                "properties": {
                    "columns": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "table": {"type": "STRING"},
                                "column": {"type": "STRING"}
                            }
                        }
                    },
                    "column_aliases": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "alias": {"type": "STRING"},
                                "column": {"type": "STRING"}
                            }
                        }
                    },
                    "aggregate_columns": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "computed_columns": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": [
                    "columns",
                    "column_aliases",
                    "aggregate_columns",
                    "computed_columns"
                ]
            }

            # Use structured output with explicit schema dict (no additionalProperties)
            response = self.llm.invoke_structured(
                prompt,
                response_format="json",
                response_schema=column_schema
            )
            
            analysis_time = time.time() - start_time
            tokens_used = self._estimate_tokens(prompt + response)
            cost_estimate = self._calculate_cost(tokens_used)
            
            # Parse the response
            column_analysis = SQLColumnAnalysis.parse_raw(response)
            
            result = AnalysisResult(
                table_analysis=None,
                column_analysis=column_analysis,
                cache_hit=False,
                analysis_time=analysis_time,
                tokens_used=tokens_used,
                cost_estimate=cost_estimate
            )
            
            # Cache the result
            self._save_to_cache(cache_key, result)
            
            logger.info(f"🤖 LLM column extraction: {len(column_analysis.columns)} columns, "
                       f"{analysis_time:.2f}s, ~${cost_estimate:.6f}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM column extraction failed: {e}")
            return AnalysisResult(None, None, False, time.time() - start_time, 0, 0)
    
    def analyze_sql_comprehensive(self, sql: str, available_tables: Optional[List[str]] = None) -> AnalysisResult:
        """
        Perform comprehensive SQL analysis (both tables and columns)
        
        Args:
            sql: SQL query to analyze
            available_tables: List of available table names for context
            
        Returns:
            AnalysisResult with both table and column analysis
        """
        cache_key = self._generate_cache_key(f"{sql}:{available_tables}", "comprehensive")
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Run both analyses
        table_result = self.extract_tables_from_sql(sql)
        column_result = self.extract_columns_from_sql(sql, available_tables)
        
        # Combine results
        result = AnalysisResult(
            table_analysis=table_result.table_analysis,
            column_analysis=column_result.column_analysis,
            cache_hit=False,
            analysis_time=table_result.analysis_time + column_result.analysis_time,
            tokens_used=table_result.tokens_used + column_result.tokens_used,
            cost_estimate=table_result.cost_estimate + column_result.cost_estimate
        )
        
        # Cache the combined result
        self._save_to_cache(cache_key, result)
        
        return result
    
    def clear_cache(self, cache_type: str = "both"):
        """
        Clear analysis cache
        
        Args:
            cache_type: Type of cache to clear ("memory", "disk", "both")
        """
        if cache_type in ["memory", "both"]:
            self.memory_cache.clear()
            logger.info("🗑️ Cleared memory cache")
        
        if cache_type in ["disk", "both"]:
            try:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink()
                logger.info("🗑️ Cleared disk cache")
            except Exception as e:
                logger.warning(f"Failed to clear disk cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        stats = {
            "memory_entries": len(self.memory_cache),
            "disk_entries": 0
        }
        
        try:
            if self.cache_dir.exists():
                stats["disk_entries"] = len(list(self.cache_dir.glob("*.json")))
        except Exception:
            pass
        
        return stats

# Global instance (can be configured)
_global_analyzer: Optional[LLMSQLAnalyzer] = None

def get_analyzer() -> LLMSQLAnalyzer:
    """Get global LLM SQL analyzer instance"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = LLMSQLAnalyzer()
    return _global_analyzer

def extract_tables_with_llm(sql: str) -> List[str]:
    """
    Convenience function to extract actual tables from SQL
    
    Args:
        sql: SQL query to analyze
        
    Returns:
        List of actual database table names (no CTEs, aliases, etc.)
    """
    analyzer = get_analyzer()
    result = analyzer.extract_tables_from_sql(sql)
    
    if result.table_analysis:
        return result.table_analysis.actual_tables
    else:
        logger.warning("Failed to extract tables with LLM, returning empty list")
        return []

def extract_columns_with_llm(sql: str, available_tables: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """
    Convenience function to extract columns from SQL
    
    Args:
        sql: SQL query to analyze
        available_tables: List of available table names for context
        
    Returns:
        List of column mappings: [{"table": "users", "column": "id"}]
    """
    analyzer = get_analyzer()
    result = analyzer.extract_columns_from_sql(sql, available_tables)
    
    if result.column_analysis:
        return result.column_analysis.columns
    else:
        logger.warning("Failed to extract columns with LLM, returning empty list")
        return []

if __name__ == "__main__":
    # Test the LLM SQL analyzer
    analyzer = LLMSQLAnalyzer()
    
    test_sql = """
    WITH user_sale AS (
      SELECT user_id, SUM(sale_price) AS revenue
      FROM `bigquery-public-data.thelook_ecommerce.order_items`
      GROUP BY user_id
    )
    SELECT u.id AS user_id, us.revenue
    FROM `bigquery-public-data.thelook_ecommerce.users` u
    LEFT JOIN user_sale us ON u.id = us.user_id
    ORDER BY revenue DESC
    """
    
    print("🧪 Testing LLM SQL Analyzer")
    print("=" * 50)
    
    # Test table extraction
    table_result = analyzer.extract_tables_from_sql(test_sql)
    print(f"Tables: {table_result.table_analysis.actual_tables if table_result.table_analysis else 'None'}")
    print(f"CTEs: {table_result.table_analysis.cte_tables if table_result.table_analysis else 'None'}")
    
    # Test column extraction
    column_result = analyzer.extract_columns_from_sql(test_sql)
    print(f"Columns: {column_result.column_analysis.columns if column_result.column_analysis else 'None'}")
    
    print(f"Total cost: ~${(table_result.cost_estimate + column_result.cost_estimate):.6f}")
