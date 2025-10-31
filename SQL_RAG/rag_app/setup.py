#!/usr/bin/env python3
"""Setuptools configuration for the SQL RAG application."""

from __future__ import annotations

from pathlib import Path
from typing import List

from setuptools import find_namespace_packages, find_packages, setup

BASE_DIR = Path(__file__).parent.resolve()


def read_requirements(filename: str) -> List[str]:
    """Parse a requirements file and return a clean dependency list."""
    path = BASE_DIR / filename
    if not path.exists():
        return []

    requirements: List[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirements.append(line)
    return requirements


def discover_py_modules() -> List[str]:
    """Return standalone Python modules that should be installed."""
    modules: List[str] = []
    for path in BASE_DIR.glob("*.py"):
        if not path.is_file():
            continue
        if path.name in {"setup.py", "setup-local.py"}:
            continue
        modules.append(path.stem)
    return modules


def read_long_description() -> str:
    """Load the project README for the package long description."""
    readme_path = BASE_DIR / "README.md"
    if not readme_path.exists():
        return ""
    return readme_path.read_text(encoding="utf-8")


packages = sorted(
    set(find_packages(include=["*"]) + find_namespace_packages(include=["*"]))
)

setup(
    name="sql-rag-app",
    version="0.1.0",
    description="Retrieval-augmented SQL assistant with FastAPI backend and React frontend.",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    author="SQL RAG Maintainers",
    python_requires=">=3.10",
    packages=packages,
    py_modules=discover_py_modules(),
    include_package_data=True,
    install_requires=read_requirements("requirements.txt"),
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.23",
            "httpx>=0.25",
            "ruff>=0.3",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
