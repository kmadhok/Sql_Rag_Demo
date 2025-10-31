#!/usr/bin/env python3
"""
Persistent storage for generated SQL queries and their results.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).parent.parent / "saved_queries"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SavedQuery:
    id: str
    question: str
    sql: str
    created_at: str
    data_preview: List[Dict]
    row_count: int

    @property
    def filename(self) -> Path:
        return STORAGE_DIR / f"{self.id}.json"


def _write_json(path: Path, payload: Dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def save_query(question: str, sql: str, data: Optional[List[Dict]] = None) -> SavedQuery:
    """
    Persist a generated SQL query and optional data preview to disk.
    """
    query_id = uuid4().hex
    created_at = datetime.utcnow().isoformat() + "Z"
    preview = (data or [])[:50]
    saved = SavedQuery(
        id=query_id,
        question=question,
        sql=sql,
        created_at=created_at,
        data_preview=preview,
        row_count=len(data or []),
    )
    _write_json(saved.filename, asdict(saved))
    logger.info("Saved query %s", saved.id)
    return saved


def list_saved_queries() -> List[SavedQuery]:
    """
    Return metadata for all saved queries (sorted by newest first).
    """
    queries: List[SavedQuery] = []
    for path in STORAGE_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text())
            queries.append(SavedQuery(**payload))
        except Exception as exc:
            logger.warning("Could not read saved query %s: %s", path, exc)
    queries.sort(key=lambda q: q.created_at, reverse=True)
    return queries


def load_saved_query(query_id: str) -> Optional[SavedQuery]:
    path = STORAGE_DIR / f"{query_id}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
        return SavedQuery(**payload)
    except Exception as exc:
        logger.error("Failed to load saved query %s: %s", query_id, exc)
        return None
