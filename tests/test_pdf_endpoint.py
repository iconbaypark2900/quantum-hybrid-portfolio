"""
tests/test_pdf_endpoint.py — PDF report generation endpoint tests.

Tests the GET /api/export/report/<run_id>.pdf route.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.pop('API_KEY', None)
os.environ['RATELIMIT_ENABLED'] = 'false'

import pytest
from unittest.mock import patch

from api import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False
    with app.test_client() as c:
        yield c


_MOCK_RUN = {
    "id": "test-pdf-run-001",
    "tenant_id": "anonymous",
    "status": "completed",
    "execution_kind": "sync_optimize",
    "spec": {
        "objective": "sharpe",
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "weight_min": 0.005,
        "weight_max": 0.30,
        "seed": 42,
    },
    "result": {
        "sharpe_ratio": 1.234,
        "expected_return": 0.12,
        "volatility": 0.18,
        "n_active": 3,
        "objective": "sharpe",
        "holdings": [
            {"name": "AAPL", "weight": 0.45, "sector": "Technology"},
            {"name": "MSFT", "weight": 0.35, "sector": "Technology"},
            {"name": "GOOGL", "weight": 0.20, "sector": "Technology"},
        ],
        "risk_metrics": {
            "var_95": -0.018,
            "cvar": -0.023,
        },
    },
    "payload": None,
    "error": None,
    "external_job_id": None,
    "created_at": "2025-06-01T12:00:00+00:00",
    "started_at": "2025-06-01T12:00:01+00:00",
    "finished_at": "2025-06-01T12:00:05+00:00",
}


class TestPdfEndpoint:

    @patch("services.lab_run_service.get_run", return_value=_MOCK_RUN)
    def test_pdf_returns_pdf_content_type(self, mock_get_run, client):
        resp = client.get('/api/export/report/test-pdf-run-001.pdf')
        assert resp.status_code == 200
        assert resp.content_type == 'application/pdf'
        mock_get_run.assert_called_once_with("test-pdf-run-001", "anonymous")

    @patch("services.lab_run_service.get_run", return_value=_MOCK_RUN)
    def test_pdf_non_empty(self, mock_get_run, client):
        resp = client.get('/api/export/report/test-pdf-run-001.pdf')
        assert resp.status_code == 200
        assert len(resp.data) > 1000, "PDF should be a non-trivial byte stream"
        assert resp.data[:5] == b'%PDF-', "PDF should start with the %PDF- magic bytes"

    def test_pdf_404_unknown_run(self, client):
        resp = client.get('/api/export/report/nonexistent-id.pdf')
        assert resp.status_code == 404
