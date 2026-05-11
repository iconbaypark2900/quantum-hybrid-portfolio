"""
tests/test_circuit_metadata.py

Verifies that circuit_metadata is embedded in quantum_metadata for IBM/VQE
objectives and absent for classical objectives.

The sync POST /api/portfolio/optimize route calls core.portfolio_optimizer.vqe_weights
(classical VQE simulation). We mock at that level to inject circuit_metadata and
assert it propagates through to the API response.
"""
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.pop("API_KEY", None)
os.environ["RATELIMIT_ENABLED"] = "false"

import pytest
import numpy as np
from unittest.mock import patch

from api import app, generate_mock_data


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as c:
        yield c


def _optimize_payload(objective="markowitz", n=5):
    assets, corr = generate_mock_data(n, "normal")
    vols = np.array([a["ann_vol"] for a in assets])
    returns = np.array([a["ann_return"] for a in assets])
    cov = np.outer(vols, vols) * corr
    return {
        "returns": returns.tolist(),
        "covariance": cov.tolist(),
        "objective": objective,
    }


MOCK_CIRCUIT_META = {
    "n_qubits": 5,
    "n_parameters": 20,
    "depth_original": 12,
    "depth_transpiled": 42,
    "gate_count_transpiled": {"cx": 16, "rz": 20, "sx": 10},
    "two_qubit_gate_count": 16,
    "backend_name": "ibm_statevector_simulator",
    "shots": 1024,
    "noise_model_type": "ideal_simulator",
    "execute_time_s": 0.123,
}


def _mock_vqe_weights(mu, Sigma, **kwargs):
    """Stub for core.portfolio_optimizer.vqe_weights — returns equal weights + circuit_metadata."""
    n = len(mu)
    w = np.ones(n) / n
    meta = {
        "execution_kind": "classical_statevector",
        "objective": "vqe",
        "n_assets": n,
        "circuit_metadata": MOCK_CIRCUIT_META,
    }
    return w, meta


def test_circuit_metadata_present_for_ibm_objective(client):
    """
    POST /api/portfolio/optimize with objective=vqe should include circuit_metadata
    in the quantum_metadata field of the response when the VQE method returns it.
    """
    with patch("core.portfolio_optimizer.vqe_weights", side_effect=_mock_vqe_weights):
        payload = _optimize_payload("vqe", n=5)
        resp = client.post("/api/portfolio/optimize", json=payload)

    assert resp.status_code == 200
    body = resp.get_json()
    data = body.get("data", body)
    qm = data.get("quantum_metadata")
    assert qm is not None, "quantum_metadata should be present for VQE objective"
    cm = qm.get("circuit_metadata")
    assert cm is not None, "circuit_metadata should be nested inside quantum_metadata"
    assert cm["depth_transpiled"] == 42
    assert cm["two_qubit_gate_count"] == 16
    assert cm["backend_name"] == "ibm_statevector_simulator"


def test_circuit_metadata_null_for_classical(client):
    """
    Classical objectives (e.g. markowitz) should return quantum_metadata=None
    (the field is absent or null in the response).
    """
    payload = _optimize_payload("markowitz", n=5)
    resp = client.post("/api/portfolio/optimize", json=payload)

    assert resp.status_code == 200
    body = resp.get_json()
    data = body.get("data", body)
    qm = data.get("quantum_metadata")
    assert qm is None, "quantum_metadata should be None for classical (markowitz) objective"


def test_circuit_metadata_depth_fields_types():
    """
    circuit_metadata dict must conform to the expected field types:
    depths and gate counts are int-or-None, backend_name is str, shots is int.
    """
    cm = MOCK_CIRCUIT_META
    assert isinstance(cm["depth_transpiled"], (int, type(None)))
    assert isinstance(cm["two_qubit_gate_count"], (int, type(None)))
    assert isinstance(cm["gate_count_transpiled"], (dict, type(None)))
    assert isinstance(cm["n_qubits"], int)
    assert isinstance(cm["backend_name"], str)
    assert isinstance(cm["shots"], int)
    assert isinstance(cm["execute_time_s"], (int, float))
    # values must be non-negative when present
    if cm["depth_transpiled"] is not None:
        assert cm["depth_transpiled"] >= 0
    if cm["two_qubit_gate_count"] is not None:
        assert cm["two_qubit_gate_count"] >= 0
    # gate_count_transpiled values must be non-negative counts
    if cm["gate_count_transpiled"] is not None:
        for gate, count in cm["gate_count_transpiled"].items():
            assert isinstance(gate, str)
            assert isinstance(count, int) and count >= 0
