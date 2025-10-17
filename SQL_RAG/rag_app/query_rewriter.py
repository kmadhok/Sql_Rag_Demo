#!/usr/bin/env python3
"""
Query Rewriting Module for SQL RAG System

Enhances user queries with SQL-specific terminology expansion, synonym handling,
and concept clarification to improve document retrieval precision.

Features:
- SQL terminology expansion and standardization
- Synonym handling for SQL concepts
- Query confidence scoring
- Caching for common query patterns
- Fallback mechanisms for reliability
"""

import time
import logging
import json
import hashlib
import os
from typing import Dict, Optional, Tuple, Any, List
from pathlib import Path

# Google Gemini imports
try:
    from google import genai
except ImportError:
    print("❌ Error: google-generativeai is required. Install with: pip install google-generativeai")
    genai = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_GEMINI_MODEL = os.getenv("LLM_REWRITE_MODEL", os.getenv("LLM_PARSE_MODEL", "gemini-2.5-flash-lite"))
GEMINI_PRO_MODEL = "gemini-2.5-pro" 
GEMINI_LITE_MODEL = "gemini-2.5-flash-lite"
CACHE_DIR = Path(__file__).parent / "query_rewrite_cache"
CACHE_EXPIRY_DAYS = 7
MIN_CONFIDENCE_THRESHOLD = 0.6

# SQL domain knowledge patterns
SQL_TERM_EXPANSIONS = {
    "join": ["inner join", "left join", "right join", "full outer join", "cross join", "natural join"],
    "agg": ["aggregation", "group by", "sum", "count", "avg", "max", "min", "having"],
    "performance": ["query optimization", "indexing", "execution time", "query plan", "statistics"],
    "inventory": ["stock", "warehouse", "supply chain", "turnover", "rotation"],
    "customer": ["client", "user", "account", "buyer", "consumer"],
    "revenue": ["sales", "income", "earnings", "profit", "financial"],
    "analysis": ["analytics", "reporting", "metrics", "insights", "dashboard"]
}

SQL_SYNONYMS = {
    "table": ["relation", "entity", "dataset"],
    "column": ["field", "attribute", "property"],
    "query": ["statement", "sql", "command"],
    "database": ["db", "schema", "data store"],
    "function": ["procedure", "method", "operation"]
}


class QueryRewriter:
    """Enhanced query rewriter for SQL domain with caching and confidence scoring"""
    
    def __init__(self, model: str = DEFAULT_GEMINI_MODEL, enable_cache: bool = True, project: str = None):
        """
        Initialize the query rewriter
        
        Args:
            model: Gemini model to use for rewriting (e.g., 'gemini-2.5-flash', 'gemini-2.5-pro')
            enable_cache: Whether to enable query rewrite caching
            project: Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        """
        self.model = model
        self.enable_cache = enable_cache
        self.project = project or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.client = None
        
        # Initialize cache directory
        if self.enable_cache:
            CACHE_DIR.mkdir(exist_ok=True)
            self._cleanup_expired_cache()
    
    def _get_genai_client(self):
        """Lazy initialization of Gemini client following generate_descriptions.py pattern"""
        if self.client is None:
            if genai is None:
                raise ImportError("google-generativeai is required. Install with: pip install google-generativeai")
            
            try:
                self.client = genai.Client(
                    vertexai=True, 
                    project=self.project,
                    location="global"  # Default location for Vertex AI
                )
                logger.debug(f"Initialized Gemini client with project: {self.project}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise
        
        return self.client
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for key"""
        return CACHE_DIR / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cached result is still valid"""
        if not cache_path.exists():
            return False
        
        try:
            # Check file age
            file_age_days = (time.time() - cache_path.stat().st_mtime) / (24 * 3600)
            return file_age_days < CACHE_EXPIRY_DAYS
        except Exception:
            return False
    
    def _cleanup_expired_cache(self):
        """Remove expired cache files"""
        try:
            if not CACHE_DIR.exists():
                return
            
            expired_count = 0
            for cache_file in CACHE_DIR.glob("*.json"):
                if not self._is_cache_valid(cache_file):
                    cache_file.unlink()
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired cache files")
                
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load rewritten query from cache"""
        if not self.enable_cache:
            return None
        
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached_data = json.load(f)
            
            logger.debug(f"Cache hit for query rewrite: {cache_key[:8]}...")
            return cached_data
            
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, rewrite_data: Dict[str, Any]):
        """Save rewritten query to cache"""
        if not self.enable_cache:
            return
        
        try:
            cache_path = self._get_cache_path(cache_key)
            
            # Add cache metadata
            cache_entry = {
                **rewrite_data,
                'cached_at': time.time(),
                'cache_key': cache_key
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f, indent=2)
            
            logger.debug(f"Cached query rewrite: {cache_key[:8]}...")
            
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
    
    def _expand_sql_terms(self, query: str) -> str:
        """Expand SQL terminology and add synonyms"""
        expanded_terms = []
        query_lower = query.lower()
        
        # Add original query
        expanded_terms.append(query)
        
        # Check for term expansions
        for term, expansions in SQL_TERM_EXPANSIONS.items():
            if term in query_lower:
                expanded_terms.extend(expansions)
        
        # Check for synonyms
        for term, synonyms in SQL_SYNONYMS.items():
            if term in query_lower:
                expanded_terms.extend(synonyms)
        
        # Remove duplicates and join
        unique_terms = list(set(expanded_terms))
        return " ".join(unique_terms)
    
    def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query intent and suggest focus areas"""
        intent_analysis = {
            'has_sql_terms': False,
            'focus_areas': [],
            'complexity': 'simple',
            'suggested_expansions': []
        }
        
        query_lower = query.lower()
        
        # Check for SQL terms
        sql_keywords = ['join', 'select', 'where', 'group by', 'having', 'order by', 'table', 'database']
        intent_analysis['has_sql_terms'] = any(keyword in query_lower for keyword in sql_keywords)
        
        # Identify focus areas
        if any(term in query_lower for term in ['join', 'relationship', 'connect']):
            intent_analysis['focus_areas'].append('joins_and_relationships')
        
        if any(term in query_lower for term in ['aggregate', 'sum', 'count', 'group', 'total']):
            intent_analysis['focus_areas'].append('aggregations')
        
        if any(term in query_lower for term in ['performance', 'optimize', 'fast', 'slow']):
            intent_analysis['focus_areas'].append('performance')
        
        if any(term in query_lower for term in ['customer', 'user', 'client']):
            intent_analysis['focus_areas'].append('customer_analysis')
        
        # Determine complexity
        if len(intent_analysis['focus_areas']) > 2 or len(query.split()) > 10:
            intent_analysis['complexity'] = 'complex'
        elif len(intent_analysis['focus_areas']) > 0:
            intent_analysis['complexity'] = 'moderate'
        
        return intent_analysis
    
    def _build_rewrite_prompt(self, query: str, intent_analysis: Dict[str, Any]) -> str:
        """Build prompt for LLM-based query rewriting"""
        
        prompt = f"""You are a SQL query rewriting expert. Your task is to enhance the user's query to improve document retrieval in a SQL code database.

Original Query: "{query}"

Intent Analysis:
- Has SQL terms: {intent_analysis['has_sql_terms']}
- Focus areas: {', '.join(intent_analysis['focus_areas']) if intent_analysis['focus_areas'] else 'general'}
- Complexity: {intent_analysis['complexity']}

Instructions:
1. Enhance the query with relevant SQL terminology and synonyms
2. Add related concepts that would help find relevant SQL examples
3. Keep the original intent but expand with technical terms
4. Focus on SQL patterns, table relationships, and query techniques
5. Make it more specific to database and SQL contexts

Enhanced Query Guidelines:
- Include both technical SQL terms and business concepts
- Add synonyms for key terms (e.g., "join" → "inner join, left join, relationship")
- Expand domain terms (e.g., "customer" → "customer, client, user analysis")
- Add related SQL concepts that would be in relevant code examples

Provide ONLY the enhanced query, no explanations:"""

        return prompt
    
    def _evaluate_rewrite_confidence(self, original: str, rewritten: str) -> float:
        """Evaluate confidence in the rewritten query"""
        
        # Basic checks
        if not rewritten or rewritten.strip() == original.strip():
            return 0.0
        
        confidence_score = 0.5  # Base score
        
        # Check if rewritten query is longer (usually good)
        if len(rewritten) > len(original):
            confidence_score += 0.2
        
        # Check if SQL terms were added
        sql_terms = ['join', 'select', 'table', 'query', 'database', 'aggregation', 'group by']
        original_sql_count = sum(1 for term in sql_terms if term in original.lower())
        rewritten_sql_count = sum(1 for term in sql_terms if term in rewritten.lower())
        
        if rewritten_sql_count > original_sql_count:
            confidence_score += 0.2
        
        # Check for reasonable length (not too long)
        if len(rewritten.split()) <= len(original.split()) * 3:
            confidence_score += 0.1
        else:
            confidence_score -= 0.2  # Penalize overly long rewrites
        
        # Ensure original meaning is preserved (basic keyword overlap)
        original_words = set(original.lower().split())
        rewritten_words = set(rewritten.lower().split())
        overlap = len(original_words.intersection(rewritten_words)) / len(original_words)
        
        if overlap >= 0.5:  # At least 50% word overlap
            confidence_score += 0.1
        else:
            confidence_score -= 0.3  # Penalize if meaning might be lost
        
        return min(max(confidence_score, 0.0), 1.0)
    
    def _get_optimal_model(self, query: str, intent_analysis: Dict[str, Any]) -> str:
        """Get optimal Gemini model based on query complexity"""
        return select_optimal_gemini_model(query, intent_analysis)
    
    def rewrite_query(self, query: str, use_fallback: bool = True, auto_select_model: bool = False) -> Dict[str, Any]:
        """
        Rewrite query for improved SQL document retrieval using Gemini models
        
        Args:
            query: Original user query
            use_fallback: Whether to use fallback methods if Gemini fails
            auto_select_model: Whether to automatically select optimal Gemini model based on complexity
            
        Returns:
            Dictionary containing rewrite results and metadata
        """
        
        start_time = time.time()
        cache_key = self._get_cache_key(query)
        
        # Try cache first
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            logger.info(f"Query rewrite cache hit: {cached_result['rewrite_time']:.3f}s")
            return cached_result
        
        try:
            # Analyze query intent
            intent_analysis = self._analyze_query_intent(query)
            
            # Select optimal model if auto-selection is enabled
            model_to_use = self.model
            if auto_select_model:
                model_to_use = self._get_optimal_model(query, intent_analysis)
                logger.info(f"Auto-selected model: {model_to_use} for query complexity: {intent_analysis.get('complexity', 'simple')}")
            
            # Try Gemini-based rewriting
            rewritten_query = None
            llm_error = None
            
            try:
                client = self._get_genai_client()
                prompt = self._build_rewrite_prompt(query, intent_analysis)
                
                llm_start = time.time()
                response = client.models.generate_content(
                    model=model_to_use,
                    contents=prompt
                )
                llm_time = time.time() - llm_start
                
                if response and hasattr(response, 'text') and response.text.strip():
                    rewritten_query = response.text.strip()
                    logger.info(f"Gemini rewrite completed in {llm_time:.3f}s")
                else:
                    llm_error = "Empty response from Gemini"
                    
            except Exception as e:
                llm_error = str(e)
                logger.warning(f"Gemini rewriting failed: {llm_error}")
            
            # Use fallback if Gemini failed and fallback is enabled
            if not rewritten_query and use_fallback:
                logger.info("Using fallback term expansion method")
                rewritten_query = self._expand_sql_terms(query)
                rewrite_method = "fallback_expansion"
            elif rewritten_query:
                rewrite_method = "gemini_enhanced"
            else:
                # No fallback, return original
                rewritten_query = query
                rewrite_method = "original"
            
            # Evaluate confidence
            confidence = self._evaluate_rewrite_confidence(query, rewritten_query)
            
            # Use original query if confidence is too low
            if confidence < MIN_CONFIDENCE_THRESHOLD and rewrite_method != "original":
                logger.warning(f"Low confidence rewrite ({confidence:.2f}), using original query")
                rewritten_query = query
                rewrite_method = "original_low_confidence"
                confidence = 1.0  # Original query has full confidence
            
            rewrite_time = time.time() - start_time
            
            # Build result
            result = {
                'original_query': query,
                'rewritten_query': rewritten_query,
                'confidence': confidence,
                'rewrite_method': rewrite_method,
                'model_used': model_to_use if 'model_to_use' in locals() else self.model,
                'intent_analysis': intent_analysis,
                'rewrite_time': rewrite_time,
                'llm_error': llm_error,
                'cache_hit': False
            }
            
            # Cache successful results
            if confidence >= MIN_CONFIDENCE_THRESHOLD:
                self._save_to_cache(cache_key, result)
            
            logger.info(f"Query rewrite completed: {rewrite_method}, confidence: {confidence:.2f}, time: {rewrite_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            
            # Return original query as fallback
            return {
                'original_query': query,
                'rewritten_query': query,
                'confidence': 1.0,
                'rewrite_method': 'error_fallback',
                'intent_analysis': {},
                'rewrite_time': time.time() - start_time,
                'llm_error': str(e),
                'cache_hit': False
            }


def create_query_rewriter(
    model: str = DEFAULT_GEMINI_MODEL, 
    enable_cache: bool = True, 
    project: str = None,
    auto_select_model: bool = False
) -> QueryRewriter:
    """
    Factory function to create a QueryRewriter instance
    
    Args:
        model: Gemini model to use ('gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.5-flash-lite')
        enable_cache: Whether to enable query rewrite caching
        project: Google Cloud project ID
        auto_select_model: Whether to automatically select model based on query complexity
    """
    return QueryRewriter(model=model, enable_cache=enable_cache, project=project)

def select_optimal_gemini_model(query: str, intent_analysis: Dict[str, Any]) -> str:
    """
    Select optimal Gemini model based on query complexity
    
    Args:
        query: User query
        intent_analysis: Query intent analysis results
        
    Returns:
        Optimal Gemini model name
    """
    complexity = intent_analysis.get('complexity', 'simple')
    query_length = len(query.split())
    focus_areas = intent_analysis.get('focus_areas', [])
    
    # Use Pro for complex queries or multiple focus areas
    if complexity == 'complex' or len(focus_areas) > 2 or query_length > 15:
        return GEMINI_PRO_MODEL
    
    # Use Flash-lite for very simple queries  
    elif complexity == 'simple' and len(focus_areas) == 0 and query_length < 5:
        return GEMINI_LITE_MODEL
    
    # Default to Flash for balanced performance/cost
    else:
        return DEFAULT_GEMINI_MODEL


def test_query_rewriter():
    """Test function for the query rewriter with Gemini integration"""
    print("🔄 Testing Gemini Query Rewriter")
    print("=" * 50)
    
    # Test with different configuration options
    print("\n1. Testing with default Flash model...")
    rewriter = create_query_rewriter()
    
    print("\n2. Testing with auto model selection...")
    rewriter_auto = create_query_rewriter(auto_select_model=True)
    
    test_queries = [
        "How to join tables?",
        "Customer spending analysis with complex aggregations and multiple table relationships",
        "Performance optimization tips",
        "Simple inventory count",
        "Which queries show aggregation patterns with GROUP BY and HAVING clauses?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        
        # Test with default model
        result = rewriter.rewrite_query(query)
        print(f"   Default Model: {result.get('model_used', 'unknown')}")
        print(f"   Original: {result['original_query']}")
        print(f"   Rewritten: {result['rewritten_query'][:100]}{'...' if len(result['rewritten_query']) > 100 else ''}")
        print(f"   Method: {result['rewrite_method']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Time: {result['rewrite_time']:.3f}s")
        
        # Test with auto model selection for comparison
        result_auto = rewriter_auto.rewrite_query(query, auto_select_model=True)
        if result_auto.get('model_used') != result.get('model_used'):
            print(f"   Auto-Selected Model: {result_auto.get('model_used', 'unknown')}")
            print(f"   Complexity: {result_auto['intent_analysis'].get('complexity', 'unknown')}")


if __name__ == "__main__":
    test_query_rewriter()
