"""
Unit tests for IBM Runtime workloads listing (no live IBM network).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services import ibm_quantum as iq  # noqa: E402


@pytest.fixture(autouse=True)
def restore_services():
    """Snapshot and restore ibm_quantum._services between tests."""
    with iq._lock:
        before = dict(iq._services)
    yield
    with iq._lock:
        iq._services.clear()
        iq._services.update(before)


def test_list_runtime_workloads_not_configured():
    tid = "__test_no_token_tenant__"
    with iq._lock:
        iq._services.pop(tid, None)
    out = iq.list_runtime_workloads(tid)
    assert out["ok"] is False
    assert out["configured"] is False
    assert out["workloads"] == []


def test_list_runtime_workloads_success_mock():
    class MockJob:
        def job_id(self):
            return "job-abc-123"

        def status(self):
            return "DONE"

        def backend(self):
            b = MagicMock()
            b.name = "ibm_mock"
            return b

        @property
        def creation_date(self):
            return datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

        def usage(self):
            return 2.5

        @property
        def instance(self):
            return "crn:v1:quantum:mock:1"

        @property
        def primitive_id(self):
            return "sampler"

    class MockSvc:
        def jobs(self, limit=10, descending=True, **kwargs):
            assert limit <= 100
            return [MockJob()]

    tid = "__test_mock_svc__"
    with iq._lock:
        iq._services[tid] = (MockSvc(), "fake-token")

    out = iq.list_runtime_workloads(tid, limit=5)
    assert out["ok"] is True
    assert out["configured"] is True
    assert len(out["workloads"]) == 1
    row = out["workloads"][0]
    assert row["job_id"] == "job-abc-123"
    assert row["status"] == "DONE"
    assert row["backend"] == "ibm_mock"
    assert row["usage_seconds"] == 2.5
    assert row["instance"] == "crn:v1:quantum:mock:1"
    assert row["program_id"] == "sampler"


def test_list_runtime_workloads_jobs_raises():
    class BoomSvc:
        def jobs(self, **kwargs):
            raise RuntimeError("simulated IBM API failure")

    tid = "__test_boom__"
    with iq._lock:
        iq._services[tid] = (BoomSvc(), "tok")

    out = iq.list_runtime_workloads(tid)
    assert out["ok"] is False
    assert out["configured"] is True
    assert out["workloads"] == []
    assert "simulated IBM API failure" in (out.get("error") or "")
