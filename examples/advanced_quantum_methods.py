#!/usr/bin/env python3
"""
Example demonstrating notebook-based portfolio optimization methods.
Shows hybrid pipeline, QUBO-SA, VQE, and classical optimizers.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from services.portfolio_optimizer import run_optimization


def generate_test_data(n_assets=10):
    """Generate test portfolio data."""
    np.random.seed(42)

    returns = np.random.randn(n_assets) * 0.1 + 0.05
    A = np.random.randn(n_assets, n_assets) * 0.3
    for i in range(n_assets):
        for j in range(i+1, n_assets):
            A[i, j] += 0.1 * np.exp(-abs(i-j)/5)
            A[j, i] += 0.1 * np.exp(-abs(i-j)/5)
    covariance = np.dot(A.T, A) / n_assets

    return returns, covariance


def compare_optimization_methods():
    """Compare different portfolio optimization methods."""
    print("="*60)
    print("COMPARING OPTIMIZATION METHODS")
    print("="*60)

    returns, covariance = generate_test_data(n_assets=15)

    methods = [
        ('Hybrid Pipeline', 'hybrid'),
        ('QUBO-SA', 'qubo_sa'),
        ('VQE', 'vqe'),
        ('Markowitz (Max Sharpe)', 'markowitz'),
        ('Min Variance', 'min_variance'),
        ('HRP', 'hrp'),
        ('Equal Weight', 'equal_weight'),
    ]

    results = []
    for name, objective in methods:
        result = run_optimization(returns, covariance, objective=objective)
        results.append((name, result.sharpe_ratio, result.expected_return, result.volatility))

    print(f"\n{'Method':<25} {'Sharpe':>10} {'Return':>10} {'Volatility':>10}")
    print("-" * 58)
    for name, sharpe, ret, vol in sorted(results, key=lambda x: -x[1]):
        print(f"{name:<25} {sharpe:>10.3f} {ret*100:>9.2f}% {vol*100:>9.2f}%")


def demonstrate_hybrid_large_portfolio():
    """Demonstrate hybrid pipeline on larger portfolios."""
    print("\n" + "="*60)
    print("DEMONSTRATING LARGE PORTFOLIO OPTIMIZATION")
    print("="*60)

    returns, covariance = generate_test_data(n_assets=50)
    result = run_optimization(returns, covariance, objective='hybrid')

    print(f"Large Portfolio (50 assets) - Hybrid pipeline:")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.3f}")
    print(f"  Expected Return: {result.expected_return*100:.2f}%")
    print(f"  Volatility: {result.volatility*100:.2f}%")
    print(f"  Active Assets: {result.n_active}")
    top_idx = np.argsort(result.weights)[-5:][::-1]
    top_w = np.sort(result.weights)[-5:][::-1]
    print(f"  Top 5 Holdings: {top_idx}")
    print(f"  Top 5 Weights: {[f'{w*100:.2f}%' for w in top_w]}")


def show_available_methods():
    """Show available methods and their descriptions."""
    print("\n" + "="*60)
    print("AVAILABLE OPTIMIZATION METHODS")
    print("="*60)

    from services.portfolio_optimizer import OBJECTIVES
    for obj_id, description in OBJECTIVES.items():
        print(f"\n  {obj_id}:")
        print(f"    {description}")


def main():
    """Run all demonstrations."""
    print("Portfolio Optimization Demo")
    print("Notebook-based methods (Hybrid, QUBO-SA, VQE) and classical optimizers.\n")

    show_available_methods()
    compare_optimization_methods()
    demonstrate_hybrid_large_portfolio()

    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nThe optimization system includes:")
    print("  • Hybrid 3-stage pipeline")
    print("  • QUBO + Simulated Annealing")
    print("  • VQE PauliTwoDesign")
    print("  • Classical: Markowitz, Min Variance, HRP, Equal Weight")


if __name__ == "__main__":
    main()
