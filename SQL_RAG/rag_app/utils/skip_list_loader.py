"""
Utility functions for loading skip lists of SQL queries.

Supports both CSV files with a `query` column and newline-delimited text files.
"""

from pathlib import Path
from typing import Iterable, Set

import pandas as pd


def load_skip_queries(paths: Iterable[Path]) -> Set[str]:
    """Return a set of normalized SQL queries parsed from skip-list files."""
    skip: Set[str] = set()
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Skip-list file not found: {path}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(path)
            if "query" not in df.columns:
                raise ValueError(f"CSV skip-list missing 'query' column: {path}")
            for value in df["query"]:
                text = str(value).strip()
                if text:
                    skip.add(text)
        else:
            for line in path.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if text:
                    skip.add(text)
    return skip
