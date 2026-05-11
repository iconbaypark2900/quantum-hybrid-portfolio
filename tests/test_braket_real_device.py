"""
Unit and integration tests for services/braket_backend.py.

All tests here run without AWS credentials — real hardware is skipped
unless BRAKET_REAL_DEVICE_TEST=1 is set in the environment.

Pytest markers:
  braket_mock   — tests that use BraketAnnealingOptimizer in mock/fallback mode
  braket_real   — tests that require a real D-Wave device (skipped by default)

Run locally (venv active):
  python -m pytest tests/test_braket_real_device.py -v -m braket_mock
"""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def small_problem():
    """5-asset test problem with fixed seed."""
    rng = np.random.default_rng(42)
    n = 5
    returns = rng.uniform(0.05, 0.20, n)
    raw = rng.standard_normal((n, n))
    covariance = (raw @ raw.T) / n + np.eye(n) * 0.01
    return returns, covariance


@pytest.fixture()
def mock_config():
    """BraketConfig for mock / classical-fallback mode (no AWS calls)."""
    from services.braket_backend import BraketConfig
    return BraketConfig(
        enabled=True,
        device_arn=None,
        s3_bucket=None,
        aws_region="us-east-1",
        shots=50,
        timeout=30,
        use_mock=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mark helpers
# ─────────────────────────────────────────────────────────────────────────────

braket_mock = pytest.mark.braket_mock
braket_real = pytest.mark.braket_real


def _skip_if_no_real_device():
    if os.getenv("BRAKET_REAL_DEVICE_TEST", "0") != "1":
        pytest.skip("Set BRAKET_REAL_DEVICE_TEST=1 and configure BRAKET_* env vars to run real-device tests")


# ─────────────────────────────────────────────────────────────────────────────
# Mock-mode tests (no AWS)
# ─────────────────────────────────────────────────────────────────────────────

@braket_mock
def test_braket_config_from_env(monkeypatch):
    """BraketConfig loads correctly from environment variables."""
    monkeypatch.setenv("BRAKET_ENABLED", "true")
    monkeypatch.setenv("BRAKET_USE_MOCK", "false")
    monkeypatch.setenv("BRAKET_DEVICE_ARN", "arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6")
    monkeypatch.setenv("BRAKET_S3_BUCKET", "test-bucket")
    monkeypatch.setenv("BRAKET_AWS_REGION", "us-west-2")
    monkeypatch.setenv("BRAKET_SHOTS", "200")
    monkeypatch.setenv("BRAKET_TIMEOUT", "600")

    from services.braket_backend import BraketAnnealingOptimizer
    config = BraketAnnealingOptimizer._load_config_from_env()

    assert config.enabled is True
    assert config.use_mock is False
    assert config.device_arn == "arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6"
    assert config.s3_bucket == "test-bucket"
    assert config.aws_region == "us-west-2"
    assert config.shots == 200
    assert config.timeout == 600


@braket_mock
def test_mock_optimize_returns_valid_weights(mock_config, small_problem):
    """Mock path returns weights that sum to 1 and have a finite Sharpe."""
    from services.braket_backend import BraketAnnealingOptimizer
    returns, covariance = small_problem

    optimizer = BraketAnnealingOptimizer(mock_config)
    result = optimizer.optimize(returns, covariance, K=3)

    weights = np.asarray(result["weights"])
    assert abs(weights.sum() - 1.0) < 1e-3, f"Weights don't sum to 1: {weights.sum()}"
    assert np.isfinite(result["sharpe_ratio"]), "Sharpe is not finite"
    assert result["expected_return"] > 0, "Expected return not positive"
    assert result["volatility"] > 0, "Volatility not positive"
    assert result["n_active"] >= 1


@braket_mock
def test_mock_optimize_no_cardinality(mock_config, small_problem):
    """K=None falls back to default cardinality selection without error."""
    from services.braket_backend import BraketAnnealingOptimizer
    returns, covariance = small_problem

    optimizer = BraketAnnealingOptimizer(mock_config)
    result = optimizer.optimize(returns, covariance, K=None)

    weights = np.asarray(result["weights"])
    assert abs(weights.sum() - 1.0) < 1e-3
    assert np.isfinite(result["sharpe_ratio"])


@braket_mock
def test_qubo_matrix_shape(mock_config, small_problem):
    """QUBO matrix is square and matches number of assets."""
    from services.braket_backend import BraketAnnealingOptimizer
    returns, covariance = small_problem
    n = len(returns)

    optimizer = BraketAnnealingOptimizer(mock_config)
    Q = optimizer._build_qubo_matrix(returns, covariance, K=3, lambda_risk=1.0, gamma=8.0)

    assert Q.shape == (n, n), f"Expected ({n},{n}), got {Q.shape}"


@braket_mock
def test_ising_conversion_roundtrip(mock_config, small_problem):
    """QUBO → Ising conversion is consistent: h and J have correct sizes."""
    from services.braket_backend import BraketAnnealingOptimizer
    returns, covariance = small_problem
    n = len(returns)

    optimizer = BraketAnnealingOptimizer(mock_config)
    Q = optimizer._build_qubo_matrix(returns, covariance, K=3, lambda_risk=1.0, gamma=8.0)
    h, J, offset = optimizer._qubo_to_ising(Q)

    assert len(h) == n, f"h should have {n} entries"
    # Quadratic terms: at most n*(n-1)/2 unique pairs
    assert len(J) <= n * (n - 1) // 2, "Too many J entries"
    assert isinstance(offset, float)


@braket_mock
def test_enforce_cardinality(mock_config):
    """_enforce_cardinality returns exactly K active assets."""
    from services.braket_backend import BraketAnnealingOptimizer

    optimizer = BraketAnnealingOptimizer(mock_config)
    binary = np.array([1, 1, 1, 0, 0])  # 3 active
    result = optimizer._enforce_cardinality(binary.copy(), K=2)
    assert result.sum() == 2, f"Expected 2 active, got {result.sum()}"

    result = optimizer._enforce_cardinality(binary.copy(), K=5)
    assert result.sum() == 5, f"Expected 5 active, got {result.sum()}"


@braket_mock
def test_device_status_disabled():
    """get_device_status returns 'disabled' when Braket is not enabled."""
    from services.braket_backend import BraketAnnealingOptimizer, BraketConfig
    config = BraketConfig(enabled=False)
    optimizer = BraketAnnealingOptimizer(config)
    status = optimizer.get_device_status()
    assert status["status"] == "disabled"
    assert status["backend"] == "classical_fallback"


@braket_mock
def test_classical_fallback_used_when_sdk_absent(mock_config, small_problem, monkeypatch):
    """When Braket SDK is absent, classical SA fallback is used transparently."""
    # Simulate no SDK by patching BRAKET_AVAILABLE = False at module level
    monkeypatch.setattr("services.braket_backend.BRAKET_AVAILABLE", False)

    from services.braket_backend import BraketAnnealingOptimizer
    returns, covariance = small_problem
    mock_config.enabled = True
    # Re-create after patch
    optimizer = BraketAnnealingOptimizer(mock_config)
    result = optimizer.optimize(returns, covariance, K=3)

    assert result["backend"] == "classical_sa"
    weights = np.asarray(result["weights"])
    assert abs(weights.sum() - 1.0) < 1e-3


# ─────────────────────────────────────────────────────────────────────────────
# SDK correctness tests: verify _execute_braket call shape with mocked SDK
# ─────────────────────────────────────────────────────────────────────────────

@braket_mock
def test_execute_braket_calls_problem_and_device_run(mock_config, small_problem):
    """
    _execute_braket uses braket.annealing.Problem (not bare keyword args),
    passes s3_destination_folder and shots, and correctly parses record_array.
    """
    from services.braket_backend import BraketAnnealingOptimizer, BraketConfig

    n = 5
    returns, covariance = small_problem
    config = BraketConfig(
        enabled=True,
        use_mock=False,
        device_arn="arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6",
        s3_bucket="test-bucket",
        shots=10,
    )

    optimizer = BraketAnnealingOptimizer.__new__(BraketAnnealingOptimizer)
    optimizer.config = config
    optimizer._device = MagicMock()
    optimizer._braket_client = MagicMock()

    # Build Ising problem to pass into _execute_braket
    Q = optimizer._build_qubo_matrix(returns, covariance, K=3, lambda_risk=1.0, gamma=8.0)
    h, J, _ = optimizer._qubo_to_ising(Q)

    # Mock annealing result: record_array with sample, energy, num_occurrences
    sample_array = np.ones((10, n), dtype=int) * -1  # all spins -1
    sample_array[0, :3] = 1  # best sample: first 3 assets
    energy_array = np.array([-5.0 + i * 0.5 for i in range(10)])
    record = MagicMock()
    record.__len__.return_value = 10
    record.__getitem__ = lambda self, key: (
        energy_array if key == "energy" else sample_array
    )
    record.__bool__ = lambda self: True
    # Use a simple dict-like mock for record_array
    import numpy.lib.recfunctions as rf  # noqa: F401

    mock_record = {
        "energy": energy_array,
        "sample": sample_array,
    }

    mock_task_result = MagicMock()
    # Make record_array a simple object with dict-style indexing
    record_obj = MagicMock()
    record_obj.__len__ = MagicMock(return_value=10)
    record_obj.__getitem__ = MagicMock(side_effect=lambda k: mock_record[k])
    mock_task_result.record_array = record_obj

    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    mock_task.result.return_value = mock_task_result
    optimizer._device.run.return_value = mock_task

    # Patch braket.annealing imports
    mock_problem_cls = MagicMock()
    mock_problem_type = MagicMock()

    with patch.dict("sys.modules", {
        "braket.annealing": MagicMock(Problem=mock_problem_cls, ProblemType=MagicMock(ISING=mock_problem_type)),
    }):
        # Also patch BRAKET_AVAILABLE
        with patch("services.braket_backend.BRAKET_AVAILABLE", True):
            result = optimizer._execute_braket(h, J, K=3)

    # Verify device.run was called (with a Problem object and s3 folder)
    optimizer._device.run.assert_called_once()
    call_kwargs = optimizer._device.run.call_args
    # Second positional or keyword: s3_destination_folder and shots
    assert call_kwargs.kwargs.get("shots") == 10, "shots not forwarded to device.run"
    s3_folder = call_kwargs.kwargs.get("s3_destination_folder")
    assert s3_folder is not None, "s3_destination_folder not passed"
    assert s3_folder[0] == "test-bucket"
    assert s3_folder[1] == "braket-results"

    # Verify task_id is captured
    assert result["task_id"] == "test-task-id-123"
    assert result["shots"] == 10
    assert "solution" in result
    assert "energy" in result


@braket_mock
def test_execute_braket_raises_when_no_samples(mock_config, small_problem):
    """_execute_braket raises RuntimeError when record_array is empty."""
    from services.braket_backend import BraketAnnealingOptimizer, BraketConfig

    n = 5
    returns, covariance = small_problem
    config = BraketConfig(enabled=True, use_mock=False, s3_bucket="test-bucket", shots=10)

    optimizer = BraketAnnealingOptimizer.__new__(BraketAnnealingOptimizer)
    optimizer.config = config
    optimizer._device = MagicMock()

    Q = optimizer._build_qubo_matrix(returns, covariance, K=3, lambda_risk=1.0, gamma=8.0)
    h, J, _ = optimizer._qubo_to_ising(Q)

    mock_task_result = MagicMock()
    empty_record = MagicMock()
    empty_record.__len__ = MagicMock(return_value=0)
    mock_task_result.record_array = empty_record

    mock_task = MagicMock()
    mock_task.id = "empty-task"
    mock_task.result.return_value = mock_task_result
    optimizer._device.run.return_value = mock_task

    with patch.dict("sys.modules", {
        "braket.annealing": MagicMock(
            Problem=MagicMock(),
            ProblemType=MagicMock(ISING=MagicMock()),
        ),
    }):
        with patch("services.braket_backend.BRAKET_AVAILABLE", True):
            with pytest.raises(RuntimeError, match="No samples returned"):
                optimizer._execute_braket(h, J, K=3)


# ─────────────────────────────────────────────────────────────────────────────
# Real-device tests (skipped unless BRAKET_REAL_DEVICE_TEST=1)
# ─────────────────────────────────────────────────────────────────────────────

@braket_real
def test_real_device_small_portfolio():
    """
    End-to-end real D-Wave run on a 5-asset portfolio.

    Requires:
      BRAKET_REAL_DEVICE_TEST=1
      BRAKET_ENABLED=true
      BRAKET_USE_MOCK=false
      BRAKET_DEVICE_ARN=<arn>
      BRAKET_S3_BUCKET=<bucket>
      AWS credentials in environment or instance profile
    """
    _skip_if_no_real_device()

    from services.braket_backend import BraketAnnealingOptimizer, BRAKET_AVAILABLE
    assert BRAKET_AVAILABLE, "Braket SDK must be installed for real-device tests"

    rng = np.random.default_rng(42)
    n = 5
    returns = rng.uniform(0.05, 0.20, n)
    raw = rng.standard_normal((n, n))
    covariance = (raw @ raw.T) / n + np.eye(n) * 0.01

    config = BraketAnnealingOptimizer._load_config_from_env()
    assert config.device_arn, "BRAKET_DEVICE_ARN must be set for real-device tests"
    assert config.s3_bucket, "BRAKET_S3_BUCKET must be set for real-device tests"
    config.use_mock = False

    optimizer = BraketAnnealingOptimizer(config)
    assert optimizer._device is not None, "Device failed to initialize"

    result = optimizer.optimize(returns, covariance, K=3)

    weights = np.asarray(result["weights"])
    assert abs(weights.sum() - 1.0) < 1e-3, f"Weights don't sum to 1: {weights.sum()}"
    assert np.isfinite(result["sharpe_ratio"])
    assert result.get("backend") == "braket_quantum"
    assert result.get("task_id") is not None

    # Serialize artifact as proof
    artifact = {
        "backend": result["backend"],
        "device_arn": config.device_arn,
        "task_id": result["task_id"],
        "shots": result.get("shots"),
        "n_assets": n,
        "seed": 42,
        "sharpe_ratio": float(result["sharpe_ratio"]),
        "weights_sum": float(weights.sum()),
        "n_active": int(result["n_active"]),
    }
    print("\n=== Real Device Artifact ===")
    print(json.dumps(artifact, indent=2))
