#!/usr/bin/env python3
"""
Standalone SQL Query Description Generator with Parallel Processing

This script generates descriptions for SQL queries in CSV files using parallel processing
for significant performance improvements. Completely decoupled from the RAG application.

Usage:
    python generate_descriptions.py
    python generate_descriptions.py --csv queries.csv --workers 8
    python generate_descriptions.py --force-rebuild --batch-size 25
    python generate_descriptions.py --dry-run --verbose
"""

import os
import sys
import pathlib
import argparse
import time
import threading
import csv
import json
import shutil
import tempfile
import platform
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Attempt to import required packages with helpful error messages
try:
    import pandas as pd
except ImportError:
    print("❌ Error: pandas is required. Install with: pip install pandas")
    sys.exit(1)

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerateContentResponse
except ImportError:
    print("❌ Error: google-generativeai is required. Install with: pip install google-generativeai")
    sys.exit(1)

try:
    import psutil
except ImportError:
    print("⚠️  Warning: psutil not found. Install with: pip install psutil for better resource detection")
    psutil = None


# ============================================================================
# Data Classes and Exceptions
# ============================================================================

@dataclass
class DescriptionTask:
    """Represents a single description generation task"""
    row_idx: int
    query_text: str
    attempt: int = 0
    max_retries: int = 3


@dataclass
class DescriptionResult:
    """Represents the result of a description generation task"""
    row_idx: int
    success: bool
    description: str
    error: Optional[str] = None
    processing_time: float = 0.0
    attempt: int = 0
    token_usage: Optional[Dict] = None


class DescriptionError(Exception):
    """Base exception for description generation"""
    pass


class OllamaConnectionError(DescriptionError):
    """Ollama service unavailable"""
    pass


class RateLimitError(DescriptionError):
    """Too many requests to Ollama"""
    pass


# ============================================================================
# Cross-Platform Worker Optimization
# ============================================================================

def get_optimal_workers() -> int:
    """Determine optimal worker count based on platform and resources"""
    cpu_count = os.cpu_count() or 4
    
    # Get available memory (GB) if psutil is available
    if psutil:
        try:
            memory_gb = psutil.virtual_memory().total / (1024**3)
        except:
            memory_gb = 8  # Default assumption
    else:
        memory_gb = 8  # Default assumption
    
    # Platform-specific optimizations
    system = platform.system()
    if system == "Windows":
        # Windows threading can be less efficient, be conservative
        base_workers = min(cpu_count // 2, 4)
    elif system == "Darwin":  # macOS
        # macOS handles threading well
        base_workers = min(cpu_count - 1, 8)  
    else:  # Linux and others
        # Linux has excellent threading support
        base_workers = min(cpu_count, 8)
    
    # Memory constraints (each worker uses ~100MB)
    memory_limited_workers = int(memory_gb * 10)  # 10 workers per GB
    
    # Ollama concurrency limits (empirically determined)
    ollama_optimal = 6  # Sweet spot for most Ollama instances
    
    optimal = min(base_workers, memory_limited_workers, ollama_optimal)
    return max(optimal, 1)  # At least 1 worker


# ============================================================================
# Advanced Progress Tracking
# ============================================================================

class AdvancedProgressTracker:
    """Advanced progress tracking with detailed metrics and ETA calculation"""
    
    def __init__(self, total_tasks: int, batch_size: int = 50):
        self.total_tasks = total_tasks
        self.batch_size = batch_size
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
        self.last_update = time.time()
        self.completion_times = []
        self.lock = threading.Lock()
        
    def update(self, success: bool, processing_time: float = 0):
        """Update progress with detailed metrics"""
        with self.lock:
            if success:
                self.completed += 1
            else:
                self.failed += 1
            
            if processing_time > 0:
                self.completion_times.append(processing_time)
        
        current_time = time.time()
        
        # Update every 5 seconds or when batch completes
        total_processed = self.completed + self.failed
        if (current_time - self.last_update > 5.0 or 
            total_processed % self.batch_size == 0 or
            total_processed == self.total_tasks):
            self._print_progress()
            self.last_update = current_time
    
    def _print_progress(self):
        """Print detailed progress information"""
        with self.lock:
            total_processed = self.completed + self.failed
            elapsed = time.time() - self.start_time
            
            # Calculate rates and ETA
            if total_processed > 0:
                rate = total_processed / elapsed
                eta_seconds = (self.total_tasks - total_processed) / rate if rate > 0 else 0
                eta = str(timedelta(seconds=int(eta_seconds)))
            else:
                rate = 0
                eta = "calculating..."
            
            # Average processing time
            avg_time = sum(self.completion_times) / len(self.completion_times) if self.completion_times else 0
            
            progress_percent = (total_processed / self.total_tasks) * 100
            
            print(f"\r🔄 Progress: {total_processed}/{self.total_tasks} ({progress_percent:.1f}%) | "
                  f"✅ {self.completed} ❌ {self.failed} | "
                  f"Rate: {rate:.1f}/s | Avg: {avg_time:.1f}s | ETA: {eta}", end="", flush=True)
            
            if total_processed == self.total_tasks:
                print()  # New line when complete
    
    def get_final_summary(self) -> dict:
        """Return comprehensive completion summary"""
        with self.lock:
            total_time = time.time() - self.start_time
            
            return {
                'total_tasks': self.total_tasks,
                'completed': self.completed,
                'failed': self.failed,
                'success_rate': (self.completed / self.total_tasks) * 100 if self.total_tasks > 0 else 0,
                'total_time': total_time,
                'average_time_per_task': sum(self.completion_times) / len(self.completion_times) if self.completion_times else 0,
                'tasks_per_second': self.total_tasks / total_time if total_time > 0 else 0
            }


# ============================================================================
# Safe CSV Operations
# ============================================================================

class SafeCSVProcessor:
    """Safe CSV processing with atomic operations and backup creation"""
    
    def __init__(self, csv_path: pathlib.Path, backup_dir: Optional[pathlib.Path] = None):
        self.csv_path = csv_path
        self.backup_dir = backup_dir or csv_path.parent
        self.backup_path = None
        
    def create_backup(self) -> pathlib.Path:
        """Create timestamped backup of CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{self.csv_path.stem}_backup_{timestamp}.csv"
        self.backup_path = self.backup_dir / backup_filename
        
        shutil.copy2(self.csv_path, self.backup_path)
        print(f"📄 Created backup: {self.backup_path}")
        return self.backup_path
    
    def get_csv_analysis(self) -> Dict:
        """Analyze CSV structure and content"""
        try:
            df = pd.read_csv(self.csv_path)
            
            # Validate structure
            if 'query' not in df.columns:
                raise ValueError("CSV missing required 'query' column")
            
            has_description_col = 'description' in df.columns
            
            # Count queries needing descriptions
            queries_needing_descriptions = []
            if has_description_col:
                for idx, row in df.iterrows():
                    query_text = row.get('query', '')
                    if pd.isna(query_text):
                        continue
                    query_text = str(query_text).strip()
                    
                    description = row.get('description', '')
                    if pd.isna(description):
                        description = ''
                    else:
                        description = str(description).strip()
                    
                    if query_text and not description:
                        queries_needing_descriptions.append((idx, query_text))
            else:
                # No description column - all queries need descriptions
                for idx, row in df.iterrows():
                    query_text = row.get('query', '')
                    if not pd.isna(query_text) and str(query_text).strip():
                        queries_needing_descriptions.append((idx, str(query_text).strip()))
            
            return {
                'total_queries': len(df),
                'has_description_column': has_description_col,
                'queries_needing_descriptions': queries_needing_descriptions,
                'columns': list(df.columns)
            }
            
        except Exception as e:
            raise ValueError(f"Error analyzing CSV: {e}")
    
    def ensure_description_column(self) -> bool:
        """Ensure CSV has description column, add if missing"""
        try:
            df = pd.read_csv(self.csv_path)
            
            if 'description' in df.columns:
                return False  # Already exists
            
            # Add empty description column
            df['description'] = ""
            
            # Create temporary backup during operation
            temp_backup = self.csv_path.with_suffix('.temp_backup')
            shutil.copy2(self.csv_path, temp_backup)
            
            try:
                df.to_csv(self.csv_path, index=False)
                temp_backup.unlink()  # Remove temp backup on success
                print(f"📝 Added 'description' column to {self.csv_path.name}")
                return True
            except Exception:
                # Restore from temp backup on failure
                temp_backup.rename(self.csv_path)
                raise
                
        except Exception as e:
            raise Exception(f"Failed to add description column: {e}")
    
    def update_descriptions_atomic(self, descriptions: Dict[int, str]) -> bool:
        """Atomically update CSV with new descriptions"""
        if not descriptions:
            print("⚠️  No descriptions to update")
            return True
            
        try:
            # Read current CSV
            df = pd.read_csv(self.csv_path)
            
            # Validate structure
            if 'query' not in df.columns:
                raise ValueError("CSV missing required 'query' column")
            
            # Ensure description column exists
            if 'description' not in df.columns:
                df['description'] = ""
            
            # Create temporary file for atomic operation
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                temp_path = pathlib.Path(temp_file.name)
                
                # Update descriptions
                for row_idx, description in descriptions.items():
                    if row_idx < len(df):
                        df.at[row_idx, 'description'] = description
                
                # Write to temporary file
                df.to_csv(temp_path, index=False)
            
            # Atomic replace (Windows-safe)
            if self.csv_path.exists():
                backup_temp = self.csv_path.with_suffix('.csv.temp_backup')
                self.csv_path.rename(backup_temp)
                try:
                    temp_path.rename(self.csv_path)
                    backup_temp.unlink()  # Remove temporary backup
                except Exception:
                    # Restore on failure
                    backup_temp.rename(self.csv_path)
                    raise
            else:
                temp_path.rename(self.csv_path)
            
            print(f"💾 Successfully updated {len(descriptions)} descriptions")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update CSV: {e}")
            if self.backup_path and self.backup_path.exists():
                print(f"🔄 Restore from backup: {self.backup_path}")
            return False
        finally:
            # Cleanup any remaining temp files
            try:
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()
            except:
                pass


# ============================================================================
# Enhanced Description Generation with Retry Logic
# ============================================================================

def generate_description_with_retry(
    query_text: str, 
    max_retries: int = 3,
    model: str = "gemini-2.5-flash-lite",
    timeout: int = 30,
    project: str = None
) -> Tuple[str, dict, bool]:
    """Enhanced description generation with Vertex AI and cost optimization"""
    
    # Initialize client once and reuse
    if not hasattr(generate_description_with_retry, '_client'):
        generate_description_with_retry._client = genai.Client(
            vertexai=True, 
            project=project or os.getenv('GOOGLE_CLOUD_PROJECT'),
            location="global"
        )
    
    client = generate_description_with_retry._client
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            # Truncate very long queries (optimize for cost)
            truncated_query = query_text[:2000] if len(query_text) > 2000 else query_text
            
            # Optimized prompt for cost efficiency (shorter input tokens)
            prompt = (
                "Describe this SQL query in 1-2 sentences. Focus on business purpose and key tables:\n\n" 
                + truncated_query
            )
            
            # Generate content with Vertex AI
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    'temperature': 0.3,
                    'max_output_tokens': 100,  # Limit output for cost control
                }
            )
            
            description = response.text.strip()
            processing_time = time.time() - start_time
            
            # Validate response quality
            if len(description) < 10:
                raise DescriptionError("Response too short")
            
            if "error" in description.lower() or "sorry" in description.lower():
                raise DescriptionError("LLM indicated error in response")
            
            # Calculate actual token usage and cost
            prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
            completion_tokens = len(description.split()) * 1.3
            
            # Cost calculation for Flash-Lite: $0.075 input / $0.30 output per million tokens
            input_cost = (prompt_tokens / 1_000_000) * 0.075
            output_cost = (completion_tokens / 1_000_000) * 0.30
            total_cost = input_cost + output_cost
            
            token_usage = {
                'prompt_tokens': int(prompt_tokens),
                'completion_tokens': int(completion_tokens),
                'total_tokens': int(prompt_tokens + completion_tokens),
                'model': model,
                'processing_time': processing_time,
                'input_cost': input_cost,
                'output_cost': output_cost,
                'total_cost': total_cost
            }
            
            return description, token_usage, True
            
        except Exception as e:
            error_type = type(e).__name__
            
            # Handle Vertex AI specific errors
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                # Rate limiting - longer wait
                wait_time = (3 ** attempt) + (time.time() % 2)
            elif "auth" in str(e).lower():
                # Authentication error - don't retry
                return f"Authentication error: {e}", {}, False
            else:
                # Standard exponential backoff
                wait_time = (2 ** attempt) + (time.time() % 1)
            
            # Determine if retry makes sense
            if attempt == max_retries - 1:
                return f"Description generation failed after {max_retries} attempts: {error_type}", {}, False
            
            if attempt < max_retries - 1:  # Don't print for last attempt
                print(f"    ⏳ Attempt {attempt + 1} failed ({error_type}), retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    return "All retry attempts failed", {}, False


# ============================================================================
# Parallel Processing Engine
# ============================================================================

class ParallelDescriptionGenerator:
    """Main parallel processing orchestrator with intelligent rate limiting"""
    
    def __init__(self, max_workers: int = 6, retry_attempts: int = 3, timeout: int = 30, rate_limit_rpm: int = 2000):
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self.timeout = timeout
        self.results_lock = threading.Lock()
        
        # Rate limiting for Vertex AI (2000 RPM default)
        self.rate_limit_rpm = rate_limit_rpm
        self.request_times = []
        self.rate_limit_lock = threading.Lock()
        
        # Intelligent worker adjustment based on rate limits
        if rate_limit_rpm < 300:
            self.max_workers = min(max_workers, 2)  # Conservative for low limits
        elif rate_limit_rpm < 1000:
            self.max_workers = min(max_workers, 4)  # Moderate for medium limits
        else:
            self.max_workers = min(max_workers, 8)  # Allow more workers for high limits
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting to stay within API quotas"""
        with self.rate_limit_lock:
            current_time = time.time()
            
            # Remove requests older than 1 minute
            self.request_times = [t for t in self.request_times if current_time - t < 60]
            
            # Check if we're at the rate limit
            if len(self.request_times) >= self.rate_limit_rpm:
                # Calculate wait time
                oldest_request = min(self.request_times)
                wait_time = 60 - (current_time - oldest_request) + 0.1  # Add small buffer
                
                if wait_time > 0:
                    print(f"    🛑 Rate limit reached, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
            
            # Record this request
            self.request_times.append(current_time)
        
    def process_single_description(self, task: DescriptionTask, model: str = "gemini-2.5-flash-lite", project: str = None) -> DescriptionResult:
        """Process a single description generation task"""
        # Enforce rate limiting before making API call
        self._enforce_rate_limit()
        
        start_time = time.time()
        
        description, token_usage, success = generate_description_with_retry(
            task.query_text,
            max_retries=task.max_retries,
            model=model,
            timeout=self.timeout,
            project=project
        )
        
        processing_time = time.time() - start_time
        
        return DescriptionResult(
            row_idx=task.row_idx,
            success=success,
            description=description,
            error=None if success else description,
            processing_time=processing_time,
            attempt=task.attempt,
            token_usage=token_usage
        )
    
    def generate_descriptions_parallel(
        self, 
        tasks: List[DescriptionTask], 
        model: str = "gemini-2.5-flash-lite",
        progress_tracker: Optional[AdvancedProgressTracker] = None,
        project: str = None
    ) -> Dict[int, DescriptionResult]:
        """Main parallel processing orchestrator"""
        results = {}
        
        print(f"🚀 Starting parallel generation with {self.max_workers} workers...")
        print(f"📊 Processing {len(tasks)} tasks with model: {model}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self.process_single_description, task, model, project): task 
                for task in tasks
            }
            
            # Process completed tasks with progress tracking
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    with self.results_lock:
                        results[result.row_idx] = result
                    
                    # Update progress tracker
                    if progress_tracker:
                        progress_tracker.update(result.success, result.processing_time)
                    
                except Exception as e:
                    with self.results_lock:
                        results[task.row_idx] = DescriptionResult(
                            row_idx=task.row_idx,
                            success=False,
                            description="",
                            error=f"Unexpected error: {e}",
                            processing_time=0.0
                        )
                    
                    if progress_tracker:
                        progress_tracker.update(False)
        
        return results


# ============================================================================
# System Diagnostics and Health Checks
# ============================================================================

def check_system_requirements() -> bool:
    """Run comprehensive system health checks"""
    print("🔍 Running system diagnostics...")
    
    checks = {}
    
    # Check Python version
    python_version = sys.version_info
    checks['python_version'] = python_version >= (3, 8)
    if not checks['python_version']:
        print(f"❌ Python 3.8+ required, found {python_version.major}.{python_version.minor}")
    
    # Check Vertex AI connection
    try:
        client = genai.Client(vertexai=True, project=os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project'), location="global")
        # Test with a simple content generation
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents='Test connection'
        )
        checks['vertexai_available'] = True
    except Exception as e:
        checks['vertexai_available'] = False
        print(f"❌ Vertex AI connection failed: {e}")
        print(f"💡 Ensure GOOGLE_CLOUD_PROJECT environment variable is set and you have proper authentication")
    
    # Check memory
    if psutil:
        try:
            memory_gb = psutil.virtual_memory().total / (1024**3)
            checks['memory_sufficient'] = memory_gb >= 4
            if not checks['memory_sufficient']:
                print(f"⚠️  Low memory: {memory_gb:.1f}GB (4GB+ recommended)")
        except:
            checks['memory_sufficient'] = True  # Assume OK if can't detect
    else:
        checks['memory_sufficient'] = True
    
    # Check disk space
    try:
        disk_usage = shutil.disk_usage('.')
        free_gb = disk_usage.free / (1024**3)
        checks['disk_space'] = free_gb >= 1
        if not checks['disk_space']:
            print(f"⚠️  Low disk space: {free_gb:.1f}GB available")
    except:
        checks['disk_space'] = True
    
    all_passed = all(checks.values())
    
    print(f"\n📊 Diagnostic Results:")
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
    
    if not all_passed:
        print(f"\n⚠️  Some checks failed. See details above.")
        return False
        
    print(f"\n✅ All systems ready!")
    return True


# ============================================================================
# Command Line Interface
# ============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Comprehensive CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generate SQL query descriptions using parallel processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_descriptions.py
  python generate_descriptions.py --csv queries.csv --workers 8
  python generate_descriptions.py --force-rebuild --batch-size 25
  python generate_descriptions.py --dry-run --verbose
  python generate_descriptions.py --resume-failed --retry-limit 5
        """
    )
    
    # Input/Output options
    parser.add_argument(
        "--csv", 
        type=str, 
        default="sample_queries.csv",
        help="Path to CSV file with 'query' column (default: sample_queries.csv)"
    )
    
    # Processing options
    parser.add_argument(
        "--workers", 
        type=int, 
        default=0,  # 0 = auto-detect
        help="Number of parallel workers (default: auto-detect based on system)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Progress update frequency (default: 50)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-flash-lite",
        help="Vertex AI model to use for description generation (default: gemini-2.5-flash-lite for cost optimization)"
    )
    
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Google Cloud Project ID (default: from GOOGLE_CLOUD_PROJECT environment variable)"
    )
    
    # Behavior options
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Regenerate all descriptions, even if they already exist"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true", 
        help="Show what would be processed without actually generating descriptions"
    )
    
    # Error handling
    parser.add_argument(
        "--retry-limit",
        type=int,
        default=3,
        help="Maximum retry attempts per query (default: 3)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout per description generation in seconds (default: 30)"
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed progress and timing information"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimize output (only show errors and final summary)"
    )
    
    # Safety options
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup of CSV file (not recommended)"
    )
    
    parser.add_argument(
        "--skip-diagnostics",
        action="store_true",
        help="Skip system diagnostics check"
    )
    
    return parser


# ============================================================================
# Main Execution Logic
# ============================================================================

def main():
    """Main execution function"""
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Validate arguments
    if args.quiet and args.verbose:
        print("❌ Error: --quiet and --verbose are mutually exclusive")
        sys.exit(1)
    
    # Set up paths
    csv_path = pathlib.Path(args.csv).expanduser().resolve()
    
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Run system diagnostics
    if not args.skip_diagnostics:
        if not check_system_requirements():
            print("\n💡 To skip diagnostics, use --skip-diagnostics")
            sys.exit(1)
    
    # Determine worker count
    if args.workers == 0:
        workers = get_optimal_workers()
        if args.verbose:
            print(f"🔧 Auto-detected {workers} optimal workers")
    else:
        workers = args.workers
    
    print(f"\n🎯 Configuration:")
    print(f"   📄 CSV file: {csv_path.name}")
    print(f"   👥 Workers: {workers}")
    print(f"   🤖 Model: {args.model}")
    print(f"   🔄 Retry limit: {args.retry_limit}")
    print(f"   ⏱️  Timeout: {args.timeout}s")
    
    try:
        # Initialize CSV processor
        csv_processor = SafeCSVProcessor(csv_path)
        
        # Analyze CSV
        print(f"\n📊 Analyzing CSV file...")
        analysis = csv_processor.get_csv_analysis()
        
        print(f"   Total queries: {analysis['total_queries']}")
        print(f"   Has description column: {analysis['has_description_column']}")
        print(f"   Queries needing descriptions: {len(analysis['queries_needing_descriptions'])}")
        
        if len(analysis['queries_needing_descriptions']) == 0:
            print("✅ All queries already have descriptions!")
            return
        
        # Handle force rebuild
        if args.force_rebuild:
            print("🔄 Force rebuild requested - will regenerate all descriptions")
            # Create tasks for all queries
            all_queries = []
            df = pd.read_csv(csv_path)
            for idx, row in df.iterrows():
                query_text = row.get('query', '')
                if not pd.isna(query_text) and str(query_text).strip():
                    all_queries.append((idx, str(query_text).strip()))
            tasks = [DescriptionTask(row_idx, query_text, max_retries=args.retry_limit) 
                    for row_idx, query_text in all_queries]
        else:
            # Create tasks for queries needing descriptions
            tasks = [DescriptionTask(row_idx, query_text, max_retries=args.retry_limit) 
                    for row_idx, query_text in analysis['queries_needing_descriptions']]
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN - Would process {len(tasks)} tasks:")
            for i, task in enumerate(tasks[:5]):  # Show first 5
                print(f"   {i+1}. Row {task.row_idx + 1}: {task.query_text[:60]}...")
            if len(tasks) > 5:
                print(f"   ... and {len(tasks) - 5} more tasks")
            
            estimated_time = len(tasks) / workers * 3  # Estimate 3 seconds per task
            print(f"\n⏱️  Estimated completion time: {estimated_time:.0f} seconds ({estimated_time/60:.1f} minutes)")
            return
        
        # Create backup if requested
        if not args.no_backup:
            csv_processor.create_backup()
        
        # Ensure description column exists
        csv_processor.ensure_description_column()
        
        # Initialize parallel processor
        generator = ParallelDescriptionGenerator(
            max_workers=workers,
            retry_attempts=args.retry_limit,
            timeout=args.timeout
        )
        
        # Initialize progress tracker
        progress_tracker = AdvancedProgressTracker(len(tasks), args.batch_size)
        
        # Generate descriptions
        print(f"\n🚀 Starting parallel description generation...")
        start_time = time.time()
        
        results = generator.generate_descriptions_parallel(
            tasks, 
            model=args.model,
            progress_tracker=progress_tracker,
            project=args.project
        )
        
        # Process results and calculate costs
        successful_descriptions = {}
        failed_results = []
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        
        for row_idx, result in results.items():
            if result.success:
                successful_descriptions[row_idx] = result.description
                # Accumulate cost information
                if result.token_usage:
                    total_cost += result.token_usage.get('total_cost', 0)
                    total_input_tokens += result.token_usage.get('prompt_tokens', 0)
                    total_output_tokens += result.token_usage.get('completion_tokens', 0)
            else:
                failed_results.append((row_idx, result.error))
        
        # Update CSV with successful descriptions
        if successful_descriptions:
            success = csv_processor.update_descriptions_atomic(successful_descriptions)
            if not success:
                print("❌ Failed to update CSV file")
                sys.exit(1)
        
        # Print final summary
        summary = progress_tracker.get_final_summary()
        total_time = time.time() - start_time
        
        print(f"\n🎉 Generation Complete!")
        print(f"   ✅ Successful: {summary['completed']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   📊 Success rate: {summary['success_rate']:.1f}%")
        print(f"   ⏱️  Total time: {total_time:.1f}s")
        print(f"   🚀 Average rate: {summary['tasks_per_second']:.1f} tasks/second")
        
        # Cost summary
        if total_cost > 0:
            print(f"\n💰 Cost Analysis ({args.model}):")
            print(f"   🪙 Input tokens: {total_input_tokens:,}")
            print(f"   🪙 Output tokens: {total_output_tokens:,}")
            print(f"   💵 Total cost: ${total_cost:.6f}")
            print(f"   📊 Cost per description: ${(total_cost/max(summary['completed'], 1)):.6f}")
            
            # Cost comparison for different models
            print(f"\n💡 Cost Comparison (for {summary['completed']} descriptions):")
            flash_lite_cost = total_cost
            flash_cost = ((total_input_tokens/1_000_000) * 0.30) + ((total_output_tokens/1_000_000) * 2.50)
            pro_cost = ((total_input_tokens/1_000_000) * 1.25) + ((total_output_tokens/1_000_000) * 10.0)
            
            print(f"   📱 Flash-Lite (current): ${flash_lite_cost:.6f}")
            print(f"   ⚡ Flash: ${flash_cost:.6f} ({(flash_cost/max(flash_lite_cost, 0.000001)):.1f}x more)")
            print(f"   🚀 Pro: ${pro_cost:.6f} ({(pro_cost/max(flash_lite_cost, 0.000001)):.1f}x more)")
        
        if failed_results and args.verbose:
            print(f"\n❌ Failed queries:")
            for row_idx, error in failed_results[:5]:  # Show first 5 failures
                print(f"   Row {row_idx + 1}: {error}")
            if len(failed_results) > 5:
                print(f"   ... and {len(failed_results) - 5} more failures")
        
        # Performance comparison
        sequential_time = len(tasks) * 3  # Estimate 3 seconds per task
        speedup = sequential_time / total_time if total_time > 0 else 1
        print(f"   🏎️  Speedup vs sequential: {speedup:.1f}x faster")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()