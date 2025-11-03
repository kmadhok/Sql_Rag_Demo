"""
SQL Assistant Prompt Templates for AI-Powered SQL Playground

Provides optimized prompts for:
- SQL Explanation: Explain queries step-by-step
- SQL Completion: Autocomplete suggestions
- SQL Fix: Debug and fix broken queries
"""

from typing import Optional


def get_explain_prompt(sql: str, schema_context: str) -> str:
    """
    Generate prompt for explaining SQL queries.

    Args:
        sql: SQL query to explain
        schema_context: Relevant database schema information

    Returns:
        Formatted prompt for SQL explanation
    """
    return f"""You are a SQL Explanation Expert for BigQuery. Provide a clear, step-by-step explanation of the SQL query below.

RELEVANT SCHEMA:
{schema_context}

SQL QUERY TO EXPLAIN:
{sql}

Provide a comprehensive explanation that covers:

1. **What data is being retrieved**: Describe the main purpose and expected output
2. **Tables involved**: List all tables and how they're used
3. **Joins and relationships**: Explain how tables are connected (if applicable)
4. **Filters and conditions**: Describe WHERE clauses and what they filter
5. **Aggregations**: Explain GROUP BY, aggregation functions, and HAVING clauses
6. **Ordering and limits**: Describe sorting and result limitations
7. **Expected output structure**: What columns and rows will be returned

Use simple, clear language suitable for intermediate SQL users. Focus on the "why" and "how" of the query.

EXPLANATION:"""


def get_complete_prompt(partial_sql: str, cursor_position: dict, schema_context: str) -> str:
    """
    Generate prompt for SQL autocomplete suggestions.

    Args:
        partial_sql: Incomplete SQL query (text before cursor)
        cursor_position: Cursor location {"line": int, "column": int}
        schema_context: Relevant database schema information

    Returns:
        Formatted prompt for SQL completion
    """
    return f"""You are a BigQuery SQL autocomplete assistant. Provide 3 completion suggestions for the partial query below.

AVAILABLE SCHEMA:
{schema_context}

PARTIAL SQL QUERY:
{partial_sql}

CURSOR POSITION: Line {cursor_position.get('line', 1)}, Column {cursor_position.get('column', 1)}

Provide 3 ranked completion suggestions. For each suggestion:
1. The completion text (what should be inserted at the cursor)
2. A brief explanation of what it does

**IMPORTANT RULES:**
- Only suggest valid BigQuery SQL syntax
- Use fully-qualified table names (project.dataset.table)
- Prioritize completions based on context (what comes logically next)
- Keep suggestions concise and practical
- Consider the schema - only suggest tables/columns that exist

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "suggestions": [
    {{"completion": "table_name", "explanation": "Brief explanation"}},
    {{"completion": "column_name", "explanation": "Brief explanation"}},
    {{"completion": "SQL clause", "explanation": "Brief explanation"}}
  ]
}}

JSON RESPONSE:"""


def get_fix_prompt(broken_sql: str, error_message: str, schema_context: str) -> str:
    """
    Generate prompt for debugging and fixing broken SQL.

    Args:
        broken_sql: SQL query that failed
        error_message: Error message from BigQuery
        schema_context: Relevant database schema information

    Returns:
        Formatted prompt for SQL fix
    """
    return f"""You are a BigQuery SQL debugging expert. Fix the broken SQL query below.

AVAILABLE SCHEMA:
{schema_context}

BROKEN SQL QUERY:
{broken_sql}

ERROR MESSAGE:
{error_message}

Analyze the error and provide a fix. Your response should include:
1. **Diagnosis**: What's wrong with the query (root cause)
2. **Fixed SQL**: The corrected query that will execute successfully
3. **Changes**: Explain what was changed and why

**IMPORTANT RULES:**
- Only fix the specific error - don't rewrite the entire query
- Use fully-qualified table names (project.dataset.table)
- Ensure the fixed query is valid BigQuery SQL
- Keep the original intent of the query
- Reference the schema to validate table/column names

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "diagnosis": "Clear explanation of what's wrong",
  "fixed_sql": "Corrected SQL query",
  "changes": "Summary of what was changed and why"
}}

JSON RESPONSE:"""


def get_schema_guidance() -> str:
    """
    Returns BigQuery-specific guidance for all prompts.

    Returns:
        Common BigQuery best practices text
    """
    return """
**BIGQUERY BEST PRACTICES:**
- Always use fully-qualified table names: `project.dataset.table`
- Use backticks for table names with special characters: `project.dataset.table-name`
- Prefer ARRAY_AGG over GROUP_CONCAT
- Use SAFE_CAST for type conversions
- Leverage partitioned and clustered tables when available
"""
