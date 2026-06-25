#!/usr/bin/env python3
"""
Braket / D-Wave end-to-end validation script.

Runs the full mock → real device ladder as documented in
docs/BRAKET_AWS_SETUP.md (Phase 2 of the quantum hardware validation plan).

Each step emits a JSON artifact containing:
  - backend, device_arn, shots, seed, n_assets (workspace metadata conventions)
  - task_id (real device), timing, portfolio weights, Sharpe

Usage (see --help):
    # Step 1: imports + health (no AWS calls)
    python scripts/braket_validate.py --check-imports

    # Step 2: mock path (classical SA, no AWS calls)
    BRAKET_ENABLED=true BRAKET_USE_MOCK=true \\
        python scripts/braket_validate.py --n 5 --seed 42

    # Step 3: real D-Wave device
    BRAKET_ENABLED=true BRAKET_USE_MOCK=false \\
        BRAKET_DEVICE_ARN=arn:aws:braket:us-east-1::device/qpu/d-wave/Advantage_system6 \\
        BRAKET_S3_BUCKET=your-bucket-name \\
        python scripts/braket_validate.py --n 5 --seed 42 \\
            --output artifacts/braket_run_$(date +%Y%m%d).json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _make_test_problem(n: int, seed: int):
    """Generate a reproducible n-asset returns + covariance matrix."""
    rng = np.random.default_rng(seed)
    returns = rng.uniform(0.05, 0.20, n)
    raw = rng.standard_normal((n, n))
    covariance = (raw @ raw.T) / n + np.eye(n) * 0.01  # PSD guarantee
    return returns, covariance


def _write_artifact(artifact: dict, output_path: str | None) -> None:
    """Write JSON artifact to stdout and optionally to a file."""
    text = json.dumps(artifact, indent=2, default=str)
    print("\n=== Artifact ===")
    print(text)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"\nArtifact saved to: {path.resolve()}")


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: import + health check
# ─────────────────────────────────────────────────────────────────────────────

def step_check_imports() -> dict:
    """Verify SDK imports and env configuration without making any AWS calls."""
    print("\n[Step 1] Checking imports and environment...\n")
    result = {
        "step": "check_imports",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Braket SDK
    try:
        import braket  # noqa: F401
        import boto3    # noqa: F401
        result["braket_sdk_installed"] = True
        try:
            import importlib.metadata
            result["braket_sdk_version"] = importlib.metadata.version("amazon-braket-sdk")
        except Exception:
            result["braket_sdk_version"] = "unknown"
    except ImportError as exc:
        result["braket_sdk_installed"] = False
        result["braket_sdk_error"] = str(exc)

    # Project backend
    try:
        from services.braket_backend import BraketAnnealingOptimizer, BRAKET_AVAILABLE  # noqa: F401
        result["project_braket_backend"] = "ok"
        result["project_braket_available"] = BRAKET_AVAILABLE
    except Exception as exc:
        result["project_braket_backend"] = "error"
        result["project_braket_error"] = str(exc)

    # Env vars
    result["env"] = {
        "BRAKET_ENABLED": os.getenv("BRAKET_ENABLED", "false"),
        "BRAKET_USE_MOCK": os.getenv("BRAKET_USE_MOCK", "true"),
        "BRAKET_DEVICE_ARN": os.getenv("BRAKET_DEVICE_ARN", "<not set>"),
        "BRAKET_S3_BUCKET": os.getenv("BRAKET_S3_BUCKET", "<not set>"),
        "BRAKET_AWS_REGION": os.getenv("BRAKET_AWS_REGION", "us-east-1"),
        "BRAKET_SHOTS": os.getenv("BRAKET_SHOTS", "100"),
        "BRAKET_TIMEOUT": os.getenv("BRAKET_TIMEOUT", "300"),
    }

    result["ok"] = (
        result.get("braket_sdk_installed", False)
        and result.get("project_braket_backend") == "ok"
    )

    status = "PASS" if result["ok"] else "FAIL (SDK not installed — mock path still usable)"
    print(f"  Braket SDK installed : {result.get('braket_sdk_installed')}")
    print(f"  Project backend      : {result.get('project_braket_backend')}")
    print(f"  BRAKET_ENABLED       : {result['env']['BRAKET_ENABLED']}")
    print(f"  BRAKET_USE_MOCK      : {result['env']['BRAKET_USE_MOCK']}")
    print(f"  BRAKET_DEVICE_ARN    : {result['env']['BRAKET_DEVICE_ARN']}")
    print(f"\n  Status: {status}\n")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: mock path
# ─────────────────────────────────────────────────────────────────────────────

def step_mock(n: int, seed: int) -> dict:
    """
    Run BraketAnnealingOptimizer in mock mode (BRAKET_USE_MOCK=true).
    No AWS credentials or device ARN required.
    """
    print(f"\n[Step 2] Mock path  n={n} seed={seed}...\n")
    from services.braket_backend import BraketAnnealingOptimizer, BraketConfig

    config = BraketAnnealingOptimizer._load_config_from_env()
    if not config.enabled:
        print("  BRAKET_ENABLED is false — setting to true for mock run.")
        config.enabled = True
    config.use_mock = True  # force mock regardless of env

    returns, covariance = _make_test_problem(n, seed)
    optimizer = BraketAnnealingOptimizer(config)

    t0 = time.perf_counter()
    result = optimizer.optimize(returns, covariance, K=max(2, n // 2))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    weights = result["weights"]
    weights_sum = float(np.sum(weights))
    n_active = int(np.sum(np.asarray(weights) > 1e-4))

    sharpe = result.get("sharpe_ratio")
    artifact = {
        "step": "mock",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": result.get("backend", "unknown"),
        "device": result.get("device", "mock"),
        "n_assets": n,
        "seed": seed,
        "shots": config.shots,
        "elapsed_ms": elapsed_ms,
        "weights_sum": weights_sum,
        "n_active": n_active,
        "sharpe_ratio": float(sharpe) if sharpe is not None else None,
        "expected_return": float(result["expected_return"]) if result.get("expected_return") is not None else None,
        "volatility": float(result["volatility"]) if result.get("volatility") is not None else None,
        "weights": [float(w) for w in weights],
        "ok": bool(abs(weights_sum - 1.0) < 1e-3 and sharpe is not None and np.isfinite(sharpe)),
    }

    status = "PASS" if artifact["ok"] else "FAIL"
    print(f"  Backend      : {artifact['backend']}")
    print(f"  Weights sum  : {weights_sum:.6f}")
    print(f"  Sharpe       : {artifact['sharpe_ratio']:.4f}")
    print(f"  Active assets: {n_active}/{n}")
    print(f"  Elapsed      : {elapsed_ms} ms")
    print(f"\n  Status: {status}\n")
    return artifact


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: real device
# ─────────────────────────────────────────────────────────────────────────────

def step_real_device(n: int, seed: int) -> dict:
    """
    Run BraketAnnealingOptimizer against the configured real D-Wave QPU.

    Requires:
      BRAKET_ENABLED=true
      BRAKET_USE_MOCK=false
      BRAKET_DEVICE_ARN=<arn>
      BRAKET_S3_BUCKET=<bucket>
      Valid AWS credentials in environment or instance profile.
    """
    print(f"\n[Step 3] Real device  n={n} seed={seed}...\n")

    device_arn = os.getenv("BRAKET_DEVICE_ARN", "")
    s3_bucket = os.getenv("BRAKET_S3_BUCKET", "")

    if not device_arn:
        return {
            "step": "real_device",
            "ok": False,
            "error": "BRAKET_DEVICE_ARN is not set. Set it to a D-Wave QPU ARN.",
        }
    if not s3_bucket:
        return {
            "step": "real_device",
            "ok": False,
            "error": "BRAKET_S3_BUCKET is not set.",
        }

    from services.braket_backend import BraketAnnealingOptimizer, BRAKET_AVAILABLE

    if not BRAKET_AVAILABLE:
        return {
            "step": "real_device",
            "ok": False,
            "error": "Amazon Braket SDK not installed. Run: pip install amazon-braket-sdk",
        }

    config = BraketAnnealingOptimizer._load_config_from_env()
    config.use_mock = False  # ensure real path

    returns, covariance = _make_test_problem(n, seed)
    optimizer = BraketAnnealingOptimizer(config)

    if not optimizer._device:
        return {
            "step": "real_device",
            "ok": False,
            "error": "Device failed to initialize. Check AWS credentials and device ARN.",
            "device_arn": device_arn,
        }

    t0 = time.perf_counter()
    try:
        result = optimizer.optimize(returns, covariance, K=max(2, n // 2))
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "step": "real_device",
            "ok": False,
            "error": str(exc),
            "device_arn": device_arn,
            "elapsed_ms": elapsed_ms,
        }

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    weights = result["weights"]
    weights_sum = float(np.sum(weights))
    n_active = int(np.sum(np.asarray(weights) > 1e-4))

    sharpe = result.get("sharpe_ratio")
    artifact = {
        "step": "real_device",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend": result.get("backend", "unknown"),
        "device": result.get("device", device_arn),
        "device_arn": device_arn,
        "n_assets": n,
        "seed": seed,
        "shots": int(result.get("shots", config.shots)),
        "task_id": result.get("task_id"),
        "energy": float(result["energy"]) if result.get("energy") is not None else None,
        "elapsed_ms": elapsed_ms,
        "weights_sum": weights_sum,
        "n_active": n_active,
        "sharpe_ratio": float(sharpe) if sharpe is not None else None,
        "expected_return": float(result["expected_return"]) if result.get("expected_return") is not None else None,
        "volatility": float(result["volatility"]) if result.get("volatility") is not None else None,
        "weights": [float(w) for w in weights],
        "ok": bool(abs(weights_sum - 1.0) < 1e-3 and sharpe is not None and np.isfinite(sharpe)),
    }

    status = "PASS" if artifact["ok"] else "FAIL"
    print(f"  Backend      : {artifact['backend']}")
    print(f"  Device ARN   : {device_arn}")
    print(f"  Task ID      : {artifact.get('task_id', 'n/a')}")
    print(f"  Weights sum  : {weights_sum:.6f}")
    print(f"  Sharpe       : {artifact['sharpe_ratio']:.4f}")
    print(f"  Active assets: {n_active}/{n}")
    print(f"  Energy       : {artifact.get('energy')}")
    print(f"  Elapsed      : {elapsed_ms} ms")
    print(f"\n  Status: {status}\n")
    return artifact


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Braket / D-Wave end-to-end validation ladder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--n", type=int, default=5, help="Number of assets (keep ≤ 10 for QPU)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default=None, help="Path to write JSON artifact")
    parser.add_argument("--check-imports", action="store_true", help="Only run Step 1 (import check)")
    parser.add_argument("--mock-only", action="store_true", help="Only run Steps 1–2 (no real device)")
    args = parser.parse_args()

    print("=" * 60)
    print("Braket / D-Wave Validation Ladder")
    print("=" * 60)

    steps_run = []
    all_ok = True

    # Step 1: always run
    r1 = step_check_imports()
    steps_run.append(r1)
    if not r1["ok"]:
        print("WARNING: Braket SDK not installed. Steps 2 and 3 will use the classical fallback.")

    if args.check_imports:
        _write_artifact({"steps": steps_run}, args.output)
        sys.exit(0 if r1["ok"] else 1)

    # Step 2: mock
    r2 = step_mock(args.n, args.seed)
    steps_run.append(r2)
    if not r2["ok"]:
        all_ok = False
        print("ERROR: Mock path failed. Fix before attempting real device.")

    if args.mock_only:
        _write_artifact({"steps": steps_run, "all_ok": r2["ok"]}, args.output)
        sys.exit(0 if r2["ok"] else 1)

    # Step 3: real device (only if BRAKET_USE_MOCK=false explicitly)
    use_mock_env = os.getenv("BRAKET_USE_MOCK", "true").lower()
    if use_mock_env == "false":
        r3 = step_real_device(args.n, args.seed)
        steps_run.append(r3)
        if not r3["ok"]:
            all_ok = False
    else:
        print("\n[Step 3] Skipped — BRAKET_USE_MOCK is not 'false'.")
        print("  Set BRAKET_USE_MOCK=false and provide BRAKET_DEVICE_ARN + BRAKET_S3_BUCKET")
        print("  to run against the real D-Wave QPU.\n")

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "all_ok": bool(all_ok),
        "steps": steps_run,
    }
    _write_artifact(summary, args.output)

    print("=" * 60)
    print(f"Overall: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
