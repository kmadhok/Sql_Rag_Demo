"""Security configuration with feature flags"""

import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SafeConfig:
    """Security configuration with gradual rollout support"""
    
    # Security feature flags
    use_safe_deserialization: bool = os.getenv('USE_SAFE_DESERIALIZATION', 'false').lower() == 'true'
    enable_sql_validation: bool = os.getenv('ENABLE_SQL_VALIDATION', 'true').lower() == 'true'
    strict_input_validation: bool = os.getenv('STRICT_INPUT_VALIDATION', 'false').lower() == 'true'
    
    # Legacy mode for rollback
    fallback_legacy_mode: bool = os.getenv('FALLBACK_LEGACY_MODE', 'true').lower() == 'true'
    
    # Rollout control
    rollout_percentage: int = int(os.getenv('SECURITY_ROLLOUT_PERCENTAGE', '0'))
    
    @property
    def should_use_new_security(self) -> bool:
        """Determine if new security features should be used"""
        if self.fallback_legacy_mode:
            return False
        
        # Gradual rollout based on percentage
        import random
        user_hash = hash(os.getenv('USER_SESSION_ID', 'default'))
        return (user_hash % 100) < self.rollout_percentage
    
    def get_security_level(self) -> str:
        """Get current security level"""
        if self.fallback_legacy_mode:
            return 'legacy'
        elif self.should_use_new_security:
            return 'strict' if self.strict_input_validation else 'standard'
        else:
            return 'legacy'

# Global configuration instance
safe_config = SafeConfig()