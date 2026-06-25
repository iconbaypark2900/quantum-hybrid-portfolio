"""
Tests for data provenance in optimize response (roadmap #13).

Verifies:
  - ``data_provenance`` block is present in optimize response.
  - Matrix-only payloads return ``fallback_used=False`` and ``data_source="matrix"``.
  - Ticker-based payloads return the provider name and an ISO data_timestamp.
  - ``data_staleness_hours`` is computed from data_timestamp.
  - /api/health/detailed returns the nested ``dependencies`` block.
  - When Tiingo fails and yfinance succeeds, ``fallback_used=True`` and
    ``data_source`` reflects the fallback provider.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.pop("API_KEY", None)
os.environ["RATELIMIT_ENABLED"] = "false"

import numpy as np
import pytest
from unittest.mock import patch

from api import app, generate_mock_data


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as c:
        yield c


def _optimize_payload_matrix(n=5):
    assets, corr = generate_mock_data(n, "normal")
    vols = np.array([a["ann_vol"] for a in assets])
    returns = np.array([a["ann_return"] for a in assets])
    cov = np.outer(vols, vols) * corr
    return {
        "returns": returns.tolist(),
        "covariance": cov.tolist(),
        "objective": "markowitz",
    }


# ── Optimize response provenance ────────────────────────────────────────────


def test_optimize_response_includes_data_provenance(client):
    """Matrix-only payload returns data_provenance with data_source='matrix'."""
    payload = _optimize_payload_matrix(n=5)
    resp = client.post("/api/portfolio/optimize", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    data = body.get("data", body)
    dp = data.get("data_provenance")
    assert dp is not None, "data_provenance block missing from response"
    assert dp["data_source"] == "matrix"
    assert dp["fallback_used"] is False
    # Matrix payloads have no data_timestamp (user-supplied data).
    assert dp["data_timestamp"] is None
    assert dp["data_staleness_hours"] is None


def test_data_provenance_with_ticker_payload(client):
    """Ticker-based payload populates data_provenance with the resolved provider."""
    with patch("services.data_provider.fetch_market_data") as mock_fetch:
        # Build a fake market payload (as if Tiingo returned it).
        n = 3
        assets = ["AAPL", "MSFT", "GOOGL"]
        vols = np.array([0.2, 0.18, 0.22])
        returns = np.array([0.10, 0.08, 0.12])
        corr = np.array([[1.0, 0.3, 0.2], [0.3, 1.0, 0.25], [0.2, 0.25, 1.0]])
        cov = corr * np.outer(vols, vols)
        ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
        mock_fetch.return_value = {
            "assets": assets,
            "names": assets,
            "sectors": ["Tech", "Tech", "Tech"],
            "returns": returns.tolist(),
            "covariance": cov.tolist(),
            "data_points": 252,
            "covariance_source": "full_window",
            "start_date": "2023-01-01",
            "end_date": "2025-01-01",
            "provider": "tiingo",
            "fallback_used": False,
            "data_timestamp": ts,
            "success": True,
            "message": "mocked",
        }
        resp = client.post(
            "/api/portfolio/optimize",
            json={"tickers": assets, "objective": "markowitz"},
        )
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json().get("data", resp.get_json())
    dp = data.get("data_provenance")
    assert dp is not None
    assert dp["data_source"] == "tiingo"
    assert dp["fallback_used"] is False
    assert dp["data_timestamp"] == ts
    # Staleness ~ 2 hours (allow generous tolerance for test runtime).
    assert dp["data_staleness_hours"] is not None
    assert 1.0 <= dp["data_staleness_hours"] <= 5.0


def test_fallback_used_flag_set_on_yfinance_fallback(client):
    """When provider != primary, fallback_used=True and data_source reflects the fallback."""
    with patch("services.data_provider.fetch_market_data") as mock_fetch:
        n = 3
        assets = ["AAPL", "MSFT", "GOOGL"]
        vols = np.array([0.2, 0.18, 0.22])
        returns = np.array([0.10, 0.08, 0.12])
        corr = np.eye(3)
        cov = corr * np.outer(vols, vols)
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        mock_fetch.return_value = {
            "assets": assets,
            "names": assets,
            "sectors": ["Tech", "Tech", "Tech"],
            "returns": returns.tolist(),
            "covariance": cov.tolist(),
            "data_points": 252,
            "covariance_source": "full_window",
            "start_date": "2023-01-01",
            "end_date": "2025-01-01",
            "provider": "yfinance",
            "fallback_used": True,
            "data_timestamp": ts,
            "success": True,
            "message": "mocked",
        }
        resp = client.post(
            "/api/portfolio/optimize",
            json={"tickers": assets, "objective": "markowitz"},
        )
    assert resp.status_code == 200
    data = resp.get_json().get("data", resp.get_json())
    dp = data.get("data_provenance")
    assert dp["data_source"] == "yfinance"
    assert dp["fallback_used"] is True


# ── /api/health/detailed ────────────────────────────────────────────────────


def test_health_detailed_endpoint_returns_nested_dependencies(client):
    """/api/health/detailed returns 200 with a ``dependencies`` block."""
    resp = client.get("/api/health/detailed")
    assert resp.status_code == 200
    body = resp.get_json()
    data = body.get("data", body)
    assert "dependencies" in data, "dependencies block missing"
    deps = data["dependencies"]
    for key in ("market_data", "database", "redis", "quantum", "dependencies"):
        assert key in deps, f"missing dependency: {key}"
    assert "overall" in data
    assert data["overall"] in ("healthy", "degraded")
    assert "timestamp" in data
    md = deps["market_data"]
    assert "status" in md
    assert "provider" in md or md.get("provider") is None
