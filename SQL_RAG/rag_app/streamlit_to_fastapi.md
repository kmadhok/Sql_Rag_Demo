Short answer: yes—but not “as-is.” Streamlit is a UI runtime; FastAPI is an HTTP server. The right move is to reuse your core RAG modules (e.g., simple_rag_simple_gemini.py, gemini_client.py, schema_manager.py, data/app_data_loader.py, optional core/bigquery_executor.py) and expose them via FastAPI endpoints. Keep Streamlit for a GUI if you like, but add a headless API for React, CLI, or other services. (Your repo is already structured to enable this split.  )
Here’s a drop-in FastAPI skeleton that wraps your existing logic.

api/main.py (new)
# api/main.py
from typing import List, Optional, Any, Dict
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---- reuse your modules (no Streamlit here) ----
from simple_rag_simple_gemini import answer_question_simple_gemini
from data.app_data_loader import (
    load_vector_store,
    load_schema_manager,
    load_lookml_safe_join_map,
)
# BigQuery executor is optional; import if available
try:
    from core.bigquery_executor import BigQueryExecutor
    BIGQUERY_OK = True
except Exception:
    BigQueryExecutor = None  # type: ignore
    BIGQUERY_OK = False

# App + CORS
app = FastAPI(title="SQL RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Models ----
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    k: int = 20
    agent_type: Optional[str] = Field(None, description="@create | @explain | @schema | @longanswer")
    user_context: Optional[str] = ""
    excluded_tables: Optional[List[str]] = None
    sql_validation: bool = False  # set True if you want server-side validation

class SourceChunk(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}

class AskResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = []
    usage: Dict[str, Any] = {}

class ExecRequest(BaseModel):
    sql: str
    dry_run: bool = False
    max_bytes_billed: int = 100_000_000

class ExecResponse(BaseModel):
    success: bool
    total_rows: int = 0
    bytes_processed: int = 0
    bytes_billed: int = 0
    execution_time: float = 0.0
    cache_hit: bool = False
    job_id: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None

# ---- Globals (warmed at startup) ----
VECTOR_STORE = None
SCHEMA_MANAGER = None
LOOKML_SAFE_JOIN_MAP = None
BQ_EXECUTOR = None

@app.on_event("startup")
def _startup():
    global VECTOR_STORE, SCHEMA_MANAGER, LOOKML_SAFE_JOIN_MAP, BQ_EXECUTOR

    # Load vector index once (fast API responses + avoids per-request disk IO)
    VECTOR_STORE = load_vector_store(None)  # default index per your app_config fallback
    if VECTOR_STORE is None:
        raise RuntimeError("No FAISS index found. Run embedding generator first.")

    SCHEMA_MANAGER = load_schema_manager()
    LOOKML_SAFE_JOIN_MAP = load_lookml_safe_join_map()

    if BIGQUERY_OK:
        # Prefer env vars; matches your Streamlit executor defaults
        project = os.getenv("BIGQUERY_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "brainrot-453319"
        dataset = os.getenv("BIGQUERY_DATASET") or "bigquery-public-data.thelook_ecommerce"
        BQ_EXECUTOR = BigQueryExecutor(project_id=project, dataset_id=dataset)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "vector_store": VECTOR_STORE is not None,
        "schema_manager": SCHEMA_MANAGER is not None,
        "lookml": LOOKML_SAFE_JOIN_MAP is not None,
        "bigquery": BIGQUERY_OK,
    }

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    if VECTOR_STORE is None:
        raise HTTPException(status_code=500, detail="Vector store not loaded")

    # Fast path for @schema: answer without LLM if you want (optional)
    # If you prefer LLM path only, just call answer_question_simple_gemini below.
    result = answer_question_simple_gemini(
        question=req.question,
        vector_store=VECTOR_STORE,
        k=req.k,
        schema_manager=SCHEMA_MANAGER,
        lookml_safe_join_map=LOOKML_SAFE_JOIN_MAP,
        sql_validation=req.sql_validation,
        # Pass extras your function supports:
        # agent_type=req.agent_type, user_context=req.user_context, excluded_tables=req.excluded_tables
    )
    if not result:
        raise HTTPException(status_code=500, detail="RAG generation failed")

    answer_text, docs, usage = result

    # Serialize sources (LangChain Document -> JSON-safe)
    sources = []
    for d in (docs or [])[:5]:  # cap for payload size
        content = getattr(d, "page_content", "")
        if len(content) > 2000:
            content = content[:2000] + "…"
        sources.append(SourceChunk(content=content, metadata=getattr(d, "metadata", {}) or {}))

    return AskResponse(answer=answer_text, sources=sources, usage=usage or {})

@app.post("/execute_sql", response_model=ExecResponse)
def execute_sql(req: ExecRequest):
    if not BIGQUERY_OK or BQ_EXECUTOR is None:
        raise HTTPException(status_code=501, detail="BigQuery execution not available on this server")

    try:
        res = BQ_EXECUTOR.execute_query(
            req.sql,
            dry_run=req.dry_run,
            max_bytes_billed=req.max_bytes_billed,
        )
        # Shape into API-friendly format
        out = ExecResponse(
            success=res.success,
            total_rows=getattr(res, "total_rows", 0),
            bytes_processed=getattr(res, "bytes_processed", 0),
            bytes_billed=getattr(res, "bytes_billed", 0),
            execution_time=getattr(res, "execution_time", 0.0),
            cache_hit=getattr(res, "cache_hit", False),
            job_id=getattr(res, "job_id", None),
            data=(None if (getattr(res, "dry_run", False) or res.data is None)
                  else res.data.to_dict(orient="records")),
            error_message=getattr(res, "error_message", None),
        )
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

How to run it
# add deps
pip install fastapi "uvicorn[standard]" pydantic

# run
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2

Why this works with your repo


You’re already separated into core modules (RAG engine, data loaders, schema manager, Gemini client). FastAPI can import those directly, no Streamlit dependency required. 


Startup eagerly warms the FAISS index + schema so requests are fast.


Endpoints cover the two main actions your UI does today: generate (/ask) and run SQL (/execute_sql).


You can deploy the API anywhere (Cloud Run, Railway, Fly.io, EC2). The Streamlit UI can call it—or you can build a React front end later. (Your setup guide steps still apply: env vars, embedding generation, etc. )


Small refactors you might need


Imports & PYTHONPATH: ensure uvicorn runs from project root so from simple_rag_simple_gemini import ... resolves.


Return shape: answer_question_simple_gemini already returns (answer, docs, usage); if your local signature differs, adapt the call.


Optional features: If you want agent_type, user_context, excluded_tables, or SQL validation toggles, add them to the answer_question_simple_gemini call (the placeholder in code shows where).


BigQuery: If you don’t need server-side execution, drop the /execute_sql route and keep compute on the client.


Coexist with Streamlit


Run them side by side:


streamlit run app_simple_gemini.py (GUI)


uvicorn api.main:app … (API)




Or migrate fully to React + FastAPI later; the API above is already React-friendly (CORS enabled).


If you want, I can tailor the /ask payload to exactly mirror your Streamlit options (e.g., Gemini mode switches, hybrid search weights, query rewriting on/off), but structurally this is all you need to get FastAPI deployment working with your current codebase.
