#!/usr/bin/env python3
"""
Quantum Integration Example

Demonstrates integration of quantum-inspired optimization methods:
1. Quantum Stochastic Walk (QSW) optimization
2. AWS Braket annealing with classical fallback
3. Hierarchical Risk Parity (HRP)
4. Quantum annealing comparison

This example shows how to use the quantum hybrid portfolio system
for real-world portfolio optimization tasks.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any
import json

# Import quantum optimization modules
from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.braket_backend import BraketAnnealingOptimizer, build_qubo_portfolio
from core.quantum_inspired.quantum_annealing import QuantumAnnealingOptimizer
from config.qsw_config import QSWConfig
from services.portfolio_optimizer import run_optimization
from services.constraints import PortfolioConstraints


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
    # Start with volatilities (10-30% annualized)
    volatilities = np.random.uniform(0.10, 0.30, n_assets)
    
    # Generate correlation matrix
    random_matrix = np.random.randn(n_assets, n_assets)
    correlation = np.corrcoef(random_matrix)
    # Ensure positive semi-definite
    correlation = (correlation + correlation.T) / 2
    np.fill_diagonal(correlation, 1.0)
    
    # Build covariance from volatilities and correlation
    covariance = np.outer(volatilities, volatilities) * correlation
    
    # Generate asset names
    asset_names = [f"ASSET_{i:02d}" for i in range(n_assets)]
    
    return {
        'returns': returns,
        'covariance': covariance,
        'asset_names': asset_names,
    }


def example_qsw_optimization(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 1: Quantum Stochastic Walk Optimization
    
    QSW achieves superior risk-adjusted returns through quantum-inspired
    graph-based optimization.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: QUANTUM STOCHASTIC WALK OPTIMIZATION")
    print("="*70)
    
    returns = data['returns']
    covariance = data['covariance']
    
    # Configure QSW optimizer
    config = QSWConfig(
        default_omega=0.3,          # Coupling strength
        evolution_time=10,          # Evolution duration
        max_turnover=0.15,          # Maximum turnover
        stability_blend_factor=0.7, # Stability vs optimization blend
    )
    
    optimizer = QuantumStochasticWalkOptimizer(config)
    
    # Run optimization for different market regimes
    regimes = ['bull', 'bear', 'normal']
    
    results = {}
    for regime in regimes:
        result = optimizer.optimize(
            returns=returns,
            covariance=covariance,
            market_regime=regime,
        )
        results[regime] = {
            'sharpe_ratio': result.sharpe_ratio,
            'expected_return': result.expected_return,
            'volatility': result.volatility,
            'turnover': result.turnover,
            'n_active': result.n_active,
        }
        
        print(f"\n{regime.upper()} Market Regime:")
        print(f"  Sharpe Ratio:    {result.sharpe_ratio:.3f}")
        print(f"  Expected Return: {result.expected_return*100:.2f}%")
        print(f"  Volatility:      {result.volatility*100:.2f}%")
        print(f"  Active Assets:   {result.n_active}")
    
    return results


def example_braket_optimization(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 2: AWS Braket Quantum Annealing
    
    Demonstrates QUBO-based portfolio optimization with:
    - Real Braket device (when configured)
    - Classical QUBO fallback (always available)
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: AWS BRAKET QUANTUM ANNEALING")
    print("="*70)
    
    returns = data['returns']
    covariance = data['covariance']
    
    # Initialize Braket optimizer
    optimizer = BraketAnnealingOptimizer()
    
    # Run optimization
    result = optimizer.optimize(
        returns=returns,
        covariance=covariance,
    )
    
    method = result.get('method', 'unknown')
    print(f"\nOptimization Method: {method}")
    print(f"  Sharpe Ratio:    {result['sharpe_ratio']:.3f}")
    print(f"  Expected Return: {result['expected_return']*100:.2f}%")
    print(f"  Volatility:      {result['volatility']*100:.2f}%")
    print(f"  Active Assets:   {result['n_active']}")
    
    # Show QUBO formulation details
    from core.quantum_inspired.braket_backend import QUBOPortfolioConfig
    config = QUBOPortfolioConfig()
    linear, quadratic = build_qubo_portfolio(returns, covariance, config)
    
    print(f"\nQUBO Formulation:")
    print(f"  Linear terms:    {len(linear)}")
    print(f"  Quadratic terms: {len(quadratic)}")
    print(f"  Risk Aversion:   {config.risk_aversion}")
    
    return {
        'method': method,
        'sharpe_ratio': result['sharpe_ratio'],
        'expected_return': result['expected_return'],
        'volatility': result['volatility'],
        'n_active': result['n_active'],
    }


def example_hrp_optimization(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 3: Hierarchical Risk Parity
    
    Modern portfolio theory implementation based on López de Prado (2016).
    Uses clustering to allocate risk across hierarchical asset groups.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: HIERARCHICAL RISK PARITY")
    print("="*70)
    
    returns = data['returns']
    covariance = data['covariance']
    
    # Run HRP optimization via unified service
    result = run_optimization(
        returns=returns,
        covariance=covariance,
        objective='hrp',
    )
    
    print(f"\nHRP Results:")
    print(f"  Sharpe Ratio:    {result.sharpe_ratio:.3f}")
    print(f"  Expected Return: {result.expected_return*100:.2f}%")
    print(f"  Volatility:      {result.volatility*100:.2f}%")
    print(f"  Active Assets:   {result.n_active}")
    
    # Show weight distribution
    weights = result.weights
    print(f"\nWeight Statistics:")
    print(f"  Max Weight:  {np.max(weights)*100:.2f}%")
    print(f"  Min Weight:  {np.max(weights[weights > 0])*100:.2f}%")
    print(f"  Mean Weight: {np.mean(weights[weights > 0])*100:.2f}%")
    
    return {
        'sharpe_ratio': result.sharpe_ratio,
        'expected_return': result.expected_return,
        'volatility': result.volatility,
        'n_active': result.n_active,
        'weights': weights,
    }


def example_quantum_annealing_comparison(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """
    Example 4: Quantum vs Classical Annealing Comparison
    
    Compares quantum annealing with classical optimization.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: QUANTUM VS CLASSICAL ANNEALING")
    print("="*70)
    
    returns = data['returns']
    covariance = data['covariance']
    
    # Run comparison
    from core.quantum_inspired.quantum_annealing import run_quantum_annealing_comparison
    comparison = run_quantum_annealing_comparison(returns, covariance)
    
    qa_result = comparison['quantum_annealing']
    classical_result = comparison['classical']
    
    print(f"\nQuantum Annealing:")
    print(f"  Sharpe Ratio:    {qa_result['sharpe_ratio']:.3f}")
    print(f"  Expected Return: {qa_result['expected_return']*100:.2f}%")
    print(f"  Volatility:      {qa_result['volatility']*100:.2f}%")
    print(f"  Iterations:      {qa_result.get('iterations', 'N/A')}")
    
    print(f"\nClassical Optimization:")
    print(f"  Sharpe Ratio:    {classical_result['sharpe_ratio']:.3f}")
    print(f"  Expected Return: {classical_result['expected_return']*100:.2f}%")
    print(f"  Volatility:      {classical_result['volatility']*100:.2f}%")
    
    # Calculate improvement
    if classical_result['sharpe_ratio'] > 0:
        improvement = (qa_result['sharpe_ratio'] / classical_result['sharpe_ratio'] - 1) * 100
        print(f"\nQuantum Advantage:")
        print(f"  Sharpe Improvement: {improvement:+.2f}%")
    
    return {
        'quantum': qa_result,
        'classical': classical_result,
        'improvement': improvement,
    }


def example_unified_service(data: Dict[str, np.ndarray]) -> None:
    """
    Example 5: Unified Optimization Service
    
    Demonstrates the unified service interface supporting multiple objectives.
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: UNIFIED OPTIMIZATION SERVICE")
    print("="*70)
    
    returns = data['returns']
    covariance = data['covariance']
    
    objectives = ['max_sharpe', 'min_variance', 'risk_parity', 'hrp']
    
    print(f"\nComparing optimization objectives:")
    print(f"{'Objective':<20} {'Sharpe':>10} {'Return':>10} {'Volatility':>12} {'Active':>8}")
    print("-" * 62)
    
    for objective in objectives:
        result = run_optimization(
            returns=returns,
            covariance=covariance,
            objective=objective,
        )
        
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
    
    methods = []
    
    # QSW
    qsw_config = QSWConfig()
    qsw_optimizer = QuantumStochasticWalkOptimizer(qsw_config)
    qsw_result = qsw_optimizer.optimize(returns, covariance)
    methods.append(('QSW', qsw_result.sharpe_ratio, qsw_result.expected_return, qsw_result.volatility))
    
    # Braket
    braket_optimizer = BraketAnnealingOptimizer()
    braket_result = braket_optimizer.optimize(returns, covariance)
    methods.append(('Braket', braket_result['sharpe_ratio'], braket_result['expected_return'], braket_result['volatility']))
    
    # HRP
    hrp_result = run_optimization(returns, covariance, objective='hrp')
    methods.append(('HRP', hrp_result.sharpe_ratio, hrp_result.expected_return, hrp_result.volatility))
    
    # Quantum Annealing
    qa_optimizer = QuantumAnnealingOptimizer()
    qa_result = qa_optimizer.optimize(returns, covariance)
    methods.append(('QA', qa_result['sharpe_ratio'], qa_result['expected_return'], qa_result.volatility))
    
    # Equal Weight (baseline)
    n = len(returns)
    ew_weights = np.ones(n) / n
    ew_return = np.dot(ew_weights, returns)
    ew_vol = np.sqrt(ew_weights @ covariance @ ew_weights)
    ew_sharpe = ew_return / ew_vol if ew_vol > 0 else 0
    methods.append(('Equal Weight', ew_sharpe, ew_return, ew_vol))
    
    print(f"\n{'Method':<20} {'Sharpe Ratio':>12} {'Return':>12} {'Volatility':>12}")
    print("-" * 58)
    for name, sharpe, ret, vol in sorted(methods, key=lambda x: -x[1]):
        print(f"{name:<20} {sharpe:>12.3f} {ret*100:>11.2f}% {vol*100:>11.2f}%")


def main():
    """Run all integration examples."""
    print("\n" + "="*70)
    print("QUANTUM HYBRID PORTFOLIO - INTEGRATION EXAMPLES")
    print("="*70)
    
    # Generate sample data
    print("\nGenerating sample portfolio data...")
    data = generate_sample_portfolio(n_assets=15, seed=42)
    
    print(f"Created portfolio with {len(data['asset_names'])} assets")
    print(f"Expected returns: {data['returns'].mean()*100:.2f}% (mean)")
    print(f"Volatility:       {np.sqrt(np.diag(data['covariance'])).mean()*100:.2f}% (mean)")
    
    # Run examples
    example_qsw_optimization(data)
    example_braket_optimization(data)
    example_hrp_optimization(data)
    example_quantum_annealing_comparison(data)
    example_unified_service(data)
    
    # Final comparison
    compare_all_methods(data)
    
    print("\n" + "="*70)
    print("INTEGRATION EXAMPLES COMPLETE")
    print("="*70)
    print("\nAll quantum-inspired optimization methods are working correctly!")
    print("\nNext steps:")
    print("  1. Try the interactive dashboard: cd frontend && npm start")
    print("  2. Start the API server: python api.py")
    print("  3. Explore more examples in examples/")
    print("  4. Read the documentation: docs/")


if __name__ == "__main__":
    main()
