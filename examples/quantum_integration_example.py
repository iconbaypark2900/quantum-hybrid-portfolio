#!/usr/bin/env python3
"""
Quantum Integration Example

Demonstrates integration of portfolio optimization methods using
the unified run_optimization service:

1. Hybrid pipeline (3-stage quantum-inspired)
2. QUBO + Simulated Annealing
3. Hierarchical Risk Parity (HRP)
4. Classical methods (Markowitz, min-variance, risk parity)

This example shows how to use the quantum hybrid portfolio system
for real-world portfolio optimization tasks.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any
import json

from services.portfolio_optimizer import run_optimization


def generate_sample_portfolio(n_assets: int = 10, seed: int = 42) -> Dict[str, np.ndarray]:
    """
    Generate sample portfolio data for demonstration.

    Args:
        n_assets: Number of assets
        seed: Random seed for reproducibility

    Returns:
        Dictionary with 'returns', 'covariance', and 'asset_names'
    """
    np.random.seed(seed)

    # Generate realistic returns (5-15% annualized)
    returns = np.random.uniform(0.05, 0.15, n_assets)

    # Generate realistic covariance matrix
    volatilities = np.random.uniform(0.10, 0.30, n_assets)
    random_matrix = np.random.randn(n_assets, n_assets)
    correlation = np.corrcoef(random_matrix)
    correlation = (correlation + correlation.T) / 2
    np.fill_diagonal(correlation, 1.0)
    covariance = np.outer(volatilities, volatilities) * correlation

    asset_names = [f"ASSET_{i:02d}" for i in range(n_assets)]

    return {
        'returns': returns,
        'covariance': covariance,
        'asset_names': asset_names,
    }


def example_hybrid_optimization(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 1: Hybrid Pipeline Optimization

    The 3-stage hybrid pipeline combines screening, quantum-inspired
    selection, and optimization for robust portfolios.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: HYBRID PIPELINE OPTIMIZATION")
    print("="*70)

    returns = data['returns']
    covariance = data['covariance']

    result = run_optimization(returns, covariance, objective='hybrid')

    print(f"\nHybrid Results:")
    print(f"  Sharpe Ratio:    {result.sharpe_ratio:.3f}")
    print(f"  Expected Return: {result.expected_return*100:.2f}%")
    print(f"  Volatility:      {result.volatility*100:.2f}%")
    print(f"  Active Assets:   {result.n_active}")

    return {
        'sharpe_ratio': result.sharpe_ratio,
        'expected_return': result.expected_return,
        'volatility': result.volatility,
        'n_active': result.n_active,
    }


def example_qubo_sa_optimization(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 2: QUBO + Simulated Annealing

    QUBO-based portfolio optimization with classical simulated annealing.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: QUBO + SIMULATED ANNEALING")
    print("="*70)

    returns = data['returns']
    covariance = data['covariance']

    result = run_optimization(returns, covariance, objective='qubo_sa')

    print(f"\nQUBO-SA Results:")
    print(f"  Sharpe Ratio:    {result.sharpe_ratio:.3f}")
    print(f"  Expected Return: {result.expected_return*100:.2f}%")
    print(f"  Volatility:      {result.volatility*100:.2f}%")
    print(f"  Active Assets:   {result.n_active}")

    return {
        'sharpe_ratio': result.sharpe_ratio,
        'expected_return': result.expected_return,
        'volatility': result.volatility,
        'n_active': result.n_active,
    }


def example_hrp_optimization(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 3: Hierarchical Risk Parity

    HRP based on López de Prado (2016). Uses clustering to allocate
    risk across hierarchical asset groups.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: HIERARCHICAL RISK PARITY")
    print("="*70)

    returns = data['returns']
    covariance = data['covariance']

    result = run_optimization(returns, covariance, objective='hrp')

    print(f"\nHRP Results:")
    print(f"  Sharpe Ratio:    {result.sharpe_ratio:.3f}")
    print(f"  Expected Return: {result.expected_return*100:.2f}%")
    print(f"  Volatility:      {result.volatility*100:.2f}%")
    print(f"  Active Assets:   {result.n_active}")

    weights = result.weights
    print(f"\nWeight Statistics:")
    active = weights[weights > 0]
    if len(active) > 0:
        print(f"  Max Weight:  {np.max(active)*100:.2f}%")
        print(f"  Min Weight:  {np.min(active)*100:.2f}%")
        print(f"  Mean Weight: {np.mean(active)*100:.2f}%")

    return {
        'sharpe_ratio': result.sharpe_ratio,
        'expected_return': result.expected_return,
        'volatility': result.volatility,
        'n_active': result.n_active,
        'weights': weights,
    }


def example_unified_service(data: Dict[str, np.ndarray]) -> None:
    """
    Example 4: Unified Optimization Service

    Demonstrates the unified service interface supporting multiple objectives.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: UNIFIED OPTIMIZATION SERVICE")
    print("="*70)

    returns = data['returns']
    covariance = data['covariance']

    objectives = ['markowitz', 'min_variance', 'hrp', 'hybrid', 'qubo_sa', 'vqe']

    print(f"\nComparing optimization objectives:")
    print(f"{'Objective':<20} {'Sharpe':>10} {'Return':>10} {'Volatility':>12} {'Active':>8}")
    print("-" * 62)

    for objective in objectives:
        result = run_optimization(returns, covariance, objective=objective)
        print(f"{objective:<20} {result.sharpe_ratio:>10.3f} "
              f"{result.expected_return*100:>9.2f}% "
              f"{result.volatility*100:>11.2f}% "
              f"{result.n_active:>8}")


def compare_all_methods(data: Dict[str, np.ndarray]) -> None:
    """
    Compare all optimization methods side-by-side.
    """
    print("\n" + "="*70)
    print("COMPARISON: ALL OPTIMIZATION METHODS")
    print("="*70)

    returns = data['returns']
    covariance = data['covariance']

    methods = [
        ('Hybrid', 'hybrid'),
        ('QUBO-SA', 'qubo_sa'),
        ('VQE', 'vqe'),
        ('HRP', 'hrp'),
        ('Markowitz', 'markowitz'),
        ('Min Variance', 'min_variance'),
    ]

    results = []
    for name, obj in methods:
        r = run_optimization(returns, covariance, objective=obj)
        results.append((name, r.sharpe_ratio, r.expected_return, r.volatility))

    # Equal Weight baseline
    n = len(returns)
    ew_weights = np.ones(n) / n
    ew_return = np.dot(ew_weights, returns)
    ew_vol = np.sqrt(ew_weights @ covariance @ ew_weights)
    ew_sharpe = ew_return / ew_vol if ew_vol > 0 else 0
    results.append(('Equal Weight', ew_sharpe, ew_return, ew_vol))

    print(f"\n{'Method':<20} {'Sharpe Ratio':>12} {'Return':>12} {'Volatility':>12}")
    print("-" * 58)
    for name, sharpe, ret, vol in sorted(results, key=lambda x: -x[1]):
        print(f"{name:<20} {sharpe:>12.3f} {ret*100:>11.2f}% {vol*100:>11.2f}%")


def main():
    """Run all integration examples."""
    print("\n" + "="*70)
    print("QUANTUM HYBRID PORTFOLIO - INTEGRATION EXAMPLES")
    print("="*70)

    print("\nGenerating sample portfolio data...")
    data = generate_sample_portfolio(n_assets=15, seed=42)

    print(f"Created portfolio with {len(data['asset_names'])} assets")
    print(f"Expected returns: {data['returns'].mean()*100:.2f}% (mean)")
    print(f"Volatility:       {np.sqrt(np.diag(data['covariance'])).mean()*100:.2f}% (mean)")

    example_hybrid_optimization(data)
    example_qubo_sa_optimization(data)
    example_hrp_optimization(data)
    example_unified_service(data)
    compare_all_methods(data)

    print("\n" + "="*70)
    print("INTEGRATION EXAMPLES COMPLETE")
    print("="*70)
    print("\nAll portfolio optimization methods are working correctly!")
    print("\nNext steps:")
    print("  1. Try the interactive dashboard: cd frontend && npm start")
    print("  2. Start the API server: python middleware/api.py")
    print("  3. Explore more examples in examples/")


if __name__ == "__main__":
    main()
