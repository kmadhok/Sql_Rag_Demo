import json
import os
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib

class ProgressTracker:
    """
    Progress tracking system for long-running batch processing jobs.
    
    Saves progress periodically to allow resuming from failures.
    """
    
    def __init__(self, job_name: str, checkpoint_dir: str = "checkpoints"):
        self.job_name = job_name
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.checkpoint_file = self.checkpoint_dir / f"{job_name}_progress.json"
        self.results_file = self.checkpoint_dir / f"{job_name}_results.json"
        
        # Progress state
        self.total_items = 0
        self.processed_items = 0
        self.failed_items = 0
        self.start_time = time.time()
        self.last_checkpoint_time = time.time()
        
        # Results storage
        self.results = []
        self.failed_queries = []
        self.processed_hashes = set()
        
        # Load existing progress if available
        self._load_progress()
    
    def initialize(self, items: List[Any], resume: bool = True) -> List[Any]:
        """
        Initialize progress tracker with items to process.
        
        Args:
            items: List of items to process
            resume: Whether to resume from previous checkpoint
            
        Returns:
            List of items that still need processing
        """
        self.total_items = len(items)
        
        if resume and self._has_existing_progress():
            remaining_items = self._get_remaining_items(items)
            print(f"Resuming from checkpoint: {self.processed_items}/{self.total_items} already processed")
            print(f"Remaining items to process: {len(remaining_items)}")
            return remaining_items
        else:
            # Fresh start
            self._reset_progress()
            print(f"Starting fresh with {self.total_items} items to process")
            return items
    
    def record_success(self, item: Any, result: Dict[str, Any]):
        """Record a successful processing result."""
        item_hash = self._get_item_hash(item)
        
        if item_hash not in self.processed_hashes:
            self.processed_items += 1
            self.processed_hashes.add(item_hash)
            
            # Store result with metadata
            result_entry = {
                "item": item,
                "result": result,
                "processed_at": time.time(),
                "item_hash": item_hash
            }
            self.results.append(result_entry)
            
            # Checkpoint periodically
            if self.processed_items % 10 == 0 or time.time() - self.last_checkpoint_time > 60:
                self._save_checkpoint()
    
    def record_failure(self, item: Any, error: str):
        """Record a failed processing attempt."""
        item_hash = self._get_item_hash(item)
        
        self.failed_items += 1
        failure_entry = {
            "item": item,
            "error": error,
            "failed_at": time.time(),
            "item_hash": item_hash
        }
        self.failed_queries.append(failure_entry)
        
        # Still count as processed to avoid infinite retries
        if item_hash not in self.processed_hashes:
            self.processed_items += 1
            self.processed_hashes.add(item_hash)
        
        # Checkpoint on failures too
        if self.failed_items % 5 == 0:
            self._save_checkpoint()
    
    def get_progress_stats(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        elapsed_time = time.time() - self.start_time
        success_rate = ((self.processed_items - self.failed_items) / max(1, self.processed_items)) * 100
        
        if self.processed_items > 0:
            avg_time_per_item = elapsed_time / self.processed_items
            eta_seconds = avg_time_per_item * (self.total_items - self.processed_items)
        else:
            avg_time_per_item = 0
            eta_seconds = 0
        
        return {
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.processed_items - self.failed_items,
            "failed_items": self.failed_items,
            "success_rate": success_rate,
            "progress_percentage": (self.processed_items / max(1, self.total_items)) * 100,
            "elapsed_time": elapsed_time,
            "avg_time_per_item": avg_time_per_item,
            "eta_seconds": eta_seconds,
            "eta_formatted": self._format_time(eta_seconds)
        }
    
    def print_progress(self):
        """Print formatted progress information."""
        stats = self.get_progress_stats()
        
        print(f"\n=== PROGRESS UPDATE ===")
        print(f"Processed: {stats['processed_items']}/{stats['total_items']} "
              f"({stats['progress_percentage']:.1f}%)")
        print(f"Successful: {stats['successful_items']}")
        print(f"Failed: {stats['failed_items']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Elapsed: {self._format_time(stats['elapsed_time'])}")
        print(f"ETA: {stats['eta_formatted']}")
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Get all successful results."""
        return [entry["result"] for entry in self.results]
    
    def get_failed_items(self) -> List[Dict[str, Any]]:
        """Get all failed items for retry."""
        return self.failed_queries
    
    def save_final_results(self, additional_data: Optional[Dict[str, Any]] = None):
        """Save final results and cleanup checkpoint files."""
        final_results = {
            "job_name": self.job_name,
            "completed_at": time.time(),
            "stats": self.get_progress_stats(),
            "results": [entry["result"] for entry in self.results],
            "failed_queries": self.failed_queries
        }
        
        if additional_data:
            final_results.update(additional_data)
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        # Clean up checkpoint file
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        
        print(f"Final results saved to: {self.results_file}")
        return final_results
    
    def _get_item_hash(self, item: Any) -> str:
        """Generate a hash for an item to track uniqueness."""
        if isinstance(item, dict):
            # Sort keys for consistent hashing
            item_str = json.dumps(item, sort_keys=True)
        else:
            item_str = str(item)
        
        return hashlib.md5(item_str.encode()).hexdigest()[:12]
    
    def _save_checkpoint(self):
        """Save current progress to checkpoint file."""
        checkpoint_data = {
            "job_name": self.job_name,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "start_time": self.start_time,
            "last_checkpoint_time": time.time(),
            "processed_hashes": list(self.processed_hashes),
            "results": self.results,
            "failed_queries": self.failed_queries
        }
        
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        self.last_checkpoint_time = time.time()
    
    def _load_progress(self):
        """Load progress from checkpoint file if it exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                self.total_items = checkpoint_data.get("total_items", 0)
                self.processed_items = checkpoint_data.get("processed_items", 0)
                self.failed_items = checkpoint_data.get("failed_items", 0)
                self.start_time = checkpoint_data.get("start_time", time.time())
                self.processed_hashes = set(checkpoint_data.get("processed_hashes", []))
                self.results = checkpoint_data.get("results", [])
                self.failed_queries = checkpoint_data.get("failed_queries", [])
                
                print(f"Loaded checkpoint: {self.processed_items} items already processed")
                
            except Exception as e:
                print(f"Warning: Could not load checkpoint file: {e}")
                self._reset_progress()
    
    def _has_existing_progress(self) -> bool:
        """Check if there is existing progress to resume from."""
        return self.checkpoint_file.exists() and self.processed_items > 0
    
    def _get_remaining_items(self, items: List[Any]) -> List[Any]:
        """Get items that haven't been processed yet."""
        remaining = []
        for item in items:
            item_hash = self._get_item_hash(item)
            if item_hash not in self.processed_hashes:
                remaining.append(item)
        return remaining
    
    def _reset_progress(self):
        """Reset all progress tracking."""
        self.processed_items = 0
        self.failed_items = 0
        self.start_time = time.time()
        self.results = []
        self.failed_queries = []
        self.processed_hashes = set()
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m {seconds%60:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"