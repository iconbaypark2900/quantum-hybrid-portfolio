"""
Portfolio constraints for Phase 2 advanced optimization.
Supports sector limits, cardinality, blacklist/whitelist.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class PortfolioConstraints:
    """
    Advanced portfolio constraints.

    Attributes:
        sector_limits: Max weight per sector, e.g. {'Technology': 0.30, 'Finance': 0.25}
        sector_min: Min weight per sector (optional), e.g. {'Healthcare': 0.05}
        max_sector_weight: Global cap for any sector not in sector_limits (e.g. 0.40)
        cardinality: Exact number of positions (uses top-k heuristic)
        min_cardinality: Minimum number of positions
        max_cardinality: Maximum number of positions
        blacklist: Asset tickers/names to exclude (case-insensitive)
        whitelist: If non-empty, ONLY these assets allowed
        turnover_budget: Max turnover per rebalance (fraction, e.g. 0.20 = 20%)
    """
    sector_limits: Dict[str, float] = field(default_factory=dict)
    sector_min: Dict[str, float] = field(default_factory=dict)
    max_sector_weight: Optional[float] = None  # e.g. 0.40
    cardinality: Optional[int] = None
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None
    blacklist: List[str] = field(default_factory=list)
    whitelist: List[str] = field(default_factory=list)
    turnover_budget: Optional[float] = None  # e.g. 0.20

    def has_constraints(self) -> bool:
        """Return True if any constraint is set."""
        return bool(
            self.sector_limits
            or self.sector_min
            or self.max_sector_weight is not None
            or self.cardinality is not None
            or self.min_cardinality is not None
            or self.max_cardinality is not None
            or self.blacklist
            or self.whitelist
        )

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "PortfolioConstraints":
        """Build from API-style dict."""
        if not d:
            return cls()
        return cls(
            sector_limits=d.get("sector_limits") or {},
            sector_min=d.get("sector_min") or {},
            max_sector_weight=d.get("max_sector_weight"),
            cardinality=d.get("cardinality"),
            min_cardinality=d.get("min_cardinality"),
            max_cardinality=d.get("max_cardinality"),
            blacklist=[str(x).strip().upper() for x in (d.get("blacklist") or [])],
            whitelist=[str(x).strip().upper() for x in (d.get("whitelist") or [])],
            turnover_budget=d.get("turnover_budget"),
        )


def compute_sector_masks(
    sectors: List[str],
) -> Dict[str, List[int]]:
    """
    Map sector name -> list of asset indices in that sector.

    Args:
        sectors: Sector for each asset (same length as returns/covariance)

    Returns:
        Dict mapping sector -> indices
    """
    masks: Dict[str, List[int]] = {}
    for i, s in enumerate(sectors):
        key = (s or "Unknown").strip()
        if key not in masks:
            masks[key] = []
        masks[key].append(i)
    return masks
