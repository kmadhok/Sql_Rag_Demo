#!/usr/bin/env python3
"""
OpenRouter client with the same interface as GeminiClient
(invoke, invoke_structured, test_connection, get_model_info).

OpenRouter exposes an OpenAI-compatible API, so any model it serves
(e.g. "google/gemini-2.5-pro", "anthropic/claude-sonnet-5") can be used
by changing a model slug.

Environment variables:
- OPENROUTER_API_KEY  (required)
- OPENROUTER_BASE_URL (optional, defaults to https://openrouter.ai/api/v1)
"""

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Attribution headers OpenRouter uses for its app rankings; harmless if unused.
APP_HEADERS = {"HTTP-Referer": "https://kanumadhok.com/sql-rag", "X-Title": "SQL RAG Demo"}
MAX_RETRIES = 3
RETRY_DELAY = 2.0


def get_openrouter_api_key() -> Optional[str]:
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key
    try:
        from dotenv import find_dotenv, load_dotenv
        env_path = find_dotenv(usecwd=True)
        if env_path:
            load_dotenv(env_path, override=False)
    except Exception as e:
        logger.debug(f"dotenv not loaded: {e}")
    return os.getenv("OPENROUTER_API_KEY")


def get_openrouter_base_url() -> str:
    return os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL)


def _to_response_format(response_schema: Any) -> Dict[str, Any]:
    """Translate a Pydantic class or JSON-schema dict into an OpenAI response_format."""
    if response_schema is None:
        return {"type": "json_object"}
    if isinstance(response_schema, dict):
        schema, name = response_schema, "response"
    elif hasattr(response_schema, "model_json_schema"):
        schema, name = response_schema.model_json_schema(), response_schema.__name__
    else:
        return {"type": "json_object"}
    return {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": False}}


class OpenRouterClient:
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        client: Optional[Any] = None,
    ):
        self.model_name = model
        self.api_key = api_key or get_openrouter_api_key()
        if not self.api_key and client is None:
            raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = client or OpenAI(
            api_key=self.api_key,
            base_url=get_openrouter_base_url(),
            default_headers=APP_HEADERS,
            timeout=120,
        )
        self._initialized = True

    def _complete(self, prompt: str, **kwargs: Any) -> str:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs,
                )
                text = response.choices[0].message.content if response.choices else None
                if not text or not text.strip():
                    raise ValueError(f"Empty response from {self.model_name}")
                return text.strip()
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
                    raise

    def invoke(self, prompt: str) -> str:
        return self._complete(prompt)

    def invoke_structured(
        self,
        prompt: str,
        response_format: str = "json",
        response_schema: Optional[Any] = None,
    ) -> str:
        if response_format != "json":
            return self._complete(prompt)
        return self._complete(prompt, response_format=_to_response_format(response_schema))

    def test_connection(self) -> Tuple[bool, str]:
        try:
            start = time.time()
            reply = self._complete("Reply with the single word: ok")
            return True, f"✅ {self.model_name} ready ({time.time() - start:.2f}s response time, reply={reply[:20]!r})"
        except Exception as e:
            return False, f"❌ OpenRouter error for {self.model_name}: {e}"

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "provider": "OpenRouter",
            "api_key_set": bool(self.api_key),
            "initialized": self._initialized,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
        }

    def __repr__(self) -> str:
        return f"OpenRouterClient(model='{self.model_name}', api_key_set={bool(self.api_key)})"
