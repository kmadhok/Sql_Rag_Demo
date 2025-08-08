import os
import shutil
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("rebuild_embeddings.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def clear_vector_store(vector_store_path: str) -> bool:
    """
    Clear the vector store directory
    
    Args:
        vector_store_path: Path to the vector store directory
        
    Returns:
        bool: True if successful, False otherwise
    """
    path = Path(vector_store_path)
    if path.exists():
        try:
            # Remove all files but keep directory
            for file in path.glob("*"):
                if file.is_file():
                    file.unlink()
                    logger.info(f"Removed file: {file}")
                elif file.is_dir():
                    shutil.rmtree(file)
                    logger.info(f"Removed directory: {file}")
            logger.info(f"Vector store cleared: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear vector store: {str(e)}")
            return False
    else:
        logger.warning(f"Vector store path does not exist: {path}")
        return False

def force_rebuild_embeddings(vector_store_path: str, status_file_path: str):
    """
    Force rebuild of embeddings by clearing vector store and status
    
    Args:
        vector_store_path: Path to the vector store directory
        status_file_path: Path to the status file
        
    Returns:
        EmbeddingManager: A new embedding manager instance
    """
    logger.info(f"Forcing rebuild of embeddings: {vector_store_path}")
    from .embedding_manager import EmbeddingManager
    
    # Clear vector store
    clear_vector_store(vector_store_path)
    
    # Reset status file
    status_path = Path(status_file_path)
    if status_path.exists():
        try:
            status_path.unlink()
            logger.info(f"Removed status file: {status_path}")
        except Exception as e:
            logger.error(f"Failed to remove status file: {str(e)}")
    
    # Initialize fresh embedding manager
    manager = EmbeddingManager(vector_store_path, status_file_path)
    logger.info("Created new embedding manager instance")
    
    return manager
