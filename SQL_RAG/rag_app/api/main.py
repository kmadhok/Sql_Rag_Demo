#!/usr/bin/env python3
"""
FastAPI entry point exposing the Query Search LLM pipeline.

This wraps the same services that Streamlit uses so other clients
can call the pipeline without depending on Streamlit.
"""

from __future__ import annotations

import os
import logging
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

from services.query_search_service import (
    QuerySearchSettings,
    QuerySearchResult,
    run_query_search,
)
from services.sql_execution_service import (
    SQLExecutionSettings,
    SQLExecutionResponse,
    initialize_executor,
    run_sql_execution,
)
from services.saved_query_store import (
    save_query,
    list_saved_queries,
    load_saved_query,
    SavedQuery as StoredQuery,
)
from services.dashboard_store import (
    create_dashboard,
    update_dashboard,
    list_dashboards,
    load_dashboard,
    delete_dashboard,
    duplicate_dashboard,
    Dashboard as StoredDashboard,
)
from data.app_data_loader import (
    load_vector_store,
    load_schema_manager,
    load_lookml_safe_join_map,
    DEFAULT_VECTOR_STORE,
)

app = FastAPI(title="SQL RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic request/response models ------------------------------------------------


class SearchRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Natural language question")
    k: int = Field(20, ge=1, le=100, description="Number of documents to retrieve")
    gemini_mode: bool = False
    hybrid_search: bool = False
    auto_adjust_weights: bool = True
    query_rewriting: bool = False
    sql_validation: bool = False
    validation_level: Optional[str] = Field(
        None, description="ValidationLevel enum name (e.g., SCHEMA_STRICT)"
    )
    excluded_tables: Optional[List[str]] = None
    user_context: Optional[str] = ""
    conversation_context: Optional[str] = ""
    agent_type: Optional[str] = None
    search_weights: Optional[Dict[str, float]] = None
    llm_model: Optional[str] = Field(
        None, description="Override the default generation model"
    )


class SourceDocument(BaseModel):
    content: str
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    answer: Optional[str]
    sql: Optional[str]
    cleaned_sql: Optional[str] = None
    sources: List[SourceDocument]
    usage: Dict[str, Any]


class ExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    dry_run: bool = False
    max_bytes_billed: int = Field(100_000_000, ge=10_000_000)
    project_id: Optional[str] = None
    dataset_id: Optional[str] = None


class ExecuteResponse(BaseModel):
    success: bool
    error_message: Optional[str]
    validation_message: Optional[str]
    metadata: Dict[str, Any]
    data: Optional[List[Dict[str, Any]]] = None
    job_id: Optional[str] = None
    bytes_processed: Optional[int] = None
    bytes_billed: Optional[int] = None
    total_rows: Optional[int] = None
    execution_time: Optional[float] = None
    cache_hit: Optional[bool] = None
    dry_run: Optional[bool] = None


# AI Assistant Request/Response Models (Week 3)


class ExplainSQLRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="SQL query to explain")


class ExplainSQLResponse(BaseModel):
    success: bool
    explanation: Optional[str] = None
    tables_analyzed: List[str] = []
    error: Optional[str] = None


class CompleteSQLRequest(BaseModel):
    partial_sql: str = Field(..., description="Partial SQL query before cursor")
    cursor_position: Dict[str, int] = Field(..., description="Cursor position {line, column}")


class SQLCompletion(BaseModel):
    completion: str
    explanation: str


class CompleteSQLResponse(BaseModel):
    success: bool
    suggestions: List[SQLCompletion] = []
    error: Optional[str] = None


class FixSQLRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="Broken SQL query")
    error_message: str = Field(..., description="Error message from execution")


class FixSQLResponse(BaseModel):
    success: bool
    diagnosis: Optional[str] = None
    fixed_sql: Optional[str] = None
    changes: Optional[str] = None
    error: Optional[str] = None


class QuickRequest(BaseModel):
    question: str = Field(..., min_length=2)
    conversation_context: Optional[str] = ""
    k: int = Field(6, ge=1, le=50)
    llm_model: Optional[str] = None


class QuickResponse(BaseModel):
    answer: Optional[str]
    usage: Dict[str, Any] = {}
    sources: List[SourceDocument] = []


class SavedQuerySummary(BaseModel):
    id: str
    question: str
    created_at: str
    row_count: int


class SavedQueryDetail(SavedQuerySummary):
    sql: str
    data_preview: List[Dict[str, Any]]


class SaveQueryRequest(BaseModel):
    question: str
    sql: str
    data: Optional[List[Dict[str, Any]]] = None


class DashboardSummary(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    chart_count: int


class DashboardDetail(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    layout_items: List[Dict[str, Any]]


class CreateDashboardRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    layout_items: Optional[List[Dict[str, Any]]] = None


class UpdateDashboardRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    layout_items: Optional[List[Dict[str, Any]]] = None


# Application state ----------------------------------------------------------------


VECTOR_STORE: Optional[FAISS] = None
SCHEMA_MANAGER = None
LOOKML_SAFE_JOIN_MAP = None
BIGQUERY_EXECUTOR = None
AI_ASSISTANT_SERVICE = None  # Week 3: AI-powered SQL assistance


@app.on_event("startup")
def startup_event() -> None:
    global VECTOR_STORE, SCHEMA_MANAGER, LOOKML_SAFE_JOIN_MAP, BIGQUERY_EXECUTOR, AI_ASSISTANT_SERVICE
    if VECTOR_STORE is None:
        index_name = os.getenv("VECTOR_STORE_NAME") or DEFAULT_VECTOR_STORE
        logging.getLogger(__name__).info(f"Loading vector store index: {index_name}")
        VECTOR_STORE = load_vector_store(index_name)
        if VECTOR_STORE is None:
            raise RuntimeError(f"No vector store available (index: {index_name}). Run embedding generator first.")
    if SCHEMA_MANAGER is None:
        SCHEMA_MANAGER = load_schema_manager()
    if LOOKML_SAFE_JOIN_MAP is None:
        LOOKML_SAFE_JOIN_MAP = load_lookml_safe_join_map()
    if BIGQUERY_EXECUTOR is None:
        try:
            BIGQUERY_EXECUTOR = initialize_executor(SQLExecutionSettings())
        except Exception:
            BIGQUERY_EXECUTOR = None

    # Initialize AI Assistant Service (Week 3)
    if AI_ASSISTANT_SERVICE is None:
        try:
            from services.ai_assistant_service import get_ai_assistant_service
            AI_ASSISTANT_SERVICE = get_ai_assistant_service()
            logging.getLogger(__name__).info("✅ AI Assistant Service initialized")
        except Exception as e:
            logging.getLogger(__name__).warning(f"⚠️ AI Assistant Service not available: {e}")
            AI_ASSISTANT_SERVICE = None


def get_vector_store() -> FAISS:
    if VECTOR_STORE is None:
        raise HTTPException(status_code=500, detail="Vector store not loaded")
    return VECTOR_STORE


def get_schema_manager():
    return SCHEMA_MANAGER


def get_lookml_safe_join_map():
    return LOOKML_SAFE_JOIN_MAP


def get_bigquery_executor():
    return BIGQUERY_EXECUTOR


def get_ai_assistant_service():
    """Get AI Assistant Service instance (Week 3)"""
    if AI_ASSISTANT_SERVICE is None:
        raise HTTPException(
            status_code=503,
            detail="AI Assistant Service not available. Check Gemini API configuration."
        )
    return AI_ASSISTANT_SERVICE


# Routes ----------------------------------------------------------------------------


@app.get("/health")
def health():
    return {
        "status": "ok",
        "vector_store": VECTOR_STORE is not None,
        "schema_manager": SCHEMA_MANAGER is not None,
        "lookml": LOOKML_SAFE_JOIN_MAP is not None,
        "bigquery_executor": BIGQUERY_EXECUTOR is not None,
    }


@app.post("/query/search", response_model=SearchResponse)
def query_search(
    payload: SearchRequest,
    vector_store: FAISS = Depends(get_vector_store),
    schema_manager=Depends(get_schema_manager),
    lookml=Depends(get_lookml_safe_join_map),
):
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="Question is empty.")

    validation_level = None
    if payload.validation_level:
        from core.sql_validator import ValidationLevel  # Lazy import to avoid global dependency issues

        validation_level = getattr(ValidationLevel, payload.validation_level, None)

    search_weights = None
    if payload.search_weights:
        from hybrid_retriever import SearchWeights  # Lazy import

        try:
            search_weights = SearchWeights(
                vector_weight=payload.search_weights.get("vector_weight", 0.5),
                keyword_weight=payload.search_weights.get("keyword_weight", 0.5),
            )
        except Exception:
            search_weights = None

    settings = QuerySearchSettings(
        k=payload.k,
        gemini_mode=payload.gemini_mode,
        hybrid_search=payload.hybrid_search,
        auto_adjust_weights=payload.auto_adjust_weights,
        query_rewriting=payload.query_rewriting,
        sql_validation=payload.sql_validation,
        validation_level=validation_level,
        excluded_tables=payload.excluded_tables,
        user_context=payload.user_context or "",
        conversation_context=payload.conversation_context or "",
        agent_type=payload.agent_type,
        search_weights=search_weights,
        llm_model=payload.llm_model,
    )

    result: QuerySearchResult = run_query_search(
        payload.question,
        vector_store=vector_store,
        schema_manager=schema_manager,
        lookml_safe_join_map=lookml,
        settings=settings,
    )

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    # Extract clean SQL using LLM for better formatting
    cleaned_sql = None
    if result.sql or result.answer_text:
        try:
            from services.sql_extraction_service import get_sql_extraction_service
            sql_service = get_sql_extraction_service()
            # Extract from answer text first (may contain formatted SQL in markdown)
            text_to_extract = result.answer_text or ""
            cleaned_sql = sql_service.extract_sql(text_to_extract, prefer_llm=True, debug=False)
            # Fallback to result.sql if extraction fails
            if not cleaned_sql:
                cleaned_sql = result.sql
        except Exception as e:
            logging.getLogger(__name__).warning(f"SQL extraction failed: {e}")
            cleaned_sql = result.sql

    sources = []
    for doc in result.sources:
        sources.append(
            SourceDocument(
                content=getattr(doc, "page_content", ""),
                metadata=getattr(doc, "metadata", {}) or {},
            )
        )

    return SearchResponse(
        answer=result.answer_text,
        sql=result.sql,
        cleaned_sql=cleaned_sql,
        sources=sources,
        usage=result.usage,
    )


@app.post("/sql/execute", response_model=ExecuteResponse)
def execute_sql(
    payload: ExecuteRequest,
    executor=Depends(get_bigquery_executor),
):
    if executor is None:
        raise HTTPException(status_code=503, detail="BigQuery executor not available.")

    settings = SQLExecutionSettings(
        project_id=payload.project_id or executor.project_id,
        dataset_id=payload.dataset_id or executor.dataset_id,
        dry_run=payload.dry_run,
        max_bytes_billed=payload.max_bytes_billed,
    )

    response: SQLExecutionResponse = run_sql_execution(
        payload.sql,
        executor=executor,
        settings=settings,
    )

    data: Optional[List[Dict[str, Any]]] = None
    if response.result and response.result.data is not None:
        data = response.result.data.to_dict(orient="records")

    result_fields = {}
    if response.result:
        result_fields.update(
            dict(
                job_id=response.result.job_id,
                bytes_processed=getattr(response.result, "bytes_processed", None),
                bytes_billed=getattr(response.result, "bytes_billed", None),
                total_rows=getattr(response.result, "total_rows", None),
                execution_time=getattr(response.result, "execution_time", None),
                cache_hit=getattr(response.result, "cache_hit", None),
                dry_run=getattr(response.result, "dry_run", None),
            )
        )

    return ExecuteResponse(
        success=response.success,
        error_message=response.error_message,
        validation_message=response.validation_message,
        metadata=response.metadata,
        data=data,
        **result_fields,
    )


# AI-Powered SQL Assistance Endpoints (Week 3) --------------------------------


@app.post("/sql/explain", response_model=ExplainSQLResponse)
def explain_sql_query(
    payload: ExplainSQLRequest,
    ai_service=Depends(get_ai_assistant_service),
    schema_manager=Depends(get_schema_manager),
):
    """
    Generate human-readable explanation of SQL query using Gemini AI.

    Week 3 Feature: AI-powered SQL explanations
    """
    try:
        # Extract table names from SQL
        table_names = schema_manager.extract_tables_from_content(payload.sql)

        # Get schema context
        schema_context = schema_manager.get_relevant_schema(
            table_names,
            max_tables=10,
            include_bigquery_guidance=True
        )

        # Generate explanation
        explanation = ai_service.explain_sql(payload.sql, schema_context)

        return ExplainSQLResponse(
            success=True,
            explanation=explanation,
            tables_analyzed=table_names,
            error=None
        )

    except Exception as e:
        logger.error(f"Error explaining SQL: {str(e)}")
        return ExplainSQLResponse(
            success=False,
            explanation=None,
            tables_analyzed=[],
            error=str(e)
        )


@app.post("/sql/complete", response_model=CompleteSQLResponse)
def complete_sql_query(
    payload: CompleteSQLRequest,
    ai_service=Depends(get_ai_assistant_service),
    schema_manager=Depends(get_schema_manager),
):
    """
    Suggest SQL completions using Gemini AI for autocomplete.

    Week 3 Feature: AI-powered autocomplete
    """
    try:
        # Get schema context for completions (use all tables, limited to 20)
        all_tables = schema_manager.get_all_tables()
        schema_context = schema_manager.get_relevant_schema(
            all_tables[:20],
            max_tables=20,
            include_bigquery_guidance=False
        )

        # Generate completions
        suggestions = ai_service.complete_sql(
            payload.partial_sql,
            payload.cursor_position,
            schema_context
        )

        # Convert to Pydantic models
        completions = [
            SQLCompletion(
                completion=s.get("completion", ""),
                explanation=s.get("explanation", "")
            )
            for s in suggestions
        ]

        return CompleteSQLResponse(
            success=True,
            suggestions=completions,
            error=None
        )

    except Exception as e:
        logger.error(f"Error completing SQL: {str(e)}")
        return CompleteSQLResponse(
            success=False,
            suggestions=[],
            error=str(e)
        )


@app.post("/sql/fix", response_model=FixSQLResponse)
def fix_sql_query(
    payload: FixSQLRequest,
    ai_service=Depends(get_ai_assistant_service),
    schema_manager=Depends(get_schema_manager),
):
    """
    Debug and fix broken SQL query using Gemini AI.

    Week 3 Feature: AI-powered SQL debugging
    """
    try:
        # Extract table names from SQL
        table_names = schema_manager.extract_tables_from_content(payload.sql)

        # Get schema context
        schema_context = schema_manager.get_relevant_schema(
            table_names,
            max_tables=10,
            include_bigquery_guidance=True
        )

        # Generate fix
        fix_result = ai_service.fix_sql(
            payload.sql,
            payload.error_message,
            schema_context
        )

        return FixSQLResponse(
            success=True,
            diagnosis=fix_result.get("diagnosis"),
            fixed_sql=fix_result.get("fixed_sql"),
            changes=fix_result.get("changes"),
            error=None
        )

    except Exception as e:
        logger.error(f"Error fixing SQL: {str(e)}")
        return FixSQLResponse(
            success=False,
            diagnosis=None,
            fixed_sql=None,
            changes=None,
            error=str(e)
        )


@app.post("/query/quick", response_model=QuickResponse)
def quick_answer(
    payload: QuickRequest,
    vector_store: FAISS = Depends(get_vector_store),
    schema_manager=Depends(get_schema_manager),
    lookml=Depends(get_lookml_safe_join_map),
):
    settings = QuerySearchSettings(
        k=payload.k,
        gemini_mode=False,
        hybrid_search=False,
        auto_adjust_weights=True,
        query_rewriting=False,
        sql_validation=False,
        user_context="",
        conversation_context=payload.conversation_context or "",
        agent_type=None,
        llm_model=payload.llm_model,
    )

    result = run_query_search(
        payload.question,
        vector_store=vector_store,
        schema_manager=schema_manager,
        lookml_safe_join_map=lookml,
        settings=settings,
    )

    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    sources = [
        SourceDocument(
            content=getattr(doc, "page_content", ""),
            metadata=getattr(doc, "metadata", {}) or {},
        )
        for doc in (result.sources or [])
    ][:5]

    return QuickResponse(
        answer=result.answer_text,
        usage=result.usage,
        sources=sources,
    )


@app.get("/schema/tables")
async def list_schema_tables(schema_manager=Depends(get_schema_manager)):
    if schema_manager is None:
        raise HTTPException(status_code=503, detail="Schema manager not initialized")

    try:
        if hasattr(schema_manager, "get_all_tables"):
            tables = schema_manager.get_all_tables()
        else:
            tables = sorted(getattr(schema_manager, "schema_lookup", {}).keys())

        return {
            "success": True,
            "tables": tables,
            "table_count": len(tables),
        }
    except Exception as exc:
        logger.error("Error fetching schema tables: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/schema/tables/{table_name}/columns")
async def list_table_columns(table_name: str, schema_manager=Depends(get_schema_manager)):
    if schema_manager is None:
        raise HTTPException(status_code=503, detail="Schema manager not initialized")

    try:
        raw_columns = schema_manager.get_schema_for_table(table_name) if hasattr(schema_manager, "get_schema_for_table") else None
        if not raw_columns and hasattr(schema_manager, "get_table_info"):
            table_info = schema_manager.get_table_info(table_name)
            if table_info and table_info.get("columns"):
                datatypes = table_info.get("datatypes") or []
                raw_columns = list(zip(table_info["columns"], datatypes))

        if not raw_columns:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        column_list = []
        for column_entry in raw_columns:
            name = ""
            col_type = ""
            description = ""

            if isinstance(column_entry, (list, tuple)):
                if len(column_entry) > 0:
                    name = column_entry[0]
                if len(column_entry) > 1:
                    col_type = column_entry[1] or ""
                if len(column_entry) > 2:
                    description = column_entry[2] or ""
            elif isinstance(column_entry, dict):
                name = column_entry.get("name") or column_entry.get("column") or ""
                col_type = column_entry.get("type") or column_entry.get("datatype") or ""
                description = column_entry.get("description") or ""
            else:
                name = str(column_entry)

            column_list.append(
                {
                    "name": name,
                    "type": col_type,
                    "description": description,
                }
            )

        fqn = schema_manager.get_fqn(table_name) if hasattr(schema_manager, "get_fqn") else None

        return {
            "success": True,
            "table": table_name,
            "fully_qualified_name": fqn or table_name,
            "columns": column_list,
            "column_count": len(column_list),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching columns for %s: %s", table_name, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/saved_queries", response_model=SavedQueryDetail)
def create_saved_query(payload: SaveQueryRequest):
    saved = save_query(payload.question, payload.sql, payload.data)
    return SavedQueryDetail(
        id=saved.id,
        question=saved.question,
        sql=saved.sql,
        created_at=saved.created_at,
        row_count=saved.row_count,
        data_preview=saved.data_preview,
    )


@app.get("/saved_queries", response_model=List[SavedQuerySummary])
def get_saved_queries():
    return [
        SavedQuerySummary(
            id=sq.id,
            question=sq.question,
            created_at=sq.created_at,
            row_count=sq.row_count,
        )
        for sq in list_saved_queries()
    ]


@app.get("/saved_queries/{query_id}", response_model=SavedQueryDetail)
def get_saved_query(query_id: str):
    saved = load_saved_query(query_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved query not found")
    return SavedQueryDetail(
        id=saved.id,
        question=saved.question,
        sql=saved.sql,
        created_at=saved.created_at,
        row_count=saved.row_count,
        data_preview=saved.data_preview,
    )


# Dashboard endpoints ---------------------------------------------------------------


@app.post("/dashboards", response_model=DashboardDetail)
def create_new_dashboard(payload: CreateDashboardRequest):
    dashboard = create_dashboard(payload.name, payload.layout_items)
    return DashboardDetail(
        id=dashboard.id,
        name=dashboard.name,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
        layout_items=dashboard.layout_items,
    )


@app.get("/dashboards", response_model=List[DashboardSummary])
def get_dashboards():
    return [
        DashboardSummary(
            id=d.id,
            name=d.name,
            created_at=d.created_at,
            updated_at=d.updated_at,
            chart_count=len(d.layout_items),
        )
        for d in list_dashboards()
    ]


@app.get("/dashboards/{dashboard_id}", response_model=DashboardDetail)
def get_dashboard(dashboard_id: str):
    dashboard = load_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return DashboardDetail(
        id=dashboard.id,
        name=dashboard.name,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
        layout_items=dashboard.layout_items,
    )


@app.patch("/dashboards/{dashboard_id}", response_model=DashboardDetail)
def update_existing_dashboard(dashboard_id: str, payload: UpdateDashboardRequest):
    dashboard = update_dashboard(dashboard_id, payload.name, payload.layout_items)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return DashboardDetail(
        id=dashboard.id,
        name=dashboard.name,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
        layout_items=dashboard.layout_items,
    )


@app.post("/dashboards/{dashboard_id}/duplicate", response_model=DashboardDetail)
def duplicate_existing_dashboard(dashboard_id: str):
    duplicated = duplicate_dashboard(dashboard_id)
    if not duplicated:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return DashboardDetail(
        id=duplicated.id,
        name=duplicated.name,
        created_at=duplicated.created_at,
        updated_at=duplicated.updated_at,
        layout_items=duplicated.layout_items,
    )


@app.delete("/dashboards/{dashboard_id}")
def delete_existing_dashboard(dashboard_id: str):
    success = delete_dashboard(dashboard_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return {"message": "Dashboard deleted successfully"}


class QuickRequest(BaseModel):
    question: str = Field(..., min_length=2)
    conversation_context: Optional[str] = ""
    k: int = Field(6, ge=1, le=50)


class QuickResponse(BaseModel):
    answer: Optional[str]
    usage: Dict[str, Any] = {}
    sources: List[SourceDocument] = []
