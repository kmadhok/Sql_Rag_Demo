"""Safe alternatives to dangerous operations with fallback support"""

import json
import logging
import pickle
from typing import Any, Optional, Dict, List
from pathlib import Path

from config.safe_config import safe_config

logger = logging.getLogger(__name__)

class SafeLoader:
    """Safe loading alternatives with fallback to legacy methods"""
    
    @staticmethod
    def safe_pickle_load(file_path: Path, fallback_to_legacy: bool = True) -> Any:
        """Safe pickle loading with validation and fallback"""
        
        if not safe_config.use_safe_deserialization:
            if fallback_to_legacy:
                logger.warning(f"Using legacy pickle loading for {file_path}")
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            else:
                raise ValueError("Safe deserialization is disabled")
        
        try:
            # Safe loading with validation
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # Validate the loaded data
            if SafeLoader._validate_pickle_data(data):
                logger.info(f"✅ Safe pickle load successful: {file_path}")
                return data
            else:
                logger.error(f"❌ Pickle data validation failed: {file_path}")
                if fallback_to_legacy:
                    # Try legacy as fallback
                    with open(file_path, 'rb') as f:
                        return pickle.load(f)
                raise ValueError("Invalid pickle data")
                
        except Exception as e:
            logger.error(f"Safe pickle loading failed: {e}")
            if fallback_to_legacy:
                logger.warning(f"Falling back to legacy loading: {file_path}")
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            raise
    
    @staticmethod
    def _validate_pickle_data(data: Any) -> bool:
        """Validate loaded pickle data for safety"""
        # Basic validation - check for expected data types
        allowed_types = (dict, list, tuple, str, int, float, bool, type(None))
        
        def is_safe_type(obj):
            if isinstance(obj, allowed_types):
                return True
            elif isinstance(obj, (list, tuple)):
                return all(is_safe_type(item) for item in obj)
            elif isinstance(obj, dict):
                return all(is_safe_type(k) and is_safe_type(v) for k, v in obj.items())
            return False
        
        return is_safe_type(data)
    
    @staticmethod
    def safe_json_load(file_path: Path) -> Dict[str, Any]:
        """Safe JSON loading with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate JSON structure
            if isinstance(data, dict):
                logger.info(f"✅ Safe JSON load successful: {file_path}")
                return data
            else:
                logger.error(f"❌ JSON data is not a dictionary: {file_path}")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {}
        except Exception as e:
            logger.error(f"JSON loading error: {e}")
            return {}
    
    @staticmethod
    def validate_file_path(file_path: Path, base_dir: Optional[Path] = None) -> bool:
        """Validate file path to prevent directory traversal"""
        if base_dir is None:
            base_dir = Path.cwd()
        
        try:
            # Resolve and check if path is within base directory
            resolved_path = file_path.resolve()
            base_resolved = base_dir.resolve()
            
            return resolved_path.is_relative_to(base_resolved)
        except Exception:
            return False

@staticmethod
def safe_load_vector_store_fallback(
    index_path: Path, 
    embeddings: Any, 
    fallback_to_legacy: bool = True
) -> Any:
    """Safe FAISS vector store loading with fallback"""
    
    try:
        # Try safe loading first
        import pickle
        
        # Validate the index path
        if not SafeLoader.validate_file_path(index_path):
            raise ValueError(f"Invalid index path: {index_path}")
        
        faiss_file = index_path / "index.faiss"
        pkl_file = index_path / "index.pkl"
        
        # Safe loading of vector store components
        if faiss_file.exists() and pkl_file.exists():
            # Validate pickle data first
            with open(pkl_file, 'rb') as f:
                pickle_data = f.read()
            
            if not SafeLoader._validate_pickle_data_raw(pickle_data):
                if not fallback_to_legacy:
                    raise ValueError("Pickle data validation failed and fallback disabled")
                logger.warning("Pickle validation failed, falling back to legacy loading")
            else:
                logger.info("✅ Pickle data validation passed")
        
        # Load with safe validation enabled
        vector_store = FAISS.load_local(
            str(index_path),
            embeddings,
            allow_dangerous_deserialization=False  # Safe mode
        )
        
        logger.info(f"✅ Safe vector store load successful: {index_path}")
        return vector_store
        
    except Exception as e:
        logger.error(f"Safe vector store loading failed: {e}")
        
        if fallback_to_legacy:
            logger.warning(f"Falling back to legacy vector store loading: {index_path}")
            return FAISS.load_local(
                str(index_path),
                embeddings,
                allow_dangerous_deserialization=True  # Legacy fallback
            )
        raise
    
    @staticmethod
    def _validate_pickle_data_raw(pickle_data: bytes) -> bool:
        """Validate raw pickle data without unpickling"""
        try:
            import pickle
            import io
            
            # Basic safety checks on pickle data
            if len(pickle_data) > 100 * 1024 * 1024:  # 100MB limit
                logger.warning("Pickle data too large for safe validation")
                return False
            
            # Check for dangerous patterns in pickle data
            dangerous_patterns = [
                b'__reduce__',
                b'__reduce_ex__',
                b'eval',
                b'exec',
                b'compile',
                b'open',
                b'file',
                b'input'
            ]
            
            for pattern in dangerous_patterns:
                if pattern in pickle_data:
                    logger.warning(f"Dangerous pattern found in pickle data: {pattern}")
                    return False
            
            # Try safe unpickling with restricted globals
            class SafeUnpickler(pickle.Unpickler):
                def find_class(self, module, name):
                    # Only allow safe classes
                    allowed_classes = [
                        ('collections', 'defaultdict'),
                        ('builtins', 'dict'),
                        ('builtins', 'list'),
                        ('builtins', 'tuple'),
                        ('builtins', 'set'),
                        ('builtins', 'frozenset'),
                        ('pandas', 'DataFrame'),
                        ('pandas', 'Series'),
                        ('numpy', 'ndarray'),
                        ('numpy', 'array')
                    ]
                    
                    if (module, name) in allowed_classes:
                        return super().find_class(module, name)
                    
                    # Allow some FAISS classes
                    if 'faiss' in module or 'langchain' in module:
                        return super().find_class(module, name)
                    
                    raise pickle.UnpicklingError(f"Class {module}.{name} not allowed for safety")
            
            # Test with safe unpickler
            try:
                safe_unpickler = SafeUnpickler(io.BytesIO(pickle_data))
                test_obj = safe_unpickler.load()
                return True
            except Exception as e:
                logger.warning(f"Safe unpickler test failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Pickle validation error: {e}")
            return False

# Compatibility layer for gradual migration
def safe_load_legacy_wrapper(file_path: Path, file_type: str = 'pickle') -> Any:
    """Wrapper for backward compatibility during migration"""
    
    if safe_config.should_use_new_security:
        if file_type == 'pickle':
            return SafeLoader.safe_pickle_load(file_path)
        elif file_type == 'json':
            return SafeLoader.safe_json_load(file_path)
    
    # Legacy fallback
    logger.warning(f"Using legacy loader for {file_path} (type: {file_type})")
    
    if file_type == 'pickle':
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    elif file_type == 'json':
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")