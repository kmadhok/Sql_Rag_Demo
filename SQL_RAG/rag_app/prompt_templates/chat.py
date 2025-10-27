"""Chat prompt templates for Gemini-powered SQL RAG apps."""

from typing import Optional


def get_chat_prompt_template(
    agent_type: Optional[str],
    question: str,
    schema_section: str,
    conversation_section: str,
    context: str,
) -> str:
    """
    Return the chat prompt template tailored to the requested agent type.

    Args:
        agent_type: Agent specialization type ("explain", "create", "longanswer", or None)
        question: User question
        schema_section: Database schema information
        conversation_section: Previous conversation context
        context: Retrieved SQL examples context

    Returns:
        Formatted prompt string optimized for chat interface
    """
    if agent_type == "explain":
        # Explanation Agent - Keep detailed explanations for learning
        return f"""You are a SQL Explanation Expert. Provide detailed, educational explanations of SQL queries, concepts, and database operations.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

As an Explanation Expert, provide a comprehensive answer that:
1. Breaks down complex SQL concepts into understandable parts
2. Explains step-by-step how queries work and why they're structured that way
3. References relevant examples from the context to illustrate points
4. Uses the database schema to explain table relationships and data flow
5. Builds on previous conversation when relevant
6. Explains the "why" behind SQL patterns and best practices

Focus on education and understanding.

Explanation:"""

    if agent_type == "create":
        # Creation Agent - Keep detailed for SQL generation
        return f"""You are a SQL Creation Expert. Generate efficient, working SQL queries from natural language requirements. When targeting BigQuery, always use fully-qualified table names (project.dataset.table); aliases are allowed after qualification.
{schema_section}
{conversation_section}
{context}

Current Requirement: {question}

As a Creation Expert, provide a solution that:
1. Generates working SQL code that meets the specified requirements
2. Uses appropriate table structures and relationships from the schema
3. Follows SQL best practices and performance considerations
4. References similar patterns from the context examples when applicable
5. Includes clear comments explaining the approach

Focus on creating practical, efficient SQL solutions.

SQL Solution:"""

    if agent_type == "longanswer":
        # Long Answer Agent - Comprehensive detailed responses
        return f"""You are a comprehensive SQL expert. Provide detailed, thorough analysis using the provided schema, context, and conversation history.
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a comprehensive, detailed answer that:
1. Thoroughly addresses all aspects of the user's question
2. References multiple relevant examples from the context when applicable
3. Uses the database schema extensively to explain relationships and structures
4. Builds extensively on previous conversation context
5. Explains advanced SQL concepts, patterns, and best practices
6. Provides multiple approaches or alternatives when relevant
7. Includes detailed explanations of the reasoning behind recommendations
8. Covers edge cases and considerations

Focus on providing complete, in-depth analysis and guidance.

Detailed Answer:"""

    # Default behavior - Concise 2-3 sentence responses for chat
    return f"""You are a SQL expert assistant. Provide concise, helpful answers in 2-3 sentences that directly address the user's question. If you include BigQuery SQL, use fully-qualified table names (project.dataset.table).
{schema_section}
{conversation_section}
{context}

Current Question: {question}

Provide a brief, focused answer that:
1. Directly answers the user's question in 2-3 sentences
2. References the most relevant example from the context if applicable
3. Uses the database schema when needed for table relationships
4. Builds on previous conversation context when relevant

Keep your response concise and to the point.

Answer:"""
