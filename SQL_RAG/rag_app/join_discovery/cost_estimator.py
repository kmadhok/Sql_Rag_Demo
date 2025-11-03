"""
Cost Estimator for Join Discovery

Handles cost estimation, guardrails, and budget enforcement for BigQuery queries.
Prevents accidental high bills by estimating costs before execution.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# BigQuery pricing (approximate, update as needed)
BQ_PRICE_PER_TB = 7.5  # USD per TB scanned


@dataclass
class TableProfile:
    """Profile of a table for cost estimation"""
    table_id: str
    row_count: int
    estimated_avg_row_bytes: int = 1000  # Default: 1KB per row

    def estimated_bytes(self, sample_size: Optional[int] = None) -> int:
        """Estimate bytes for a sample query"""
        if sample_size is None:
            sample_size = self.row_count
        actual_sample = min(sample_size, self.row_count)
        return actual_sample * self.estimated_avg_row_bytes


@dataclass
class JoinCandidate:
    """Join candidate to validate"""
    left_table: str
    right_table: str
    left_column: str
    right_column: str

    def __hash__(self):
        return hash((self.left_table, self.right_table, self.left_column, self.right_column))

    def __eq__(self, other):
        return (self.left_table == other.left_table and
                self.right_table == other.right_table and
                self.left_column == other.left_column and
                self.right_column == other.right_column)


@dataclass
class CostEstimate:
    """Cost estimation result"""
    status: str  # 'APPROVED', 'WARN', 'ABORT'
    total_candidates: int
    estimated_queries: int
    avg_bytes_per_query: int
    estimated_total_bytes: int
    estimated_cost_usd: float
    budget_usd: float
    budget_exceeded: bool
    budget_percentage: float
    warning_message: Optional[str] = None
    savings_vs_full_scan: str = ""
    breakdown: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status,
            'total_candidates': self.total_candidates,
            'estimated_queries': self.estimated_queries,
            'avg_bytes_per_query': self.avg_bytes_per_query,
            'estimated_total_bytes': self.estimated_total_bytes,
            'estimated_cost_usd': round(self.estimated_cost_usd, 2),
            'budget_usd': self.budget_usd,
            'budget_exceeded': self.budget_exceeded,
            'budget_percentage': round(self.budget_percentage, 1),
            'warning_message': self.warning_message,
            'savings_vs_full_scan': self.savings_vs_full_scan,
            'breakdown': self.breakdown
        }


class CostEstimator:
    """
    Estimates and manages costs for join discovery operations.

    Implements guardrails to prevent unexpectedly high BigQuery bills.
    """

    def __init__(
        self,
        budget_usd: float = 25.0,
        warn_threshold_percentage: float = 80.0,
        max_bytes_per_query: int = 1_000_000_000,  # 1 GB safety cap
    ):
        """
        Initialize cost estimator.

        Args:
            budget_usd: Maximum budget in USD (default: $25)
            warn_threshold_percentage: Warn when cost reaches this % of budget
            max_bytes_per_query: Safety cap on bytes per single query
        """
        self.budget_usd = budget_usd
        self.warn_threshold_percentage = warn_threshold_percentage
        self.max_bytes_per_query = max_bytes_per_query
        self.actual_cost_usd = 0.0
        self.actual_bytes_scanned = 0
        self.actual_queries_executed = 0
        self.cached_queries = 0

        logger.info(f"CostEstimator initialized: budget=${budget_usd}, warn_threshold={warn_threshold_percentage}%")

    def estimate_cost(
        self,
        table_profiles: Dict[str, TableProfile],
        candidates: List[JoinCandidate],
        dry_run: bool = False
    ) -> CostEstimate:
        """
        Estimate cost for discovering joins.

        Args:
            table_profiles: Map of table_id -> TableProfile
            candidates: List of join candidates to validate
            dry_run: If True, use smaller sample sizes for estimation

        Returns:
            CostEstimate with status (APPROVED/WARN/ABORT)
        """
        logger.info(f"Estimating cost for {len(candidates)} candidates...")

        if not candidates:
            logger.info("No candidates to estimate - returning zero cost")
            return CostEstimate(
                status='APPROVED',
                total_candidates=0,
                estimated_queries=0,
                avg_bytes_per_query=0,
                estimated_total_bytes=0,
                estimated_cost_usd=0.0,
                budget_usd=self.budget_usd,
                budget_exceeded=False,
                budget_percentage=0.0,
                savings_vs_full_scan="100% (no queries needed)"
            )

        # Calculate cost per candidate
        total_bytes = 0
        breakdown = {
            'per_candidate': [],
            'summary': {}
        }

        for candidate in candidates:
            # Estimate bytes for this candidate validation query
            # Query typically scans both tables' key columns
            bytes_estimate = self._estimate_candidate_cost(candidate, table_profiles)
            total_bytes += bytes_estimate

            breakdown['per_candidate'].append({
                'candidate': f"{candidate.left_table}.{candidate.left_column} -> {candidate.right_table}.{candidate.right_column}",
                'estimated_bytes': bytes_estimate,
                'estimated_cost_usd': bytes_estimate / 1e12 * BQ_PRICE_PER_TB
            })

        estimated_cost = total_bytes / 1e12 * BQ_PRICE_PER_TB  # Convert bytes to TB
        avg_bytes_per_query = total_bytes // len(candidates) if candidates else 0

        # Calculate savings vs full table scans
        total_table_bytes = sum(
            profile.row_count * profile.estimated_avg_row_bytes
            for profile in table_profiles.values()
        )
        savings_percentage = 100 * (1 - total_bytes / max(total_table_bytes, 1))

        # Determine status
        budget_percentage = (estimated_cost / self.budget_usd) * 100

        status = 'APPROVED'
        warning_msg = None

        if estimated_cost > self.budget_usd:
            status = 'ABORT'
            warning_msg = f"Cost estimate (${estimated_cost:.2f}) exceeds budget (${self.budget_usd:.2f})"
            logger.warning(warning_msg)
        elif budget_percentage >= self.warn_threshold_percentage:
            status = 'WARN'
            warning_msg = f"Cost estimate (${estimated_cost:.2f}) reaches {budget_percentage:.1f}% of budget"
            logger.warning(warning_msg)

        breakdown['summary'] = {
            'total_candidates': len(candidates),
            'total_estimated_bytes': total_bytes,
            'avg_bytes_per_candidate': avg_bytes_per_query,
            'estimated_cost_usd': round(estimated_cost, 2),
            'budget_usd': self.budget_usd,
            'budget_remaining_usd': round(self.budget_usd - estimated_cost, 2),
        }

        estimate = CostEstimate(
            status=status,
            total_candidates=len(candidates),
            estimated_queries=len(candidates),
            avg_bytes_per_query=avg_bytes_per_query,
            estimated_total_bytes=total_bytes,
            estimated_cost_usd=estimated_cost,
            budget_usd=self.budget_usd,
            budget_exceeded=estimated_cost > self.budget_usd,
            budget_percentage=budget_percentage,
            warning_message=warning_msg,
            savings_vs_full_scan=f"{savings_percentage:.1f}% vs full scans",
            breakdown=breakdown
        )

        logger.info(f"Cost estimate: ${estimated_cost:.2f} ({status})")
        return estimate

    def _estimate_candidate_cost(
        self,
        candidate: JoinCandidate,
        table_profiles: Dict[str, TableProfile]
    ) -> int:
        """Estimate bytes scanned for validating a single join candidate"""

        left_profile = table_profiles.get(candidate.left_table)
        right_profile = table_profiles.get(candidate.right_table)

        if not left_profile or not right_profile:
            # Conservative estimate: assume 10 MB per table if profile unavailable
            return 10_000_000

        # Cardinality test queries scan both tables' key columns
        # Typical: SELECT COUNT(DISTINCT left_column) FROM left_table
        #         SELECT COUNT(DISTINCT right_column) FROM right_table
        # Then: SELECT right_column FROM right_table WHERE right_column IN (SELECT DISTINCT left_column FROM left_table LIMIT N)

        # Conservative estimate: scan full key columns for both tables
        left_bytes = left_profile.estimated_bytes(sample_size=None)
        right_bytes = right_profile.estimated_bytes(sample_size=5000)  # Sample 5K from right table

        # Cap to safety limit
        total = min(left_bytes + right_bytes, self.max_bytes_per_query)

        return total

    def record_query_execution(
        self,
        bytes_scanned: int,
        cache_hit: bool = False,
        query_description: str = ""
    ) -> None:
        """
        Record actual query execution for cost tracking.

        Args:
            bytes_scanned: Actual bytes scanned by BigQuery
            cache_hit: Whether query result was cached
            query_description: Human description of query
        """
        if cache_hit:
            self.cached_queries += 1
            cost = 0.0  # Cached queries are free
        else:
            cost = bytes_scanned / 1e12 * BQ_PRICE_PER_TB

        self.actual_bytes_scanned += bytes_scanned
        self.actual_cost_usd += cost
        self.actual_queries_executed += 1

        logger.debug(
            f"Query execution recorded: {bytes_scanned:,} bytes, "
            f"${cost:.4f} cost, cache_hit={cache_hit}"
        )

    def get_actual_cost_summary(self) -> Dict:
        """Get actual cost metrics from execution"""
        return {
            'queries_executed': self.actual_queries_executed,
            'total_bytes_scanned': self.actual_bytes_scanned,
            'actual_cost_usd': round(self.actual_cost_usd, 2),
            'queries_cached': self.cached_queries,
            'cost_saved_by_caching': round(
                self.cached_queries * (self.actual_bytes_scanned / max(self.actual_queries_executed, 1)) / 1e12 * BQ_PRICE_PER_TB,
                2
            ),
            'timestamp': datetime.utcnow().isoformat()
        }

    def check_budget_exceeded(self) -> Tuple[bool, str]:
        """Check if actual cost has exceeded budget"""
        if self.actual_cost_usd > self.budget_usd:
            msg = f"Actual cost (${self.actual_cost_usd:.2f}) exceeds budget (${self.budget_usd:.2f})"
            logger.error(msg)
            return True, msg
        return False, ""

    def should_abort(self, estimated_cost: float) -> bool:
        """Check if operation should be aborted based on cost estimate"""
        return estimated_cost > self.budget_usd
