import asyncio
import time
import random
from collections import deque
from typing import Optional, Dict, Any
import logging

class RateLimiter:
    """
    Rate limiter for Vertex AI Gemini API to prevent 429 errors.
    
    Tracks requests per minute and implements adaptive concurrency
    with exponential backoff for rate limit violations.
    """
    
    def __init__(self, 
                 requests_per_minute: int = 15,
                 tokens_per_minute: int = 250000,
                 requests_per_day: int = 1000,
                 initial_concurrency: int = 2):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.requests_per_day = requests_per_day
        self.current_concurrency = initial_concurrency
        self.max_concurrency = initial_concurrency
        
        # Track request timestamps for RPM calculation
        self.request_times = deque()
        self.daily_requests = 0
        self.daily_reset_time = time.time() + 86400  # 24 hours from now
        
        # Token tracking
        self.token_usage = deque()
        self.total_tokens_used = 0
        
        # Adaptive concurrency
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        
        # Rate limit violation tracking
        self.last_rate_limit_time = 0
        self.rate_limit_backoff = 1.0
        
        # Progress tracking
        self.total_processed = 0
        self.total_errors = 0
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _cleanup_old_requests(self):
        """Remove request timestamps older than 1 minute."""
        current_time = time.time()
        while self.request_times and current_time - self.request_times[0] > 60:
            self.request_times.popleft()
    
    def _cleanup_old_tokens(self):
        """Remove token usage older than 1 minute."""
        current_time = time.time()
        while self.token_usage and current_time - self.token_usage[0][0] > 60:
            _, tokens = self.token_usage.popleft()
            self.total_tokens_used -= tokens
    
    def _reset_daily_counter(self):
        """Reset daily request counter if needed."""
        if time.time() > self.daily_reset_time:
            self.daily_requests = 0
            self.daily_reset_time = time.time() + 86400
    
    def can_make_request(self, estimated_tokens: int = 1000) -> bool:
        """
        Check if we can make a request without violating rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            True if request can be made, False otherwise
        """
        self._cleanup_old_requests()
        self._cleanup_old_tokens()
        self._reset_daily_counter()
        
        current_time = time.time()
        
        # Check if we're still in backoff period
        if current_time - self.last_rate_limit_time < self.rate_limit_backoff:
            return False
        
        # Check RPM limit
        if len(self.request_times) >= self.requests_per_minute:
            return False
        
        # Check daily limit
        if self.daily_requests >= self.requests_per_day:
            return False
        
        # Check token limit
        if self.total_tokens_used + estimated_tokens > self.tokens_per_minute:
            return False
        
        return True
    
    def record_request(self, tokens_used: int = 0):
        """Record a successful request."""
        current_time = time.time()
        self.request_times.append(current_time)
        self.daily_requests += 1
        
        if tokens_used > 0:
            self.token_usage.append((current_time, tokens_used))
            self.total_tokens_used += tokens_used
        
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.total_processed += 1
        
        # Adaptive concurrency - increase on success
        if self.consecutive_successes >= 5 and self.current_concurrency < self.max_concurrency:
            self.current_concurrency = min(self.current_concurrency + 1, self.max_concurrency)
            self.consecutive_successes = 0
    
    def record_rate_limit_violation(self):
        """Record a 429 rate limit violation."""
        current_time = time.time()
        self.last_rate_limit_time = current_time
        self.consecutive_failures += 1
        self.total_errors += 1
        
        # Exponential backoff with jitter
        self.rate_limit_backoff = min(60.0, self.rate_limit_backoff * 2) + random.uniform(0, 1)
        
        # Adaptive concurrency - decrease on failure
        if self.consecutive_failures >= 2:
            self.current_concurrency = max(1, self.current_concurrency - 1)
            self.consecutive_failures = 0
        
        self.logger.warning(f"Rate limit hit. Backing off for {self.rate_limit_backoff:.1f}s. "
                          f"Concurrency reduced to {self.current_concurrency}")
    
    def record_error(self, error: Exception):
        """Record a general error."""
        self.total_errors += 1
        self.logger.error(f"API error: {str(error)}")
    
    async def wait_for_availability(self, estimated_tokens: int = 1000, max_wait: float = 300):
        """
        Wait until a request can be made without violating rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if ready to make request, False if max_wait exceeded
        """
        start_time = time.time()
        
        while not self.can_make_request(estimated_tokens):
            if time.time() - start_time > max_wait:
                return False
            
            # Calculate wait time based on what's limiting us
            wait_time = self._calculate_wait_time()
            self.logger.info(f"Rate limited. Waiting {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)
        
        return True
    
    def _calculate_wait_time(self) -> float:
        """Calculate optimal wait time based on current limits."""
        current_time = time.time()
        
        # If in backoff period, wait for that
        backoff_wait = max(0, self.rate_limit_backoff - (current_time - self.last_rate_limit_time))
        if backoff_wait > 0:
            return backoff_wait
        
        # If RPM limited, wait until oldest request expires
        if len(self.request_times) >= self.requests_per_minute:
            return max(1.0, 61 - (current_time - self.request_times[0]))
        
        # If token limited, wait for token window to reset
        if self.total_tokens_used >= self.tokens_per_minute * 0.9:  # 90% threshold
            return max(1.0, 30.0)  # Conservative wait
        
        # Default minimal wait
        return 1.0
    
    def get_current_concurrency(self) -> int:
        """Get the current recommended concurrency level."""
        return self.current_concurrency
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        self._cleanup_old_requests()
        self._cleanup_old_tokens()
        
        return {
            "requests_last_minute": len(self.request_times),
            "tokens_last_minute": self.total_tokens_used,
            "daily_requests": self.daily_requests,
            "current_concurrency": self.current_concurrency,
            "total_processed": self.total_processed,
            "total_errors": self.total_errors,
            "success_rate": (self.total_processed / (self.total_processed + self.total_errors)) * 100 
                          if (self.total_processed + self.total_errors) > 0 else 0,
            "backoff_time_remaining": max(0, self.rate_limit_backoff - 
                                        (time.time() - self.last_rate_limit_time))
        }


def exponential_backoff_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for exponential backoff retry on API calls.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for first retry
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Only retry on specific rate limit errors
                    if "429" in error_str or "resource exhausted" in error_str or "quota" in error_str:
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            logging.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s due to: {e}")
                            await asyncio.sleep(delay)
                            continue
                    
                    # Don't retry for other errors
                    raise e
            
            # If we've exhausted retries, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


# Global rate limiter instance for Gemini 2.5 Flash-Lite free tier
# Can be configured for different tiers
GEMINI_RATE_LIMITER = RateLimiter(
    requests_per_minute=15,     # Free tier limit
    tokens_per_minute=250000,   # Free tier limit  
    requests_per_day=1000,      # Free tier limit
    initial_concurrency=2       # Conservative starting point
)