"""
Synthetic market data for simulation mode — aligned with `api.app.generate_mock_data`
(annualized returns + correlation → covariance for `/api/portfolio/optimize`).
"""
from __future__ import annotations

import numpy as np

_NAMES = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "JNJ",
    "PG", "UNH", "HD", "MA", "BAC", "DIS", "NFLX", "KO", "PFE", "CVX", "WMT",
    "MRK", "ABT", "ADBE", "NKE", "PEP", "T", "VZ", "PYPL", "BRK",
]
_SECTORS = [
    "Tech", "Tech", "Tech", "Tech", "Tech", "Tech", "Tech", "Finance", "Finance", "Health",
    "Consumer", "Health", "Consumer", "Finance", "Finance", "Consumer", "Tech", "Consumer",
    "Health", "Energy", "Consumer", "Health", "Health", "Tech", "Consumer", "Consumer",
    "Telecom", "Telecom", "Tech", "Finance",
]


def generate_synthetic(n_assets: int, regime: str, seed: int) -> tuple[list, np.ndarray, list[dict]]:
    """
    Returns (returns_1d, covariance_matrix, asset_dicts for display).
    """
    rng = np.random.default_rng(seed)
    regime_params = {
        "bull": {"drift": 0.0008, "vol": 0.012, "corr_base": 0.3},
        "bear": {"drift": -0.0003, "vol": 0.022, "corr_base": 0.6},
        "volatile": {"drift": 0.0002, "vol": 0.028, "corr_base": 0.45},
        "normal": {"drift": 0.0004, "vol": 0.015, "corr_base": 0.35},
    }
    params = regime_params.get(regime, regime_params["normal"])

    assets: list[dict] = []
    for i in range(n_assets):
        drift = params["drift"] + (rng.random() - 0.4) * 0.001
        vol = params["vol"] * (0.7 + rng.random() * 0.6)
        daily = rng.normal(drift, vol, 252)
        ann_return = float(np.mean(daily) * 252)
        ann_vol = float(np.std(daily) * np.sqrt(252))
        sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0
        assets.append(
            {
                "name": _NAMES[i] if i < len(_NAMES) else f"ASSET_{i}",
                "sector": _SECTORS[i] if i < len(_SECTORS) else "Other",
                "ann_return": ann_return,
                "ann_vol": ann_vol,
                "sharpe": float(sharpe),
            }
        )

    n = n_assets
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            same = 0.1 if assets[i]["sector"] == assets[j]["sector"] else 0.0
            base = params["corr_base"]
            r_c = rng.uniform(-0.2, 0.4)
            c_val = float(np.clip(base + same + r_c, -0.3, 0.95))
            corr[i, j] = c_val
            corr[j, i] = c_val

    cov = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            cov[i, j] = assets[i]["ann_vol"] * assets[j]["ann_vol"] * corr[i, j]

    returns_1d = [a["ann_return"] for a in assets]
    return returns_1d, cov, assets


def build_matrix_optimize_payload(
    n_assets: int,
    regime: str,
    seed: int,
    objective: str,
    weight_min: float,
    max_weight: float,
    k: str,
    k_screen: str,
    k_select: str,
) -> dict:
    returns_1d, cov, assets = generate_synthetic(n_assets, regime, seed)
    payload: dict = {
        "returns": returns_1d,
        "covariance": cov.tolist(),
        "asset_names": [a["name"] for a in assets],
        "sectors": [a["sector"] for a in assets],
        "objective": objective,
        "weight_min": weight_min,
        "maxWeight": max_weight,
        "seed": seed,
    }
    if k.strip():
        try:
            payload["K"] = int(k)
        except ValueError:
            pass
    if k_screen.strip():
        try:
            payload["K_screen"] = int(k_screen)
        except ValueError:
            pass
    if k_select.strip():
        try:
            payload["K_select"] = int(k_select)
        except ValueError:
            pass
    return payload
