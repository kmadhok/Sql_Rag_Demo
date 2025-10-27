"""Application configuration with feature flags"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class AppConfig:
    """Main application configuration with migration support"""
    
    # Original constants from main app
    FAISS_INDICES_DIR: Path = Path(__file__).parent.parent / "faiss_indices"
    DEFAULT_VECTOR_STORE: str = "index_transformed_sample_queries"
    CSV_PATH: Path = Path(__file__).parent.parent / "sample_queries_with_metadata.csv"
    CATALOG_ANALYTICS_DIR: Path = Path(__file__).parent.parent / "catalog_analytics"
    SCHEMA_CSV_PATH: Path = Path(__file__).parent.parent / "data_new/thelook_ecommerce_schema.csv"
    
    # Pagination configuration
    QUERIES_PER_PAGE: int = 15
    MAX_PAGES_TO_SHOW: int = 10
    
    # Feature flags for migration
    use_modular_components: bool = os.getenv('USE_MODULAR_COMPONENTS', 'false').lower() == 'true'
    enable_performance_optimizations: bool = os.getenv('ENABLE_PERF_OPT', 'false').lower() == 'true'
    use_new_database_layer: bool = os.getenv('USE_NEW_DATABASE_LAYER', 'false').lower() == 'true'
    
    # Rollout control
    component_rollout_percentage: int = int(os.getenv('COMPONENT_ROLLOUT_PERCENTAGE', '0'))
    
    # Debug and logging
    debug_mode: bool = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    verbose_logging: bool = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
    
    @property
    def should_use_modular_components(self) -> bool:
        """Determine if modular components should be used"""
        if not self.use_modular_components:
            return False
        
        # Gradual rollout
        import random
        rollout_hash = hash(os.getenv('USER_SESSION_ID', f"{os.getpid()}"))
        return (rollout_hash % 100) < self.component_rollout_percentage
    
    def get_database_mode(self) -> str:
        """Get database operation mode"""
        if self.use_new_database_layer:
            return 'modern'
        return 'legacy'
    
    def get_optimization_level(self) -> str:
        """Get performance optimization level"""
        if self.enable_performance_optimizations:
            return 'aggressive' if self.debug_mode else 'conservative'
        return 'legacy'

# Global configuration instance
app_config = AppConfig()