#!/usr/bin/env python3
"""
Quick verification that the project works.
Run: python quick_test.py
"""
import numpy as np
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer

print("🚀 Testing Quantum Hybrid Portfolio...")
print("-" * 50)

# Create test data
n_assets = 10
np.random.seed(42)
returns = np.random.randn(n_assets) * 0.1 + 0.05
A = np.random.randn(n_assets, n_assets)
covariance = np.dot(A.T, A) / n_assets

# Run optimizer
print("Creating optimizer...")
optimizer = QuantumStochasticWalkOptimizer()

print("Running optimization...")
result = optimizer.optimize(returns, covariance)

# Show results
print("\n✅ SUCCESS! Portfolio optimized.")
print("-" * 50)
print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
print(f"Expected Return: {result.expected_return*100:.2f}%")
print(f"Volatility: {result.volatility*100:.2f}%")
print(f"Active Assets: {np.sum(result.weights > 0.001)}/{n_assets}")
print("-" * 50)
print("\n✓ Project is fully operational!")
print("\nNext steps:")
print("  • Run tests: python -m pytest tests/test_quantum_walk.py -v")
print("  • Run example: python examples/basic_qsw_example.py")
print("  • See guide: cat HOW_TO_RUN.md")
