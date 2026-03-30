#!/usr/bin/env python3
"""
Local QA script for IBM Quantum portfolio optimization.

Runs qaoa_ibm objective on small test data, prints results, and optionally
saves a summary for talking points or demo documentation.

Usage:
    python scripts/run_ibm_qa.py
    IBM_QUANTUM_TOKEN="mXc9WbYpxz44ykVJLpW3nF7xdWlDZz9Tum1B9uKHuuYv" .venv/bin/python scripts/run_ibm_qa.py
    IBM_QUANTUM_BACKEND=simulator_stabilizer python scripts/run_ibm_qa.py --save results.json
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from services.portfolio_optimizer import run_optimization


def main() -> int:
    parser = argparse.ArgumentParser(description="Run IBM Quantum QAOA portfolio optimization QA")
    parser.add_argument(
        "--save",
        metavar="FILE",
        help="Save summary to JSON file (e.g. results.json)",
    )
    parser.add_argument(
        "--assets",
        type=int,
        default=10,
        help="Number of assets (default 10; keep small for hardware)",
    )
    args = parser.parse_args()

    # Small synthetic test data
    rng = np.random.default_rng(42)
    n = args.assets
    returns = rng.uniform(0.02, 0.12, n)
    cov_scale = rng.uniform(0.1, 0.3, (n, n))
    covariance = np.dot(cov_scale, cov_scale.T) + np.eye(n) * 0.01

    print("IBM Quantum QAOA — Local QA Run")
    print("=" * 50)
    print(f"Assets: {n}")
    print(f"IBM_QUANTUM_TOKEN: {'set' if os.environ.get('IBM_QUANTUM_TOKEN') else 'NOT SET (will use classical fallback)'}")
    print(f"IBM_QUANTUM_BACKEND: {os.environ.get('IBM_QUANTUM_BACKEND', '(auto)')}")
    print()

    t0 = time.perf_counter()
    result = run_optimization(
        returns,
        covariance,
        objective="qaoa_ibm",
        market_regime="normal",
    )
    elapsed = time.perf_counter() - t0

    print("Results")
    print("-" * 50)
    print(f"Objective:         {result.objective}")
    print(f"Backend:           {result.backend_type}")
    print(f"Sharpe ratio:      {result.sharpe_ratio:.4f}")
    print(f"Expected return:   {result.expected_return:.4f}")
    print(f"Volatility:       {result.volatility:.4f}")
    print(f"N active assets:   {result.n_active}")
    print(f"Runtime:           {elapsed:.2f}s")
    print()
    print("Weights:", np.round(result.weights, 4).tolist())

    summary = {
        "objective": result.objective,
        "backend_type": str(result.backend_type),
        "sharpe_ratio": float(result.sharpe_ratio),
        "expected_return": float(result.expected_return),
        "volatility": float(result.volatility),
        "n_active": result.n_active,
        "runtime_seconds": round(elapsed, 2),
        "n_assets": n,
        "weights": [float(w) for w in result.weights],
        "token_set": bool(os.environ.get("IBM_QUANTUM_TOKEN")),
    }

    if args.save:
        with open(args.save, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSaved summary to {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
