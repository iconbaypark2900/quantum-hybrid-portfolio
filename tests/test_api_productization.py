import os
import sys
import time
import pytest

# Ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Keep auth optional for tests
os.environ.pop("API_KEY", None)
os.environ["API_KEY_REQUIRED"] = "false"
os.environ["ADMIN_API_KEY"] = "admin-test-key"

from api import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as c:
        yield c


def _opt_payload():
    return {
        "returns": [0.12, 0.10, 0.14, 0.09],
        "covariance": [
            [0.04, 0.01, 0.01, 0.00],
            [0.01, 0.05, 0.01, 0.00],
            [0.01, 0.01, 0.06, 0.01],
            [0.00, 0.00, 0.01, 0.03],
        ],
        "asset_names": ["AAPL", "MSFT", "NVDA", "JNJ"],
        "sectors": ["Tech", "Tech", "Tech", "Health"],
        "objective": "max_sharpe",
        "strategyPreset": "balanced",
    }


def test_batch_optimization_endpoint(client):
    payload = {"requests": [_opt_payload(), _opt_payload()]}
    r = client.post("/api/portfolio/optimize/batch", json=payload)
    assert r.status_code == 200
    data = r.get_json()
    assert data["count"] == 2
    assert all(item["status"] == "ok" for item in data["results"])


def test_async_optimize_job_flow(client):
    r = client.post("/api/jobs/optimize", json={"payload": _opt_payload()})
    assert r.status_code == 202
    body = r.get_json()
    job_id = body["job_id"]

    # Poll until completion
    for _ in range(30):
        status_r = client.get(f"/api/jobs/{job_id}")
        assert status_r.status_code == 200
        status_data = status_r.get_json()
        if status_data["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert status_data["status"] == "completed"
    assert "qsw_result" in status_data["result"]


def test_admin_api_key_lifecycle(client):
    create = client.post(
        "/api/admin/api-keys",
        json={"tenant_id": "tenant_alpha", "key_name": "pilot"},
        headers={"X-Admin-Key": "admin-test-key"},
    )
    assert create.status_code == 201
    created = create.get_json()
    assert created["tenant_id"] == "tenant_alpha"
    assert created["api_key"]

    listed = client.get(
        "/api/admin/api-keys",
        headers={"X-Admin-Key": "admin-test-key"},
    )
    assert listed.status_code == 200
    keys = listed.get_json()["keys"]
    assert any(k["tenant_id"] == "tenant_alpha" for k in keys)

