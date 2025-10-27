#!/usr/bin/env python3
"""
SQL Extraction Service

A dedicated service for extracting SQL from text responses
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

class SQLExtractionService:
    """Dedicated service for SQL extraction from text"""
    
    def __init__(self):
        # Try to initialize LLM, but fail gracefully
        self.llm_client = None
        self.init_llm_client()
    
    def init_llm_client(self):
        """Initialize LLM client for extraction"""
        try:
            from gemini_client import GeminiClient
            import os
            
            self.llm_client = GeminiClient(
                api_key=os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'),
                model="gemini-2.5-flash-lite"
            )
            logger.info("✅ SQL Extraction Service LLM client ready")
            
        except Exception as e:
            logger.warning(f"⚠️ SQL Extraction Service: Could not initialize LLM client: {e}")
            self.llm_client = None
    
    def extract_sql_simple(self, text: str, debug: bool = True) -> Optional[str]:
        """Simple SQL extraction - no LLM, just basic patterns"""
        if not text or len(text.strip()) < 10:
            return None
        
        if debug:
            logger.info(f"🔍 Simple SQL extraction attempt ({len(text)} chars)")
            logger.info(f"📝 Input text:\n[START]\n{text}\n[END]")
        
        # Simple patterns first
        patterns = [
            (r'```sql\s*([^`]+)```', 1),
            (r'```([^`]*)```', 1),
            (r'SELECT[^;]+;', 0),
            (r'WITH[^;]+;', 0)
        ]
        
        for pattern, group_idx in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    if group_idx > 0:
                        result = match.group(group_idx).strip()
                    else:
                        result = match.group(0).strip()
                    
                    if result and len(result) > 10:
                        # Basic validation
                        result_upper = result.upper()
                        if any(keyword in result_upper for keyword in ['SELECT', 'WITH', 'INSERT', 'UPDATE']):
                            logger.info(f"✅ Simple extraction found SQL ({len(result)} chars)")
                            return result
                            
            except Exception as e:
                logger.warning(f"Pattern {pattern} failed: {e}")
                continue
        
        logger.warning("❌ Simple extraction found no SQL")
        return None
    
    def extract_sql_with_llm(self, text: str, debug: bool = True) -> Optional[str]:
        """LLM-based SQL extraction"""
        if not self.llm_client:
            logger.warning("LLM client not available, falling back to simple extraction")
            return self.extract_sql_simple(text, debug)
        
        if debug:
            logger.info(f"🤖 LLM extraction attempt ({len(text)} chars)")
            logger.info(f"📝 Input text:\n[START]\n{text}\n[END]")
        
        try:
            prompt = f"""Extract ONLY the SQL query from this text. Return the SQL and nothing else.

Rules:
1. Return ONLY the SQL query
2. Do not include any explanations or comments
3. Start directly with the SQL keyword
4. End with semicolon if possible
5. If no SQL is found, return "NO_SQL_FOUND"

Text to extract from:
{text}

SQL:"""
            
            result = self.llm_client.invoke(prompt)
            
            if result and result.strip():
                result = result.strip()
                
                if "NO_SQL_FOUND" in result.upper():
                    logger.info("LLM reported no SQL found")
                    return None
                
                # Validate basic SQL structure
                result_upper = result.upper()
                if any(keyword in result_upper for keyword in ['SELECT', 'WITH', 'INSERT', 'UPDATE']):
                    logger.info(f"✅ LLM extraction found SQL ({len(result)} chars)")
                    return result
                else:
                    logger.warning(f"LLM result doesn't look like SQL: {result[:50]}...")
                    return None
            else:
                logger.warning("LLM returned empty result")
                return None
                
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return None
    
    def extract_sql(self, text: str, prefer_llm: bool = True, debug: bool = True) -> Optional[str]:
        """Main extraction method - try LLM first, fallback to patterns"""
        if prefer_llm and self.llm_client:
            result = self.extract_sql_with_llm(text, debug)
            if result:
                return result
        
        # Fallback to simple extraction
        return self.extract_sql_simple(text, debug)

# Global instance for easy import
_sql_service = None

def get_sql_extraction_service():
    """Get global SQL extraction service instance"""
    global _sql_service
    if _sql_service is None:
        _sql_service = SQLExtractionService()
    return _sql_service

def extract_sql_from_text(text: str, debug: bool = True) -> Optional[str]:
    """Convenience function for quick extraction"""
    service = get_sql_extraction_service()
    return service.extract_sql(text, prefer_llm=True, debug=debug)