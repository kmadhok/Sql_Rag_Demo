"""Application configuration with feature flags"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_BASE_DIR = Path(__file__).parent.parent
_DEFAULT_FAISS_DIR = _BASE_DIR / "faiss_indices"
_DEFAULT_CSV_PATH = _BASE_DIR / "sample_queries_with_metadata.csv"
_DEFAULT_ANALYTICS_DIR = _BASE_DIR / "catalog_analytics"
_DEFAULT_SCHEMA_PATH = _BASE_DIR / "data_new/thelook_ecommerce_schema.csv"


def _env_path(key: str, default: Path) -> Path:
    """Resolve a path from environment, falling back to provided default."""
    value = os.getenv(key)
    if value:
        return Path(value).expanduser()
    return default


def _env_vector_store(default: str) -> str:
    """Resolve default vector store name with backwards compatibility."""
    return (
        os.getenv("DEFAULT_VECTOR_STORE")
        or os.getenv("VECTOR_STORE_NAME")
        or default
    )


@dataclass
class AppConfig:
    """Main application configuration with migration support"""

    # Original constants from main app (now env-aware)
    FAISS_INDICES_DIR: Path = field(default_factory=lambda: _env_path("FAISS_INDICES_DIR", _DEFAULT_FAISS_DIR))
    DEFAULT_VECTOR_STORE: str = field(default_factory=lambda: _env_vector_store("index_sample_queries_with_metadata_recovered"))
    CSV_PATH: Path = field(default_factory=lambda: _env_path("CSV_PATH", _DEFAULT_CSV_PATH))
    CATALOG_ANALYTICS_DIR: Path = field(default_factory=lambda: _env_path("CATALOG_ANALYTICS_DIR", _DEFAULT_ANALYTICS_DIR))
    SCHEMA_CSV_PATH: Path = field(default_factory=lambda: _env_path("SCHEMA_CSV_PATH", _DEFAULT_SCHEMA_PATH))

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
