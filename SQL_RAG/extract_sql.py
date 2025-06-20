# sql_catalog.py
"""
End-to-end SQL catalogue + (optional) description generator.

Refactored for clarity, but preserves original behaviour.
Now supports **root_dir** → choose where the scan starts when you are
NOT hopping across git branches.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from settings import (  # all constants live here
    DEFAULT_CATALOG_FILE,
    DEFAULT_MODEL,
    MAX_QUERY_LENGTH,
    OLLAMA_TIMEOUT,
    SELECT_RE,
    FROM_RE,
    TRIPLE_QUOTE_RE,
    VENV_PATTERNS,
    STDERR_CONSOLE_MSG,
    STDOUT_CONSOLE_MSG,
)

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


# ──────────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class QueryEntry:
    path: Path
    sql: str
    branch: str = "current"

    @property
    def filename(self) -> str:
        return self.path.name


# ──────────────────────────────────────────────────────────────────────────────
# Git helpers
# ──────────────────────────────────────────────────────────────────────────────
def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Thin wrapper around subprocess.run with sane defaults."""
    return subprocess.run(cmd, capture_output=True, text=True, check=True, **kw)


def current_branch() -> str | None:
    try:
        return _run(["git", "branch", "--show-current"]).stdout.strip() or None
    except Exception:
        LOG.warning("Not inside a git repository (or git missing).")
        return None


def list_remote_branches() -> list[str]:
    try:
        raw = _run(["git", "branch", "-r"]).stdout.splitlines()
        return [
            b.strip().replace("origin/", "")
            for b in raw
            if b.strip() and not b.startswith("origin/HEAD")
        ]
    except Exception as exc:
        LOG.error("Failed to list branches: %s", exc)
        return []


@contextmanager
def checkout(branch: str):
    """Temporarily check out *branch*, restoring the original no-matter-what."""
    orig = current_branch()
    if branch and branch != orig:
        try:
            _run(["git", "checkout", branch])
            LOG.info("→ switched to branch %s", branch)
            yield
        finally:
            if orig:
                _run(["git", "checkout", orig])
                LOG.info("→ restored branch %s", orig)
    else:
        yield


# ──────────────────────────────────────────────────────────────────────────────
# 1. SQL extraction
# ──────────────────────────────────────────────────────────────────────────────
class SQLExtractor:
    """
    Parameters
    ----------
    include_git_branches : bool
        If True, scans each branch in `branches` (or all remote branches)
        by checking them out one at a time. `root_dir` is ignored.
    branches : Iterable[str] | None
        List of branch names to search. Ignored if `include_git_branches` False.
    root_dir : str | Path
        Directory from which to start the recursive scan **when staying on the
        current branch**. Default = current working directory.
    """

    def __init__(
        self,
        include_git_branches: bool = False,
        branches: Iterable[str] | None = None,
        root_dir: str | Path = ".",
    ):
        self.include_git_branches = include_git_branches
        self.branches = list(branches or [])
        self.root_dir = Path(root_dir).expanduser().resolve()

    # ---------- public API ----------------------------------------------------
    def scrape(self, output: Path = Path(DEFAULT_CATALOG_FILE)) -> Path:
        LOG.info("Scanning files …")
        entries: list[QueryEntry] = []

        if not self.include_git_branches:
            entries.extend(self._scrape_branch("current"))
        else:
            targets = self.branches or list_remote_branches() or ["current"]
            LOG.info("Searching across %d branch(es).", len(targets))
            for br in targets:
                with checkout(br):
                    entries.extend(self._scrape_branch(br))

        self._write_markdown(entries, output)
        return output

    # ---------- internals -----------------------------------------------------
    def _scrape_branch(self, branch_name: str) -> list[QueryEntry]:
        # Decide base directory:
        # • when hopping branches we scan the repo root (`.`) after checkout
        # • otherwise we honour the user-supplied root_dir
        base_dir = Path(".") if self.include_git_branches else self.root_dir

        out: list[QueryEntry] = []
        sql_paths = list(base_dir.rglob("*.sql"))
        py_paths = [
            p
            for p in base_dir.rglob("*.py")
            if not any(vpat in str(p) for vpat in VENV_PATTERNS)
        ]

        LOG.debug(
            "[%s] %s .sql, %s .py found under %s",
            branch_name,
            len(sql_paths),
            len(py_paths),
            base_dir,
        )

        # .sql files (whole file = one query)
        for p in sql_paths:
            try:
                out.append(QueryEntry(p, p.read_text(encoding="utf-8"), branch_name))
            except Exception as exc:
                LOG.error("[%s] reading %s failed: %s", branch_name, p, exc)

        # .py files (extract quoted SQL blocks)
        for p in py_paths:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                LOG.error("[%s] reading %s failed: %s", branch_name, p, exc)
                continue

            for block in self._sql_blocks(content):
                out.append(QueryEntry(p, block, branch_name))

        return out

    @staticmethod
    def _sql_blocks(code: str) -> List[str]:
        """Return all triple-quoted strings that look like SQL."""
        return [
            m.group(1).strip()
            for m in TRIPLE_QUOTE_RE.finditer(code)
            if SELECT_RE.search(m.group(1)) and FROM_RE.search(m.group(1))
        ]

    # ---------- markdown ------------------------------------------------------
    @staticmethod
    def _write_markdown(entries: list[QueryEntry], dest: Path):
        LOG.info("Writing %s SQL queries → %s", len(entries), dest)

        with dest.open("w", encoding="utf-8") as md:
            md.write("# SQL Query Catalog\n\n")
            group: dict[str, list[QueryEntry]] = {}
            for e in entries:
                group.setdefault(e.branch, []).append(e)

            counter = 1
            for branch, sub in group.items():
                multi = len(group) > 1
                if multi:
                    md.write(f"## Branch: {branch}\n\n")
                for q in sub:
                    md.write(f"### Query #{counter} – {q.filename}\n\n")
                    md.write(f"**File:** {q.path}\n\n")
                    if multi:
                        md.write(f"**Branch:** {q.branch}\n\n")
                    md.write("```sql\n")
                    md.write(q.sql.strip())
                    md.write("\n```\n\n---\n\n")
                    counter += 1


# ──────────────────────────────────────────────────────────────────────────────
# 2. Natural-language descriptions via Ollama (optional)
# ──────────────────────────────────────────────────────────────────────────────
class DescriptionGenerator:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        if not self._ollama_ok():
            raise RuntimeError("Ollama unavailable or not working.")

    @staticmethod
    def _ollama_ok() -> bool:
        try:
            return _run(["ollama", "list"]).returncode == 0
        except Exception as exc:
            LOG.error("Ollama check failed: %s", exc)
            return False

    # public ------------------------------------------------------------------
    def describe(self, query: str, retries: int = 3) -> str:
        prompt = (
            "Please describe this SQL query in 2–3 sentences of plain English.\n\n"
            "```sql\n"
            f"{query[:MAX_QUERY_LENGTH]}{'...' if len(query) > MAX_QUERY_LENGTH else ''}\n"
            "```"
        )
        for attempt in range(retries):
            try:
                result = _run(
                    ["ollama", "run", self.model, prompt],
                    timeout=OLLAMA_TIMEOUT,
                ).stdout.strip()
                return self._clean(result)
            except subprocess.TimeoutExpired:
                LOG.warning("Ollama timeout, attempt %d/%d", attempt + 1, retries)
                time.sleep(2)
            except subprocess.CalledProcessError as exc:
                LOG.warning("Ollama error: %s", exc)
                time.sleep(2)
        return "⚠️ description generation failed"

    # internals ---------------------------------------------------------------
    @staticmethod
    def _clean(text: str) -> str:
        # remove console wrappers
        for tag in (STDOUT_CONSOLE_MSG, STDERR_CONSOLE_MSG):
            if text.startswith(tag):
                text = text[len(tag) :].lstrip()
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = text.split("Description:", 1)[-1]
        return " ".join(text.split())


# ──────────────────────────────────────────────────────────────────────────────
# 3. Markdown post-processing
# ──────────────────────────────────────────────────────────────────────────────
class MarkdownProcessor:
    QUERY_HEADER_RE = re.compile(
        r"## Query #(?P<idx>\d+) – (?P<fname>.*?)\n\n\*\*File:\*\* (?P<path>.*?)\n",
        flags=re.DOTALL,
    )

    @staticmethod
    def to_latin1(src: Path) -> Path:
        dst = src.with_name(src.stem + "_latin1.md")
        LOG.info("Fixing encoding → %s", dst)
        dst.write_bytes(src.read_bytes())  # byte-for-byte copy
        return dst

    # -------------------------------------------------------------------------
    def add_descriptions(self, md_file: Path, generator: DescriptionGenerator) -> Path:
        text = md_file.read_text(encoding="latin-1")
        queries = list(self.QUERY_HEADER_RE.finditer(text))
        LOG.info("Generating descriptions for %d queries …", len(queries))

        for m in queries:
            idx, fname, path = m["idx"], m["fname"], m["path"]
            # pull full SQL block that follows this header
            sql_block = re.search(
                rf"{re.escape(m.group(0))}.*?```sql\n(.*?)\n```", text, re.DOTALL
            )[1]
            description = generator.describe(sql_block)
            injection = (
                f"## Query #{idx} – {fname}\n\n**File:** {path}"
                f"\n\n**Description:** {description}\n\n```sql"
            )
            text = text.replace(m.group(0), injection, 1)

        out = md_file.with_name(md_file.stem + "_with_descriptions.md")
        out.write_text(text, encoding="utf-8")
        LOG.info("Markdown enriched → %s", out)

        # dump a JSON side-car
        (out.with_suffix(".json")).write_text(
            json.dumps(
                [
                    dict(index=int(m["idx"]), file=m["path"], description="…")
                    for m in queries
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        return out


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────────────
def main():
    LOG.info("=== SQL catalogue pipeline ===")

    # Example: stay on current branch but only scan ./src/sql_reports
    # extractor = SQLExtractor(root_dir="src/sql_reports")

    extractor = SQLExtractor()  # default: scan entire cwd only
    catalog = extractor.scrape()

    processor = MarkdownProcessor()
    fixed = processor.to_latin1(catalog)

    # Uncomment if you want automatic descriptions via Ollama
    # generator = DescriptionGenerator()
    # enriched = processor.add_descriptions(fixed, generator)
    # LOG.info("✓ Finished. Next: run 'python sql_query_rag.py' on %s", enriched)

    LOG.info("✓ Finished. Catalog written to %s", fixed)


if __name__ == "__main__":
    main()
