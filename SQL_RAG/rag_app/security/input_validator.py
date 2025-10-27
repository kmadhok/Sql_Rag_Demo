"""Input validation utilities for security"""

import re
import logging
from typing import Optional, List
from config.safe_config import safe_config

logger = logging.getLogger(__name__)

class InputValidator:
    """Input validation and sanitization"""
    
    # Patterns for dangerous input
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'vbscript:',   # VBScript protocol
        r'on\w+\s*=',  # Event handlers
        r'\b(eval|exec|system)\s*\(',  # Code execution
        r'\$\{.*\}',  # Template injection
        r'\$\(.*\)',   # jQuery injection
        r'<\?php',      # PHP injection
        r'\[\[.*\]\]', # Template injection
    ]
    
    def __init__(self, validation_level: str = 'standard'):
        """Initialize input validator
        
        Args:
            validation_level: 'strict', 'standard', or 'legacy'
        """
        self.validation_level = validation_level or safe_config.get_security_level()
    
    def validate_user_input(self, user_input: str, input_type: str = 'general') -> tuple[bool, Optional[str]]:
        """Validate user input for safety
        
        Args:
            user_input: User input to validate
            input_type: Type of input ('query', 'search', 'general')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not user_input or not isinstance(user_input, str):
            return False, "Invalid input type or empty input"
        
        # Check length limits
        if not self._validate_length(user_input, input_type):
            return False, f"Input too long for {input_type}"
        
        # Check for dangerous patterns
        if self.validation_level != 'legacy':
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, user_input, re.IGNORECASE | re.DOTALL):
                    logger.warning(f"Dangerous pattern detected in {input_type}: {pattern}")
                    return False, f"Potentially dangerous input detected"
        
        # Type-specific validation
        if input_type == 'query':
            return self._validate_query_input(user_input)
        elif input_type == 'search':
            return self._validate_search_input(user_input)
        
        return True, None
    
    def _validate_length(self, user_input: str, input_type: str) -> bool:
        """Validate input length"""
        length_limits = {
            'query': 2000,      # SQL queries can be longer
            'search': 500,       # Search terms shorter
            'general': 1000,     # General input
            'filename': 255,     # Filenames
            'table_name': 64     # Table names
        }
        
        max_length = length_limits.get(input_type, 1000)
        return len(user_input) <= max_length
    
    def _validate_query_input(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate SQL query input"""
        # Check for obvious SQL injection attempts
        injection_patterns = [
            r'(\;|\-\-|\/\*|\*\/)',  # SQL comments
            r'\b(UNION\s+SELECT|EXEC\s*\(|SP_)',  # SQL injection
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "Potential SQL injection detected"
        
        return True, None
    
    def _validate_search_input(self, search_term: str) -> tuple[bool, Optional[str]]:
        """Validate search input"""
        # Allow most characters in search but limit dangerous ones
        dangerous_chars = ['<', '>', '|', '&', ';', '`', '$']
        
        for char in dangerous_chars:
            if char in search_term:
                return False, f"Character '{char}' not allowed in search"
        
        return True, None
    
    def sanitize_input(self, user_input: str) -> str:
        """Sanitize input by removing dangerous elements"""
        sanitized = user_input
        
        # Remove HTML tags
        sanitized = re.sub(r'<[^>]*>', '', sanitized)
        
        # Remove JavaScript/VBScript protocols
        sanitized = re.sub(r'(javascript|vbscript):', '', sanitized, flags=re.IGNORECASE)
        
        # Remove event handlers
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        return sanitized.strip()

# Backward compatibility wrapper
def validate_input_legacy_wrapper(user_input: str, input_type: str = 'general') -> tuple[bool, Optional[str]]:
    """Wrapper for backward compatibility"""
    
    if safe_config.strict_input_validation:
        validator = InputValidator()
        return validator.validate_user_input(user_input, input_type)
    else:
        # Legacy mode - minimal validation
        logger.debug("Strict input validation disabled (legacy mode)")
        
        # Basic safety check only
        if not user_input or not isinstance(user_input, str):
            return False, "Invalid input"
        
        return len(user_input) <= 10000, None  # Reasonable length limit