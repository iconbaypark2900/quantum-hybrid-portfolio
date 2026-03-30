"""
Unit tests for IBM Runtime workloads listing (no live IBM network).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services import ibm_quantum as iq  # noqa: E402
from services.data_provider import MarketPayload  # noqa: E402


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
        iq._services[tid] = (MockSvc(), "fake-token", None)

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
        iq._services[tid] = (BoomSvc(), "tok", None)

    out = iq.list_runtime_workloads(tid)
    assert out["ok"] is False
    assert out["configured"] is True
    assert out["workloads"] == []
    assert "simulated IBM API failure" in (out.get("error") or "")


def test_verify_token_does_not_persist_or_cache_service():
    pytest.importorskip("qiskit_ibm_runtime")
    tid = "__verify_no_side_effects__"
    with iq._lock:
        iq._services.pop(tid, None)

    class MockBackend:
        name = "ibm_mock_backend"

    class MockService:
        def backends(self):
            return [MockBackend()]

        def instances(self):
            return [{"name": "inst-a", "plan": "open", "crn": "crn:v1:quantum:testing:12345"}]

        def active_instance(self):
            return "crn:v1:quantum:active"

    with patch("qiskit_ibm_runtime.QiskitRuntimeService", return_value=MockService()):
        out = iq.verify_token(tid, "fake-token-value")

    assert out["ok"] is True
    assert out["backends"] == ["ibm_mock_backend"]
    assert out["tenant_id"] == tid
    assert len(out["ibm_instances"]) == 1
    assert out["ibm_instances"][0]["name"] == "inst-a"
    assert out["ibm_active_instance"] == "crn:v1:quantum:active"
    assert out.get("ibm_saved_instance_crn_suffix") is None


def test_verify_token_passes_instance_crn_to_qiskit():
    pytest.importorskip("qiskit_ibm_runtime")
    tid = "__verify_inst_kw__"
    captured: dict = {}

    class Mini:
        def backends(self):
            return []

        def instances(self):
            return []

        def active_instance(self):
            return None

    def fake_ctor(**kwargs):
        captured.update(kwargs)
        return Mini()

    crn = "crn:v1:quantum:public:ibm-q:us-east:instance-guid"
    with patch("qiskit_ibm_runtime.QiskitRuntimeService", side_effect=fake_ctor):
        out = iq.verify_token(tid, "fake-token-value", crn)

    assert out["ok"] is True
    assert captured.get("channel") == "ibm_quantum_platform"
    assert captured.get("token") == "fake-token-value"
    assert captured.get("instance") == crn
    assert out.get("ibm_saved_instance_crn_suffix")
    with iq._lock:
        assert tid not in iq._services


def test_verify_token_empty():
    out = iq.verify_token("t", "")
    assert out["ok"] is False
    assert "empty" in (out.get("error") or "").lower()


def test_secrets_persistence_enabled_reflects_db_factory():
    prev = iq._db_conn_factory
    try:
        iq.set_db_conn_factory(lambda: None)
        assert iq.secrets_persistence_enabled() is True
        iq.set_db_conn_factory(None)
        assert iq.secrets_persistence_enabled() is False
    finally:
        iq.set_db_conn_factory(prev)


def test_hardware_smoke_not_configured():
    tid = "__smoke_no_token__"
    with iq._lock:
        iq._services.pop(tid, None)
    out = iq.hardware_smoke_test(tid)
    assert out["ok"] is False
    assert out.get("configured") is False


def test_hardware_smoke_invalid_mode():
    out = iq.hardware_smoke_test("default", mode="not-a-mode")
    assert out["ok"] is False
    assert "mode" in (out.get("error") or "").lower()


def test_hardware_smoke_success_mock():
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_ibm_runtime")
    from qiskit.circuit.library import EfficientSU2

    tid = "__smoke_mock_ok__"
    cfg = MagicMock()
    cfg.simulator = False
    cfg.n_qubits = 5
    st = MagicMock()
    st.pending_jobs = 0
    backend = MagicMock()
    backend.name = "ibm_test"
    backend.configuration.return_value = cfg
    backend.status.return_value = st

    mock_svc = MagicMock()
    mock_svc.backends.return_value = [backend]

    mp = MarketPayload(
        assets=[
            {"name": "A", "sector": "x", "ann_return": 0.1, "ann_vol": 0.2, "sharpe": 0.5},
            {"name": "B", "sector": "x", "ann_return": 0.08, "ann_vol": 0.18, "sharpe": 0.5},
        ],
        returns=np.array([0.1, 0.08]),
        covariance=np.array([[0.04, 0.01], [0.01, 0.05]]),
        tickers=["A", "B"],
        source="matrix",
    )

    pub = MagicMock()
    pub.data.meas.get_counts.return_value = {"00": 64, "11": 64}
    pub.job_id = "job-smoke-xyz"

    indexed = MagicMock()
    indexed.__getitem__.return_value = pub

    run_chain = MagicMock()
    run_chain.result.return_value = indexed

    sampler_inst = MagicMock()
    sampler_inst.run.return_value = run_chain

    ansatz = EfficientSU2(2, reps=1, entanglement="linear")
    ansatz.measure_all()
    bound = ansatz.assign_parameters(np.zeros(len(ansatz.parameters)))

    pm = MagicMock()
    pm.run.return_value = bound

    with iq._lock:
        iq._services[tid] = (mock_svc, "tok", None)

    with patch("services.data_provider.load_market_payload", return_value=mp), patch(
        "qiskit.transpiler.preset_passmanagers.generate_preset_pass_manager", return_value=pm
    ), patch("qiskit_ibm_runtime.SamplerV2", return_value=sampler_inst):
        out = iq.hardware_smoke_test(tid, mode="hardware")

    assert out["ok"] is True
    assert out.get("configured") is True
    assert out["backend"] == "ibm_test"
    assert out["counts"].get("00") == 64
    assert out["n_assets"] == 2
    assert out.get("smoke_profile") == "efficient_su2_fixed_params_vqe_shaped"
    assert out.get("sharpe_ratio") is not None
    assert out.get("job_id") == "job-smoke-xyz"


def test_hardware_smoke_market_load_fails():
    tid = "__smoke_mkt_fail__"
    with iq._lock:
        iq._services[tid] = (MagicMock(), "tok", None)
    with patch(
        "services.data_provider.load_market_payload",
        side_effect=ValueError("no data"),
    ):
        out = iq.hardware_smoke_test(tid, market_payload={"tickers": ["BAD"]})
    assert out["ok"] is False
    assert "Market data" in (out.get("error") or "")


def test_marginal_weights_from_counts():
    w = iq._marginal_weights_from_counts(
        {"00": 25, "11": 75}, 2, 0.001, 0.30
    )
    assert len(w) == 2
    assert abs(float(np.sum(w)) - 1.0) < 1e-6
