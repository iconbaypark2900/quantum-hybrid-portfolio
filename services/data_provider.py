"""
Data provider abstraction for optimization and analytics endpoints.

Supports:
- Matrix input (returns + covariance) for production fund integrations.
- Ticker input via yfinance as a fallback/demo source.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import os

from services.data_provider_v2 import fetch_market_data


@dataclass
class MarketPayload:
    """Normalized market payload consumed by optimization services."""
    assets: List[Dict[str, Any]]
    returns: np.ndarray
    covariance: np.ndarray
    tickers: List[str]
    source: str  # "matrix" or "yfinance"


def _assets_from_matrix(
    returns: np.ndarray,
    covariance: np.ndarray,
    asset_names: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    n_assets = len(returns)
    names = asset_names or [f"ASSET_{i}" for i in range(n_assets)]
    sec = sectors or ["Unknown"] * n_assets

    assets: List[Dict[str, Any]] = []
    for i in range(n_assets):
        ann_vol = float(np.sqrt(covariance[i][i])) if i < len(covariance) else 0.0
        ann_ret = float(returns[i])
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
        assets.append(
            {
                "name": names[i] if i < len(names) else f"ASSET_{i}",
                "sector": sec[i] if i < len(sec) else "Unknown",
                "ann_return": ann_ret,
                "ann_vol": ann_vol,
                "sharpe": float(sharpe),
            }
        )
    return assets


def load_market_payload(data: Dict[str, Any]) -> MarketPayload:
    """
    Normalize request payload into market data for optimization.

    Preferred production path:
    - provide `returns` and `covariance` directly.

    Fallback path:
    - provide `tickers` with optional date range to fetch via yfinance.
    """
    tickers = data.get("tickers", []) or []
    returns_in = data.get("returns")
    covariance_in = data.get("covariance")
    matrix_only = os.getenv("REQUIRE_MATRIX_INPUT", "false").lower() == "true"

    # Production path: direct matrix input
    if returns_in is not None and covariance_in is not None:
        returns = np.array(returns_in, dtype=float)
        covariance = np.array(covariance_in, dtype=float)
        if returns.ndim != 1 or covariance.ndim != 2:
            raise ValueError("returns must be 1D and covariance must be 2D")
        if covariance.shape[0] != covariance.shape[1]:
            raise ValueError("covariance matrix must be square")
        if len(returns) != covariance.shape[0]:
            raise ValueError("returns length must match covariance dimensions")

        assets = _assets_from_matrix(
            returns=returns,
            covariance=covariance,
            asset_names=data.get("asset_names"),
            sectors=data.get("sectors"),
        )
        synthetic_tickers = [a["name"] for a in assets]
        return MarketPayload(
            assets=assets,
            returns=returns,
            covariance=covariance,
            tickers=synthetic_tickers,
            source="matrix",
        )

    # Fallback path: yfinance ticker fetch
    if matrix_only:
        raise ValueError("This environment requires returns/covariance input; ticker-based fetch is disabled")
    if not tickers:
        raise ValueError("Provide either (returns + covariance) or a non-empty tickers list")

    market_data = fetch_market_data(
        tickers=tickers,
        start_date=data.get("startDate") or data.get("start_date"),
        end_date=data.get("endDate") or data.get("end_date"),
    )

    returns = np.array(market_data["returns"], dtype=float)
    covariance = np.array(market_data["covariance"], dtype=float)

    assets: List[Dict[str, Any]] = []
    for i, name in enumerate(market_data.get("names", [])):
        ann_vol = float(np.sqrt(covariance[i][i])) if i < len(covariance) else 0.0
        ann_ret = float(market_data["returns"][i])
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
        assets.append(
            {
                "name": market_data["assets"][i] if i < len(market_data["assets"]) else str(name),
                "sector": market_data["sectors"][i] if i < len(market_data["sectors"]) else "Unknown",
                "ann_return": ann_ret,
                "ann_vol": ann_vol,
                "sharpe": float(sharpe),
            }
        )

    return MarketPayload(
        assets=assets,
        returns=returns,
        covariance=covariance,
        tickers=list(tickers),
        source="yfinance",
    )

