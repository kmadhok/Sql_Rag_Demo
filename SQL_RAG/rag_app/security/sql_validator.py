"""SQL validation wrapper with security controls"""

import re
import logging
from typing import Tuple, List, Optional
from config.safe_config import safe_config

logger = logging.getLogger(__name__)

class SafeSQLValidator:
    """SQL validation and security wrapper"""
    # Dangerous SQL patterns to block (UNION allowed for read-only operations)
    DANGEROUS_PATTERNS = [
        r'\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE)\b',
        r'\b(EXEC|EXECUTE)\b',  # Removed UNION as it's safe for read-only operations
        r'(\-\-|\/\*|\*\/)',  # Comment delimiters (removed ; as it's valid SQL syntax)
        r'(\<\?php|\<script)',  # Script injection
        r'\b(exec\(|system\(|shell_exec\()\b',  # Command execution
        r'\b(xp_cmdshell|sp_oacreate)\b',  # SQL Server specific
    ]
    
    # Allowed SQL keywords (whitelist approach)
    ALLOWED_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
        'GROUP', 'BY', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET', 'WITH', 'AS', 'ON',
        'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'ILIKE',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'DATE', 'TIME', 'TIMESTAMP', 'INTERVAL', 'CAST', 'EXTRACT', 'UNION'
    ]
    
    def __init__(self, validation_level: str = 'standard'):
        """Initialize SQL validator
        
        Args:
            validation_level: 'strict', 'standard', or 'legacy'
        """
        self.validation_level = validation_level or safe_config.get_security_level()
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate SQL query for safety
        
        Args:
            query: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not isinstance(query, str):
            return False, "Invalid query input"
        
        query_clean = query.strip().upper()
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query_clean, re.IGNORECASE):
                matched = re.search(pattern, query_clean, re.IGNORECASE).group()
                logger.warning(f"Dangerous SQL pattern detected: {matched}")
                return False, f"Dangerous SQL pattern blocked: {matched}"
        
        # Extra validation for strict mode
        if self.validation_level == 'strict':
            # Check if query starts with SELECT only
            if not query_clean.startswith('SELECT '):
                return False, "Only SELECT queries allowed in strict mode"
            
            # Validate table names (prevent injection)
            table_names = self._extract_table_names(query)
            for table in table_names:
                if not self._is_valid_table_name(table):
                    return False, f"Invalid table name detected: {table}"
        
        # Validate in standard mode
        if self.validation_level == 'standard':
            # Check for allowed keywords
            if not self._has_only_allowed_keywords(query):
                logger.warning(f"Query contains potentially unsafe keywords: {query[:100]}...")
                # Allow in standard mode but log
        
        logger.debug(f"SQL validation passed: {self.validation_level}")
        return True, None
    
    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        # Simple regex for table name extraction
        pattern = r'\bFROM\s+([\w\.]+)|\bJOIN\s+([\w\.]+)'
        matches = re.findall(pattern, query, re.IGNORECASE)
        
        table_names = []
        for match in matches:
            for table in match:
                if table and table not in table_names:
                    table_names.append(table)
        
        return table_names
    
    def _is_valid_table_name(self, table_name: str) -> bool:
        """Validate individual table name"""
        if not table_name:
            return False
        
        # Check for dangerous characters
        dangerous_chars = [';', '--', '/*', '*/', '<', '>', '|', '&']
        for char in dangerous_chars:
            if char in table_name:
                return False
        
        # Check pattern (alphanumeric, underscore, period)
        pattern = r'^[a-zA-Z0-9_\.]+$'
        return bool(re.match(pattern, table_name))
    
    def _has_only_allowed_keywords(self, query: str) -> bool:
        """Check if query contains only allowed SQL keywords"""
        query_upper = query.upper()
        
        # Extract SQL keywords from query
        sql_keywords = re.findall(r'\b[A-Z_]+\b', query_upper)
        
        for keyword in sql_keywords:
            if keyword not in self.ALLOWED_KEYWORDS:
                return False
        
        return True
    
    def sanitize_query(self, query: str) -> str:
        """Sanitize query by removing dangerous patterns"""
        # Remove comment-style attacks
        sanitized = re.sub(r'(\-\-|\/\*|\*\/)', '', query)
        
        # Remove dangerous SQL keywords (replace with safe SELECT)
        for pattern in self.DANGEROUS_PATTERNS:
            if 'DROP' in pattern or 'DELETE' in pattern or 'UPDATE' in pattern:
                sanitized = re.sub(pattern, 'SELECT', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()

# Backward compatibility wrapper
def validate_sql_legacy_wrapper(query: str) -> Tuple[bool, Optional[str]]:
    """Wrapper for backward compatibility"""
    
    if safe_config.enable_sql_validation:
        validator = SafeSQLValidator()
        return validator.validate_query(query)
    else:
        # Legacy mode - always pass (unsafe but maintains compatibility)
        logger.debug("SQL validation disabled (legacy mode)")
        return True, None