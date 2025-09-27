#!/usr/bin/env python3
"""
Hybrid Retriever for SQL RAG System

Combines vector similarity search with keyword-based BM25 search using Reciprocal Rank Fusion (RRF).
Optimized for SQL queries with enhanced handling of table names, SQL functions, and technical terminology.

Features:
- BM25 keyword search for exact matching
- Vector search for semantic similarity
- Reciprocal Rank Fusion (RRF) for combining results
- SQL-aware query preprocessing
- Configurable search weights
- Compatible with existing Gemini optimizations
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class HybridSearchResult:
    """Result from hybrid search with scoring details"""
    document: Document
    vector_score: float
    keyword_score: float
    fusion_score: float
    rank_vector: int
    rank_keyword: int
    search_method: str  # 'vector', 'keyword', or 'hybrid'

@dataclass
class SearchWeights:
    """Search method weights for fusion"""
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    
    def __post_init__(self):
        # Normalize weights to sum to 1.0
        total = self.vector_weight + self.keyword_weight
        if total > 0:
            self.vector_weight /= total
            self.keyword_weight /= total

class SQLQueryAnalyzer:
    """Analyzes SQL queries to optimize search strategy"""
    
    # SQL keywords that benefit from exact matching
    SQL_KEYWORDS = {
        'functions': ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'GROUP BY', 'ORDER BY', 'HAVING'],
        'joins': ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN'],
        'clauses': ['WHERE', 'SELECT', 'FROM', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER'],
        'operators': ['AND', 'OR', 'NOT', 'IN', 'EXISTS', 'LIKE', 'BETWEEN']
    }
    
    @classmethod
    def analyze_query_type(cls, query: str) -> Dict[str, Any]:
        """Analyze query to determine optimal search strategy"""
        query_upper = query.upper()
        
        analysis = {
            'has_table_names': cls._detect_table_names(query),
            'has_sql_functions': any(func in query_upper for func in cls.SQL_KEYWORDS['functions']),
            'has_joins': any(join in query_upper for join in cls.SQL_KEYWORDS['joins']),
            'has_technical_terms': cls._count_technical_terms(query_upper),
            'is_schema_query': cls._is_schema_query(query),
            'recommended_weights': cls._recommend_weights(query_upper)
        }
        
        return analysis
    
    @classmethod
    def _detect_table_names(cls, query: str) -> bool:
        """Detect if query contains potential table names"""
        # Look for patterns like "table_name", "TableName", or common SQL table patterns
        table_patterns = [
            r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*\.',  # table.column pattern
            r'\bFROM\s+[a-zA-Z_][a-zA-Z0-9_]*\b',  # FROM table pattern
            r'\bJOIN\s+[a-zA-Z_][a-zA-Z0-9_]*\b',  # JOIN table pattern
        ]
        
        for pattern in table_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _count_technical_terms(cls, query_upper: str) -> int:
        """Count SQL technical terms in query"""
        count = 0
        for category in cls.SQL_KEYWORDS.values():
            for term in category:
                count += query_upper.count(term)
        return count
    
    @classmethod
    def _is_schema_query(cls, query: str) -> bool:
        """Detect if query is asking about database schema"""
        schema_terms = ['schema', 'table', 'column', 'structure', 'database', 'relationship']
        query_lower = query.lower()
        return any(term in query_lower for term in schema_terms)
    
    @classmethod
    def _recommend_weights(cls, query_upper: str) -> SearchWeights:
        """Recommend optimal search weights based on query analysis"""
        # Base weights favor vector search for semantic understanding
        vector_weight = 0.7
        keyword_weight = 0.3
        
        # Increase keyword weight for technical queries
        technical_score = cls._count_technical_terms(query_upper)
        if technical_score > 3:
            keyword_weight = 0.5  # High technical content
            vector_weight = 0.5
        elif technical_score > 1:
            keyword_weight = 0.4  # Moderate technical content
            vector_weight = 0.6
        
        # Increase keyword weight for schema queries
        schema_indicators = ['TABLE', 'COLUMN', 'SCHEMA', 'STRUCTURE']
        if any(indicator in query_upper for indicator in schema_indicators):
            keyword_weight = min(keyword_weight + 0.2, 0.6)
            vector_weight = 1.0 - keyword_weight
        
        return SearchWeights(vector_weight=vector_weight, keyword_weight=keyword_weight)

class HybridRetriever:
    """Hybrid retriever combining vector and keyword search"""
    
    def __init__(self, vector_store: FAISS, documents: List[Document]):
        """
        Initialize hybrid retriever
        
        Args:
            vector_store: Pre-built FAISS vector store
            documents: List of documents for BM25 indexing
        """
        self.vector_store = vector_store
        self.documents = documents
        
        # Build BM25 index
        logger.info(f"Building BM25 index for {len(documents)} documents...")
        self._build_bm25_index()
        
        # Initialize query analyzer
        self.query_analyzer = SQLQueryAnalyzer()
    
    def _build_bm25_index(self):
        """Build BM25 index from documents"""
        try:
            # Preprocess documents for BM25
            corpus = []
            for doc in self.documents:
                # Combine content and metadata for comprehensive search
                searchable_text = doc.page_content
                
                # Add metadata terms for enhanced matching
                if hasattr(doc, 'metadata') and doc.metadata:
                    if doc.metadata.get('description'):
                        searchable_text += " " + doc.metadata['description']
                    if doc.metadata.get('table'):
                        searchable_text += " " + doc.metadata['table']
                    if doc.metadata.get('tables'):
                        searchable_text += " " + doc.metadata['tables']
                
                # Tokenize with SQL-aware preprocessing
                tokens = self._preprocess_for_bm25(searchable_text)
                corpus.append(tokens)
            
            # Build BM25 index
            self.bm25 = BM25Okapi(corpus)
            logger.info(f"✅ BM25 index built successfully with {len(corpus)} documents")
            
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            raise
    
    def _preprocess_for_bm25(self, text: str) -> List[str]:
        """Preprocess text for BM25 with SQL-aware tokenization"""
        # Convert to lowercase for consistency
        text = text.lower()
        
        # Preserve SQL keywords and identifiers
        # Split on whitespace and common SQL delimiters
        tokens = re.findall(r'\b\w+\b|[().,;]', text)
        
        # Filter out very short tokens but keep SQL keywords
        sql_keywords = {kw.lower() for category in SQLQueryAnalyzer.SQL_KEYWORDS.values() for kw in category}
        filtered_tokens = []
        
        for token in tokens:
            if len(token) >= 2 or token in sql_keywords:
                filtered_tokens.append(token)
        
        return filtered_tokens
    
    def _keyword_search(self, query: str, k: int) -> List[Tuple[Document, float, int]]:
        """Perform BM25 keyword search"""
        try:
            # Preprocess query
            query_tokens = self._preprocess_for_bm25(query)
            
            # Get BM25 scores
            scores = self.bm25.get_scores(query_tokens)
            
            # Get top-k results with scores and ranks
            doc_scores = [(i, score) for i, score in enumerate(scores)]
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for rank, (doc_idx, score) in enumerate(doc_scores[:k]):
                if doc_idx < len(self.documents):
                    results.append((self.documents[doc_idx], score, rank + 1))
            
            logger.debug(f"BM25 search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _vector_search(self, query: str, k: int) -> List[Tuple[Document, float, int]]:
        """Perform vector similarity search"""
        try:
            # Use existing FAISS vector store
            docs_with_scores = self.vector_store.similarity_search_with_score(query, k=k)
            
            # Convert to consistent format with ranks
            results = []
            for rank, (doc, score) in enumerate(docs_with_scores):
                results.append((doc, score, rank + 1))
            
            logger.debug(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _reciprocal_rank_fusion(self, 
                               vector_results: List[Tuple[Document, float, int]], 
                               keyword_results: List[Tuple[Document, float, int]], 
                               weights: SearchWeights,
                               k: int = 60) -> List[HybridSearchResult]:
        """
        Combine results using Reciprocal Rank Fusion (RRF)
        
        Args:
            vector_results: Vector search results with (doc, score, rank)
            keyword_results: Keyword search results with (doc, score, rank)
            weights: Search method weights
            k: RRF constant (default 60 as per literature)
        """
        # Create document ID mapping
        def doc_id(doc):
            return f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk', '')}"
        
        # Build result maps
        vector_map = {doc_id(doc): (doc, score, rank) for doc, score, rank in vector_results}
        keyword_map = {doc_id(doc): (doc, score, rank) for doc, score, rank in keyword_results}
        
        # Get all unique documents
        all_doc_ids = set(vector_map.keys()) | set(keyword_map.keys())
        
        fusion_results = []
        
        for doc_key in all_doc_ids:
            # Get scores and ranks (default to last rank + 1 if not found)
            vector_data = vector_map.get(doc_key)
            keyword_data = keyword_map.get(doc_key)
            
            if vector_data:
                doc, vector_score, vector_rank = vector_data
            else:
                doc = keyword_data[0]  # Get document from keyword results
                vector_score = 0.0
                vector_rank = len(vector_results) + 1
            
            if keyword_data:
                if not vector_data:  # Only get doc if not already from vector
                    doc = keyword_data[0]
                keyword_score = keyword_data[1]
                keyword_rank = keyword_data[2]
            else:
                keyword_score = 0.0
                keyword_rank = len(keyword_results) + 1
            
            # Calculate RRF score
            rrf_vector = 1.0 / (k + vector_rank)
            rrf_keyword = 1.0 / (k + keyword_rank)
            
            # Apply weights
            fusion_score = (weights.vector_weight * rrf_vector + 
                           weights.keyword_weight * rrf_keyword)
            
            # Determine search method
            if vector_data and keyword_data:
                search_method = 'hybrid'
            elif vector_data:
                search_method = 'vector'
            else:
                search_method = 'keyword'
            
            fusion_results.append(HybridSearchResult(
                document=doc,
                vector_score=vector_score,
                keyword_score=keyword_score,
                fusion_score=fusion_score,
                rank_vector=vector_rank,
                rank_keyword=keyword_rank,
                search_method=search_method
            ))
        
        # Sort by fusion score
        fusion_results.sort(key=lambda x: x.fusion_score, reverse=True)
        
        return fusion_results
    
    def hybrid_search(self, 
                     query: str, 
                     k: int = 4, 
                     weights: Optional[SearchWeights] = None,
                     auto_adjust_weights: bool = True) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining vector and keyword methods
        
        Args:
            query: Search query
            k: Number of results to return
            weights: Search method weights (if None, will use defaults or auto-adjust)
            auto_adjust_weights: Whether to automatically adjust weights based on query analysis
            
        Returns:
            List of HybridSearchResult objects sorted by fusion score
        """
        logger.info(f"Performing hybrid search for: '{query[:50]}...'")
        
        # Analyze query if auto-adjustment is enabled
        if auto_adjust_weights:
            analysis = self.query_analyzer.analyze_query_type(query)
            weights = analysis['recommended_weights']
            logger.info(f"Auto-adjusted weights: vector={weights.vector_weight:.2f}, keyword={weights.keyword_weight:.2f}")
        elif weights is None:
            weights = SearchWeights()  # Use defaults
        
        # Perform both searches with expanded k for better fusion
        search_k = max(k * 2, 10)  # Search more documents for better fusion
        
        # Vector search
        logger.debug("Performing vector search...")
        vector_results = self._vector_search(query, search_k)
        
        # Keyword search
        logger.debug("Performing keyword search...")
        keyword_results = self._keyword_search(query, search_k)
        
        # Combine using RRF
        logger.debug("Applying Reciprocal Rank Fusion...")
        fusion_results = self._reciprocal_rank_fusion(
            vector_results, keyword_results, weights
        )
        
        # Return top-k results
        final_results = fusion_results[:k]
        
        logger.info(f"Hybrid search completed: {len(final_results)} results")
        logger.info(f"Search method breakdown: "
                   f"hybrid={sum(1 for r in final_results if r.search_method == 'hybrid')}, "
                   f"vector={sum(1 for r in final_results if r.search_method == 'vector')}, "
                   f"keyword={sum(1 for r in final_results if r.search_method == 'keyword')}")
        
        return final_results
    
    def search(self, 
               query: str, 
               k: int = 4, 
               method: str = 'hybrid',
               **kwargs) -> List[Document]:
        """
        Convenience method that returns documents (compatible with existing code)
        
        Args:
            query: Search query
            k: Number of results
            method: 'hybrid', 'vector', or 'keyword'
            **kwargs: Additional arguments for hybrid_search
            
        Returns:
            List of Document objects
        """
        if method == 'vector':
            results = self._vector_search(query, k)
            return [doc for doc, score, rank in results]
        elif method == 'keyword':
            results = self._keyword_search(query, k)
            return [doc for doc, score, rank in results]
        else:  # hybrid
            results = self.hybrid_search(query, k, **kwargs)
            return [result.document for result in results]