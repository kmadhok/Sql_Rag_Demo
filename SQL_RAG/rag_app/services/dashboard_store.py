#!/usr/bin/env python3
"""
Persistent storage for dashboard layouts and chart configurations.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).parent.parent / "dashboards"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ChartConfig:
    """Configuration for a single chart visualization."""
    chart_type: str  # "bar", "column", "line", "pie", etc.
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    aggregation: str = "count"  # "count", "sum", "avg", "min", "max"


@dataclass
class LayoutItem:
    """A single chart card in the dashboard grid."""
    i: str  # Unique item ID (required by react-grid-layout)
    x: int  # Grid column position (0-11 for 12-column grid)
    y: int  # Grid row position
    w: int  # Width in grid columns (1-12)
    h: int  # Height in grid rows
    saved_query_id: str  # Reference to saved query
    chart_config: ChartConfig


@dataclass
class Dashboard:
    """A complete dashboard with layout and chart configurations."""
    id: str
    name: str
    created_at: str
    updated_at: str
    layout_items: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def filename(self) -> Path:
        return STORAGE_DIR / f"{self.id}.json"


def _write_json(path: Path, payload: Dict) -> None:
    """Atomically write JSON to disk."""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def create_dashboard(name: str, layout_items: Optional[List[Dict[str, Any]]] = None) -> Dashboard:
    """
    Create and persist a new dashboard.
    """
    dashboard_id = uuid4().hex
    now = datetime.utcnow().isoformat() + "Z"

    dashboard = Dashboard(
        id=dashboard_id,
        name=name,
        created_at=now,
        updated_at=now,
        layout_items=layout_items or [],
    )

    _write_json(dashboard.filename, asdict(dashboard))
    logger.info("Created dashboard %s: %s", dashboard.id, dashboard.name)
    return dashboard


def update_dashboard(
    dashboard_id: str,
    name: Optional[str] = None,
    layout_items: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dashboard]:
    """
    Update an existing dashboard's name or layout.
    """
    dashboard = load_dashboard(dashboard_id)
    if not dashboard:
        logger.warning("Dashboard %s not found for update", dashboard_id)
        return None

    if name is not None:
        dashboard.name = name
    if layout_items is not None:
        dashboard.layout_items = layout_items

    dashboard.updated_at = datetime.utcnow().isoformat() + "Z"

    _write_json(dashboard.filename, asdict(dashboard))
    logger.info("Updated dashboard %s", dashboard_id)
    return dashboard


def list_dashboards() -> List[Dashboard]:
    """
    Return all dashboards (sorted by most recently updated first).
    """
    dashboards: List[Dashboard] = []
    for path in STORAGE_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text())
            dashboards.append(Dashboard(**payload))
        except Exception as exc:
            logger.warning("Could not read dashboard %s: %s", path, exc)

    dashboards.sort(key=lambda d: d.updated_at, reverse=True)
    return dashboards


def load_dashboard(dashboard_id: str) -> Optional[Dashboard]:
    """
    Load a specific dashboard by ID.
    """
    path = STORAGE_DIR / f"{dashboard_id}.json"
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text())
        return Dashboard(**payload)
    except Exception as exc:
        logger.error("Failed to load dashboard %s: %s", dashboard_id, exc)
        return None


def duplicate_dashboard(dashboard_id: str) -> Optional[Dashboard]:
    """
    Duplicate an existing dashboard with a new ID and name.
    """
    original = load_dashboard(dashboard_id)
    if not original:
        logger.warning("Dashboard %s not found for duplication", dashboard_id)
        return None

    # Create new dashboard with copied layout items
    new_dashboard_id = uuid4().hex
    now = datetime.utcnow().isoformat() + "Z"

    duplicated = Dashboard(
        id=new_dashboard_id,
        name=f"{original.name} (Copy)",
        created_at=now,
        updated_at=now,
        layout_items=original.layout_items.copy(),
    )

    _write_json(duplicated.filename, asdict(duplicated))
    logger.info("Duplicated dashboard %s to %s", dashboard_id, new_dashboard_id)
    return duplicated


def delete_dashboard(dashboard_id: str) -> bool:
    """
    Delete a dashboard by ID.
    """
    path = STORAGE_DIR / f"{dashboard_id}.json"
    if not path.exists():
        logger.warning("Dashboard %s not found for deletion", dashboard_id)
        return False

    try:
        path.unlink()
        logger.info("Deleted dashboard %s", dashboard_id)
        return True
    except Exception as exc:
        logger.error("Failed to delete dashboard %s: %s", dashboard_id, exc)
        return False
