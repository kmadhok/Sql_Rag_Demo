"""
Status file management for background embedding processing
"""

import os
import json
import threading
from pathlib import Path
from typing import Dict, Any

class BackgroundProcessingStatus:
    """Class to manage background processing status through a JSON file"""
    
    def __init__(self, status_file_path: str):
        """
        Initialize the status manager
        
        Args:
            status_file_path: Path to the JSON status file
        """
        self.status_file_path = Path(status_file_path)
        self.lock = threading.Lock()
        self._initialize_status()
        
    def _initialize_status(self):
        """Initialize or load the status file"""
        if self.status_file_path.exists():
            try:
                with open(self.status_file_path, 'r') as f:
                    self.status = json.load(f)
            except Exception as e:
                print(f"Error loading status file: {e}")
                self._create_default_status()
        else:
            self._create_default_status()
            
    def _create_default_status(self):
        """Create a default status dictionary"""
        self.status = {
            "is_complete": False,
            "background_task_running": False,
            "processed_queries": 0,
            "total_queries": 0,
            "last_updated": "",
            "error": None
        }
        self._save_status()
        
    def _save_status(self):
        """Save the current status to the JSON file"""
        with self.lock:
            with open(self.status_file_path, 'w') as f:
                json.dump(self.status, f, indent=2)
    
    def update_status(self, processed_count: int, total_count: int):
        """
        Update the processing status
        
        Args:
            processed_count: Number of queries processed
            total_count: Total number of queries
        """
        with self.lock:
            self.status["processed_queries"] = processed_count
            self.status["total_queries"] = total_count
            self.status["is_complete"] = processed_count >= total_count
            self.status["background_task_running"] = not self.status["is_complete"]
            
            from datetime import datetime
            self.status["last_updated"] = datetime.now().isoformat()
            
            self._save_status()
            
    def set_complete(self):
        """Mark the processing as complete"""
        with self.lock:
            self.status["is_complete"] = True
            self.status["background_task_running"] = False
            from datetime import datetime
            self.status["last_updated"] = datetime.now().isoformat()
            self._save_status()
    
    def set_error(self, error_message: str):
        """Set an error message"""
        with self.lock:
            self.status["error"] = error_message
            from datetime import datetime
            self.status["last_updated"] = datetime.now().isoformat()
            self._save_status()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status"""
        with self.lock:
            return dict(self.status)
