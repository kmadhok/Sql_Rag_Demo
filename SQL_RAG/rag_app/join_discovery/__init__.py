"""
Table Join Discovery Module

A standalone, modular tool for discovering table join relationships in BigQuery datasets.
Designed for cost awareness, incremental analysis, and comprehensive validation.
"""

__version__ = "0.1.0"

from join_discovery_engine import JoinDiscoveryEngine
from cost_estimator import CostEstimator
from run_manifest import RunManifest

__all__ = [
    "JoinDiscoveryEngine",
    "CostEstimator",
    "RunManifest",
]
