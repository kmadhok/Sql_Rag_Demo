# settings.py
"""
Central configuration for the SQL-RAG toolkit.

Import it like:
    from settings import DEFAULT_CATALOG_FILE, SELECT_RE, …

You can freely extend this file with more flags, API keys, logging levels, etc.
"""

from __future__ import annotations
import re
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Paths / project helper
# ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent

# When *not* searching across git branches, SQLExtractor starts its recursive
# scan from whatever directory the caller passes, default ".".
# (So PROJECT_ROOT is purely a convenience if you want an absolute base path.)
# Example usage:
#     extractor = SQLExtractor(root_dir=PROJECT_ROOT / "src" / "queries")

# ─────────────────────────────────────────────────────────────
# File / folder patterns to skip
# ─────────────────────────────────────────────────────────────
VENV_PATTERNS: list[str] = [
    ".env",
    "yaml_env",
    "sql_formatter",
    "read_pdf",
    "venv",
    "env",
    ".venv",
    "virtualenv",
    ".virtualenv",
    "__pycache__",
]

# ─────────────────────────────────────────────────────────────
# Regexes to detect SQL blocks
# ─────────────────────────────────────────────────────────────
TRIPLE_QUOTE_RE = re.compile(r'"""(.*?)"""', re.DOTALL)
SELECT_RE       = re.compile(r"\bselect\b", re.IGNORECASE)
FROM_RE         = re.compile(r"\bfrom\b",   re.IGNORECASE)

# ─────────────────────────────────────────────────────────────
# Console-noise markers from Ollama (used for cleanup)
# ─────────────────────────────────────────────────────────────
JUNK_PATTERN        = r"failed to get console mode for stderr: The handle is invalid\."
STDOUT_CONSOLE_MSG  = "failed to get console mode for stdout: The handle is invalid."
STDERR_CONSOLE_MSG  = "failed to get console mode for stderr: The handle is invalid."

# ─────────────────────────────────────────────────────────────
# Default filenames produced by the pipeline
# ─────────────────────────────────────────────────────────────
DEFAULT_CATALOG_FILE = "sql_catalog_combined.md"
DEFAULT_FIXED_FILE   = "sql_catalog_combined_fixed.md"
DEFAULT_JSON_FILE    = "sql_catalog_combined_descriptions.json"

# ─────────────────────────────────────────────────────────────
# Ollama model / run-time settings
# ─────────────────────────────────────────────────────────────
DEFAULT_MODEL    = "qwen2.5-coder:3b"   # change to whatever model tag you like
OLLAMA_TIMEOUT   = 45                   # seconds allowed for each ollama call
MAX_QUERY_LENGTH = 1_000                # characters to keep when truncating
