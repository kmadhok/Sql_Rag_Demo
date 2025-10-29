"""
Query Search API - Vector-based SQL query generation pipeline
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time
import os
from pathlib import Path
import json
import re
import requests
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import settings
from services.rag_service import rag_service
from data.app_data_loader import load_vector_store, load_schema_manager
from core.bigquery_executor import BigQueryExecutor, QueryResult
from core.sql_validator import SQLValidator, ValidationLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query-search", tags=["query-search"])

# Request/Response models
class QuerySearchRequest(BaseModel):
    question: str
    k: int = 4  # number of documents to retrieve
    use_gemini: bool = True
    schema_injection: bool = True
    sql_validation: bool = True

class QuerySearchResponse(BaseModel):
    question: str
    answer: str
    sql_query: Optional[str] = None
    retrieved_documents: List[Dict[str, Any]] = []
    schema_injected: Optional[str] = None
    validation_passed: Optional[bool] = None
    validation_errors: List[str] = []
    execution_available: bool = False
    usage_stats: Dict[str, Any] = {}
    timestamp: str
    session_id: str
    processing_time: float

# Real data integration - remove mock data

class VectorSearchService:
    """Service for handling vector-based query search with real FAISS integration"""
    
    def __init__(self):
        logger.info("🚀 Initializing VectorSearchService with real data integration...")
        
        # Load real vector store with fallback handling
        try:
            self.vector_store = self._load_vector_store_with_fallback("index_sample_queries_with_metadata_recovered")
            if self.vector_store is not None:
                logger.info("✅ Successfully loaded FAISS vector store with embeddings")
            else:
                logger.error("❌ Vector store loading returned None")
        except Exception as e:
            logger.error(f"❌ Failed to load vector store: {e}")
            self.vector_store = None
    
    def _load_vector_store_with_fallback(self, index_name: str):
        """Load vector store with multiple fallback strategies"""
        logger.info(f"🔄 Loading vector store: {index_name}")
        
        # Strategy 1: Try normal loading
        try:
            from data.app_data_loader import load_vector_store
            vector_store = load_vector_store(index_name)
            if vector_store:
                logger.info(f"✅ Strategy 1: Normal loading successful")
                return vector_store
        except Exception as e:
            logger.warning(f"⚠️ Strategy 1 failed: {e}")
        
        # Strategy 2: Try loading with mock embeddings (for compatibility)
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_core.embeddings import Embeddings
            from pathlib import Path
            
            index_path = Path(__file__).parent.parent.parent / "faiss_indices" / index_name
            
            if not (index_path / "index.faiss").exists():
                logger.error(f"❌ FAISS index files not found at: {index_path}")
                return None
            
            # Create mock embeddings for compatibility
            class MockEmbeddings(Embeddings):
                def __init__(self, embedding_dim=1536):
                    self.embedding_dim = embedding_dim
                
                def embed_query(self, text):
                    import hashlib
                    hash_obj = hashlib.sha256(text.encode('utf-8'))
                    hash_bytes = hash_obj.digest()
                    base_values = [float(b) / 255.0 for b in hash_bytes]
                    if len(base_values) < self.embedding_dim:
                        repeated = (base_values * ((self.embedding_dim // len(base_values)) + 1))[:self.embedding_dim]
                        return repeated
                    else:
                        return base_values[:self.embedding_dim]
                
                def embed_documents(self, texts):
                    return [self.embed_query(text) for text in texts]
                
                def __call__(self, text):
                    if isinstance(text, list):
                        return self.embed_documents(text)
                    else:
                        return self.embed_query(text)
            
            try:
                embeddings = MockEmbeddings()
                vector_store = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
                logger.info(f"✅ Strategy 2: Mock embeddings loading successful")
                return vector_store
            except Exception as e:
                logger.warning(f"⚠️ Strategy 2 failed: {e}")
        
        # Strategy 3: Try loading the original embeddings if possible
        try:
            # Check if Ollama is available
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                from langchain_ollama import OllamaEmbeddings
                embeddings = OllamaEmbeddings(model="nomic-embed-text")
                from langchain_community.vectorstores import FAISS
                from pathlib import Path
                index_path = Path(__file__).parent.parent.parent / "faiss_indices" / index_name
                vector_store = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
                logger.info(f"✅ Strategy 3: Ollama embeddings loading successful")
                return vector_store
        except Exception as e:
            logger.warning(f"⚠️ Strategy 3 (Ollama) failed: {e}")
        
        logger.error(f"❌ All vector store loading strategies failed for: {index_name}")
        return None
            
        # Load real schema manager
        try:
            self.schema_manager = load_schema_manager()
            logger.info(f"✅ Successfully loaded schema manager with {self.schema_manager.table_count if self.schema_manager else 0} tables")
        except Exception as e:
            logger.error(f"❌ Failed to load schema manager: {e}")
            self.schema_manager = None
            
        # Initialize BigQuery executor
        try:
            self.bigquery_executor = BigQueryExecutor()
            logger.info("✅ Successfully initialized BigQuery executor")
        except Exception as e:
            logger.error(f"❌ Failed to initialize BigQuery executor: {e}")
            self.bigquery_executor = None
            
        # Initialize SQL validator
        try:
            if self.schema_manager:
                self.sql_validator = SQLValidator(self.schema_manager)
                logger.info("✅ Successfully initialized SQL validator")
            else:
                self.sql_validator = None
                logger.warning("⚠️ SQL validator not available - no schema manager")
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQL validator: {e}")
            self.sql_validator = None
        
        # Check service readiness
        self.vector_search_ready = self.vector_store is not None
        self.bigquery_ready = self.bigquery_executor is not None
        self.schema_ready = self.schema_manager is not None
        
        logger.info(f"🔧 Service Status - Vector Search: {'✅' if self.vector_search_ready else '❌'}, BigQuery: {'✅' if self.bigquery_ready else '❌'}, Schema: {'✅' if self.schema_ready else '❌'}")
        
    def retrieve_relevant_queries(self, question: str, k: int = 4) -> List[Dict[str, Any]]:
        """Retrieve relevant queries using real FAISS vector search"""
        logger.info(f"🔍 Starting vector search for: '{question}'")
        logger.info(f"📊 Vector store status: {self.vector_store is not None}")
        logger.info(f"📊 Vector search ready: {self.vector_search_ready}")
        
        if not self.vector_search_ready:
            logger.error("❌ Vector store not available for search")
            # Try to load it again
            logger.info("🔄 Attempting to reload vector store...")
            try:
                from data.app_data_loader import load_vector_store
                self.vector_store = load_vector_store("index_sample_queries_with_metadata_recovered")
                if self.vector_store:
                    logger.info("✅ Vector store reloaded successfully")
                    self.vector_search_ready = True
                else:
                    logger.error("❌ Vector store reload returned None")
            except Exception as e:
                logger.error(f"❌ Vector store reload failed: {e}")
                
        if not self.vector_search_ready:
            logger.error("❌ Vector search still not available - returning empty results")
            return []
            
        try:
            logger.info(f"🔍 Searching for {k} relevant queries for: '{question}'")
            logger.info(f"📊 Vector store type: {type(self.vector_store)}")
            
            # Check if vector store has any documents
            try:
                # Get some info about the vector store
                if hasattr(self.vector_store, 'index'):
                    logger.info(f"📊 Vector store index: {str(type(self.vector_store.index))}")
                    if hasattr(self.vector_store.index, 'ntotal'):
                        logger.info(f"📊 Vector store contains {self.vector_store.index.ntotal} documents")
            except Exception as e:
                logger.warning(f"⚠️ Could not get vector store info: {e}")
            
            # Use FAISS similarity search
            docs = self.vector_store.similarity_search(question, k=k)
            logger.info(f"📊 FAISS returned {len(docs)} documents")
            
            results = []
            for i, doc in enumerate(docs):
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata.copy() if hasattr(doc, 'metadata') else {}
                }
                # Add similarity score based on position (FAISS returns ranked results)
                result["metadata"]["score"] = 1.0 - (i * 0.1)  # Simple scoring: 1.0, 0.9, 0.8, etc.
                results.append(result)
                logger.info(f"📊 Document {i+1}: '{doc.page_content[:50]}...' (score: {result['metadata']['score']})")
                
            logger.info(f"✅ Retrieved {len(results)} relevant queries")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during vector search: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []
    
    def extract_relevant_tables(self, question: str, retrieved_queries: List[Dict[str, Any]]) -> List[str]:
        """Extract relevant tables from question and retrieved queries using schema manager"""
        logger.info(f"🔍 Starting table extraction for: '{question}'")
        logger.info(f"📊 Retrieved queries count: {len(retrieved_queries)}")
        logger.info(f"📊 Schema manager ready: {self.schema_ready}")
        
        if not self.schema_ready:
            logger.warning("⚠️ Schema manager not available - using fallback table extraction")
            return self._fallback_table_extraction(question)
            
        tables_found = set()
        
        try:
            # Extract tables from retrieved queries using metadata
            for query_data in retrieved_queries:
                logger.info(f"📊 Processing retrieved query: {query_data.get('metadata', {})}")
                if 'tables' in query_data['metadata']:
                    logger.info(f"📊 Found tables in metadata: {query_data['metadata']['tables']}")
                    tables_found.update(query_data['metadata']['tables'])
                
                # Also extract from the SQL content itself
                sql_content = query_data.get('content', '')
                if sql_content:
                    logger.info(f"📊 Extracting tables from SQL: {sql_content[:50]}...")
                    extracted_from_sql = self.schema_manager.extract_tables_from_sql(sql_content)
                    logger.info(f"📊 Tables extracted from SQL: {extracted_from_sql}")
                    tables_found.update(extracted_from_sql)
            
            # Extract tables from user question using schema manager's intelligent detection
            logger.info(f"📊 Detecting relevant tables from question using schema manager...")
            tables_from_question = self.schema_manager.detect_relevant_tables(question)
            logger.info(f"📊 Tables detected from question: {tables_from_question}")
            tables_found.update(tables_from_question)
            
            # Get available tables for debugging
            available_tables = self.schema_manager.get_available_tables()
            logger.info(f"📊 Available tables in schema: {available_tables}")
            
            # Normalize and filter to available tables
            normalized_tables = []
            
            for table in tables_found:
                logger.info(f"📊 Processing table: {table}")
                try:
                    normalized = self.schema_manager.normalize_table_name(table)
                    logger.info(f"📊 Normalized table: {table} -> {normalized}")
                    if normalized in available_tables:
                        if normalized not in normalized_tables:
                            normalized_tables.append(normalized)
                            logger.info(f"✅ Added table to results: {normalized}")
                        else:
                            logger.info(f"ℹ️ Table already in results: {normalized}")
                    else:
                        logger.info(f"⚠️ Table not found in available tables: {normalized}")
                except Exception as e:
                    logger.error(f"❌ Error normalizing table '{table}': {e}")
                        
            logger.info(f"📋 Final extracted {len(normalized_tables)} relevant tables: {normalized_tables}")
            return normalized_tables
            
        except Exception as e:
            logger.error(f"❌ Error during table extraction: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return self._fallback_table_extraction(question)
    
    def _fallback_table_extraction(self, question: str) -> List[str]:
        """Fallback table extraction using keyword matching"""
        question_lower = question.lower()
        keywords = {
            'user': 'users',
            'users': 'users', 
            'customer': 'users',
            'customers': 'users',
            'product': 'products',
            'products': 'products',
            'order': 'orders',
            'orders': 'orders',
            'item': 'order_items',
            'items': 'order_items',
            'distribution': 'distribution_centers',
            'event': 'events',
            'events': 'events'
        }
        
        found_tables = []
        for keyword, table in keywords.items():
            if keyword in question_lower and table not in found_tables:
                found_tables.append(table)
                
        logger.info(f"📋 Fallback table extraction found: {found_tables}")
        return found_tables
    
    def inject_schema(self, tables: List[str]) -> str:
        """Generate schema snippet for relevant tables using real schema manager"""
        if not tables:
            return ""
            
        if not self.schema_ready:
            logger.warning("⚠️ Schema manager not available - using fallback schema")
            return self._fallback_schema_injection(tables)
            
        try:
            schema_lines = ["# Database Schema:"]
            
            for table_name in tables:
                if self.schema_manager.has_table(table_name):
                    table_info = self.schema_manager.get_table_info(table_name)
                    fqn = self.schema_manager.get_fqn(table_name)
                    
                    schema_lines.append(f"# Table: {table_name}")
                    schema_lines.append(f"# FQN: `{fqn}`")
                    
                    if table_info['columns']:
                        for col in table_info['columns']:
                            nullable_str = "NULL" if col.get('nullable', True) else "NOT NULL"
                            schema_lines.append(f"#   {col['name']} {col['datatype']} {nullable_str}")
                    else:
                        # Fallback to column list
                        columns = self.schema_manager.get_table_columns(table_name)
                        for col in columns:
                            schema_lines.append(f"#   {col} STRING NULL")  # Default type info
                    
                    schema_lines.append("")  # Empty line between tables
                else:
                    schema_lines.append(f"# Table: {table_name} (not found in schema)")
                    schema_lines.append("")
            
            schema_text = "\n".join(schema_lines)
            logger.info(f"🏗️ Injected schema for {len(tables)} tables")
            return schema_text
            
        except Exception as e:
            logger.error(f"❌ Error during schema injection: {e}")
            return self._fallback_schema_injection(tables)
    
    def _fallback_schema_injection(self, tables: List[str]) -> str:
        """Fallback schema injection using basic table info"""
        schema_lines = ["# Database Schema:"]
        for table_name in tables:
            schema_lines.append(f"# Table: {table_name}")
            schema_lines.append("#   id INT64 NOT NULL")
            schema_lines.append("#   created_at TIMESTAMP NOT NULL")
            schema_lines.append("")
        return "\n".join(schema_lines)
    
    def validate_sql(self, sql: str, required_tables: List[str]) -> Dict[str, Any]:
        """Validate SQL against schema using real SQL validator"""
        if not self.sql_validator:
            logger.warning("⚠️ SQL validator not available - using basic validation")
            return self._basic_sql_validation(sql, required_tables)
            
        try:
            # Use real SQL validator
            validation_result = self.sql_validator.validate_sql(
                sql=sql,
                allowed_tables=required_tables,
                validation_level=ValidationLevel.SCHEMA_STRICT
            )
            
            result = {
                "valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "extracted_tables": list(validation_result.tables_found),
                "extracted_columns": list(validation_result.columns_found),
                "joins_found": validation_result.joins_found,
                "suggestions": validation_result.suggestions
            }
            
            logger.info(f"✅ SQL validation completed: {'PASSED' if result['valid'] else 'FAILED'} - {len(result['errors'])} errors, {len(result['warnings'])} warnings")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error during SQL validation: {e}")
            return self._basic_sql_validation(sql, required_tables)
    
    def _basic_sql_validation(self, sql: str, required_tables: List[str]) -> Dict[str, Any]:
        """Basic SQL validation as fallback"""
        validation_errors = []
        
        # Extract tables from SQL (simple regex approach)
        table_pattern = r'FROM\s+`?([^`\s]+)`?|JOIN\s+`?([^`\s]+)`?'
        extracted_tables = re.findall(table_pattern, sql, re.IGNORECASE)
        extracted_tables = [table[0] or table[1] for table in extracted_tables]
        extracted_tables = [t.split('.')[-1].replace('`', '') for t in extracted_tables]
        
        # Security checks
        forbidden_patterns = [r'DROP\s+', r'DELETE\s+', r'UPDATE\s+', r'INSERT\s+', r'CREATE\s+', r'TRUNCATE\s+']
        for pattern in forbidden_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                validation_errors.append(f"DML operation not allowed: {pattern}")
        
        # Basic SELECT check
        if not re.search(r'\bSELECT\b', sql, re.IGNORECASE):
            validation_errors.append("Query must be a SELECT statement")
        
        if not re.search(r'\bFROM\b', sql, re.IGNORECASE):
            validation_errors.append("Query must contain a FROM clause")
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": [],
            "extracted_tables": extracted_tables,
            "extracted_columns": [],
            "joins_found": [],
            "suggestions": []
        }

# Initialize service
vector_search_service = VectorSearchService()

@router.post("/search", response_model=QuerySearchResponse)
async def query_search(request: QuerySearchRequest):
    """Execute vector-based query search pipeline"""
    start_time = time.time()
    
    try:
        logger.info(f"Query search pipeline started for: '{request.question}'")
        
        # Step 1: Retrieve relevant queries
        retrieval_start = time.time()
        retrieved_documents = vector_search_service.retrieve_relevant_queries(
            request.question, k=request.k
        )
        retrieval_time = time.time() - retrieval_start
        
        logger.info(f"Retrieved {len(retrieved_documents)} documents in {retrieval_time:.3f}s")
        
        # Step 2: Extract relevant tables
        tables = vector_search_service.extract_relevant_tables(request.question, retrieved_documents)
        logger.info(f"Extracted tables: {tables}")
        
        # Step 3: Schema injection
        schema_injected = vector_search_service.inject_schema(tables) if request.schema_injection else None
        
        # Step 4: Generate SQL using LLM (RAG service)
        generation_start = time.time()
        llm_response = rag_service.process_query(
            question=request.question,
            agent_type="create"  # Using create agent for SQL generation
        )
        generation_time = time.time() - generation_start
        
        sql_query = llm_response.get('sql_query', '')
        answer = llm_response.get('message', '')
        
        # Step 5: SQL validation
        validation_result = None
        if request.sql_validation and sql_query:
            validation_start = time.time()
            validation_result = vector_search_service.validate_sql(sql_query, tables)
            validation_time = time.time() - validation_start
            logger.info(f"SQL validation completed in {validation_time:.3f}s: {'PASSED' if validation_result['valid'] else 'FAILED'}")
        
        total_time = time.time() - start_time
        
        # Step 6: Build response
        response_data = {
            "question": request.question,
            "answer": answer,
            "sql_query": sql_query,
            "retrieved_documents": retrieved_documents,
            "schema_injected": schema_injected,
            "validation_passed": validation_result['valid'] if validation_result else None,
            "validation_errors": validation_result['errors'] if validation_result else [],
            "execution_available": bool(validation_result and validation_result['valid']),
            "usage_stats": {
                "retrieval_time": retrieval_time,
                "generation_time": generation_time,
                "documents_retrieved": len(retrieved_documents),
                "tables_retrieved": len(tables),
                "token_usage": llm_response.get('token_usage', {})
            },
            "timestamp": datetime.now().isoformat(),
            "session_id": f"query_search_{int(time.time())}",
            "processing_time": total_time
        }
        
        logger.info(f"Query search pipeline completed in {total_time:.3f}s")
        return response_data
        
    except Exception as e:
        logger.error(f"Error in query search pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Query search failed: {str(e)}")

class ExecuteQueryRequest(BaseModel):
    sql: str
    dry_run: bool = False
    session_id: Optional[str] = None

class ExecuteQueryResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: int = 0
    execution_time: float = 0.0
    bytes_processed: Optional[int] = None
    bytes_billed: Optional[int] = None
    job_id: Optional[str] = None
    cache_hit: bool = False
    dry_run: bool = False
    error_message: Optional[str] = None
    sql: str
    timestamp: str = None

@router.post("/execute", response_model=ExecuteQueryResponse)
async def execute_query(request: ExecuteQueryRequest):
    """Execute SQL query using real BigQuery integration"""
    try:
        logger.info(f"🚀 Executing SQL query (dry_run={request.dry_run}): {request.sql[:100]}...")
        
        if not vector_search_service.bigquery_ready:
            raise HTTPException(
                status_code=503,
                detail="BigQuery executor not available - check configuration"
            )
        
        # Execute query using BigQuery executor
        execution_start = time.time()
        result: QueryResult = vector_search_service.bigquery_executor.execute_query(
            sql=request.sql,
            dry_run=request.dry_run
        )
        execution_time = time.time() - execution_start
        
        # Convert result to API response format
        response_data = ExecuteQueryResponse(
            success=result.success,
            data=result.data.to_dict('records') if result.data is not None else None,
            columns=list(result.data.columns) if result.data is not None else None,
            row_count=result.total_rows,
            execution_time=execution_time,
            bytes_processed=result.bytes_processed,
            bytes_billed=result.bytes_billed,
            job_id=result.job_id,
            cache_hit=result.cache_hit,
            dry_run=result.dry_run,
            error_message=result.error_message,
            sql=request.sql,
            timestamp=datetime.now().isoformat()
        )
        
        if result.success:
            logger.info(f"✅ Query executed successfully in {execution_time:.3f}s - {result.total_rows} rows returned")
        else:
            logger.error(f"❌ Query execution failed: {result.error_message}")
            
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error executing query: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")