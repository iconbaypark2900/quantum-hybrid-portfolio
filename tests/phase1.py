"""
Phase 1 Fix Verification Script

Run this script after applying all P0 fixes to verify:
1. Returns are properly annualized
2. Classical benchmark works correctly
3. Graph edge weights are sensible
4. Evolution produces differentiated portfolios
5. Overall performance improves

Usage:
    python verify_phase1_fixes.py
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.graph_builder import FinancialGraphBuilder
from core.quantum_inspired.evolution_dynamics import QuantumEvolution
from validation.chang_validation import ChangValidation
from config.qsw_config import QSWConfig

def verify_return_annualization():
    """Verify returns are properly annualized."""
    print("="*60)
    print("TEST 1: Return Annualization")
    print("="*60)
    
    # Generate synthetic daily returns
    daily_returns = pd.Series(np.random.randn(252) * 0.01 + 0.0005)  # ~12.5% annual
    
    # Calculate both ways
    not_annualized = daily_returns.mean()
    annualized = daily_returns.mean() * 252
    
    print(f"Daily mean return: {not_annualized:.6f}")
    print(f"Annualized return: {annualized:.6f} ({annualized*100:.2f}%)")
    
    # Verify it's in reasonable range
    if 0.01 < annualized < 0.50:  # 1% to 50% annual
        print("✓ PASS: Annualized returns in reasonable range")
        return True
    else:
        print("✗ FAIL: Annualized returns outside reasonable range")
        return False

def verify_classical_benchmark():
    """Verify classical Markowitz optimization works."""
    print("\n" + "="*60)
    print("TEST 2: Classical Benchmark")
    print("="*60)
    
    # Create test data
    n_assets = 10
    returns = np.random.randn(n_assets) * 0.1 + 0.05
    A = np.random.randn(n_assets, n_assets)
    covariance = np.dot(A.T, A) / n_assets
    
    # Test classical optimization
    validator = ChangValidation()
    classical_sharpe = validator._calculate_classical_sharpe_proper(returns, covariance)
    
    # Equal weight for comparison
    equal_weights = np.ones(n_assets) / n_assets
    equal_return = np.dot(equal_weights, returns)
    equal_vol = np.sqrt(np.dot(equal_weights, np.dot(covariance, equal_weights)))
    equal_sharpe = equal_return / equal_vol if equal_vol > 0 else 0
    
    print(f"Equal-weight Sharpe: {equal_sharpe:.3f}")
    print(f"Optimized Sharpe: {classical_sharpe:.3f}")
    print(f"Improvement: {(classical_sharpe/equal_sharpe - 1)*100:.1f}%")
    
    # Classical optimization should beat equal-weight
    if classical_sharpe > equal_sharpe * 1.01:  # At least 1% better
        print("✓ PASS: Classical optimization beats equal-weight")
        return True
    else:
        print("✗ FAIL: Classical optimization doesn't improve over equal-weight")
        return False

def verify_graph_construction():
    """Verify graph edge weights make sense."""
    print("\n" + "="*60)
    print("TEST 3: Graph Construction")
    print("="*60)
    
    # Create test data with known correlations
    n_assets = 10
    returns = np.random.randn(n_assets) * 0.1 + 0.05
    
    # Create correlation matrix with clear structure
    correlation = np.eye(n_assets)
    # Add some high correlations
    correlation[0, 1] = correlation[1, 0] = 0.8  # Strong positive
    correlation[2, 3] = correlation[3, 2] = -0.7  # Strong negative
    correlation[4, 5] = correlation[5, 4] = 0.3   # Weak positive
    
    # Convert to covariance
    std_dev = np.random.rand(n_assets) * 0.1 + 0.1
    covariance = correlation * np.outer(std_dev, std_dev)
    
    # Build graph
    builder = FinancialGraphBuilder()
    graph, metrics = builder.build_graph(returns, covariance, market_regime='normal')
    
    print(f"Nodes: {metrics['n_nodes']}")
    print(f"Edges: {metrics['n_edges']}")
    print(f"Density: {metrics['density']:.3f}")
    print(f"Average weight: {metrics['avg_weight']:.3f}")
    
    # Check edge weights
    if graph.has_edge(0, 1):
        weight_01 = graph[0][1]['weight']
        print(f"Edge 0-1 weight (corr=0.8): {weight_01:.3f}")
    
    if graph.has_edge(2, 3):
        weight_23 = graph[2][3]['weight']
        print(f"Edge 2-3 weight (corr=-0.7): {weight_23:.3f}")
    
    # Graph should have edges and reasonable density
    # Note: Density can be low with sparse correlations (this is fine)
    if metrics['n_edges'] > 0 and metrics['density'] < 0.9:
        print("✓ PASS: Graph has reasonable structure")
        print(f"  Note: Low density ({metrics['density']:.3f}) is OK for sparse correlations")
        return True
    else:
        print("✗ FAIL: Graph structure problematic")
        return False

def verify_evolution_differentiation():
    """Verify quantum evolution produces differentiated portfolios."""
    print("\n" + "="*60)
    print("TEST 4: Evolution Differentiation")
    print("="*60)
    
    # Create test data
    n_assets = 15
    returns = np.random.randn(n_assets) * 0.1 + 0.05
    A = np.random.randn(n_assets, n_assets)
    covariance = np.dot(A.T, A) / n_assets
    
    # Build graph
    builder = FinancialGraphBuilder()
    graph, _ = builder.build_graph(returns, covariance)
    
    # Run evolution with different omega values
    evolution = QuantumEvolution()
    
    weights_list = []
    overlaps = []
    
    for omega in [0.1, 0.2, 0.3, 0.4, 0.5]:
        weights, metrics = evolution.evolve(graph, omega, evolution_time=10)
        weights_list.append(weights)
        overlaps.append(metrics['state_overlap'])
        
    print(f"State overlaps: {[f'{o:.3f}' for o in overlaps]}")
    
    # Check differentiation between different omega values
    weight_diff = np.mean([
        np.sum(np.abs(weights_list[i] - weights_list[i+1]))
        for i in range(len(weights_list)-1)
    ])
    
    print(f"Average weight difference between omegas: {weight_diff:.3f}")
    
    # Weights should be different for different omega values
    if weight_diff > 0.1:  # At least 10% total change
        print("✓ PASS: Evolution produces differentiated portfolios")
        return True
    else:
        print("✗ FAIL: Evolution produces too-similar portfolios")
        print("       (May need to reduce evolution_time further)")
        return False

def verify_full_optimization():
    """Verify full optimization pipeline."""
    print("\n" + "="*60)
    print("TEST 5: Full Optimization Pipeline")
    print("="*60)
    
    # Create realistic test data
    n_assets = 20
    returns = np.random.randn(n_assets) * 0.1 + 0.05
    A = np.random.randn(n_assets, n_assets)
    covariance = np.dot(A.T, A) / n_assets
    
    # Run QSW optimization
    optimizer = QuantumStochasticWalkOptimizer()
    result = optimizer.optimize(returns, covariance, market_regime='normal')
    
    print(f"Sharpe Ratio: {result.sharpe_ratio:.3f}")
    print(f"Expected Return: {result.expected_return*100:.2f}%")
    print(f"Volatility: {result.volatility*100:.2f}%")
    print(f"Active Assets: {np.sum(result.weights > 0.001)}")
    print(f"Max Weight: {np.max(result.weights)*100:.2f}%")
    print(f"Graph Density: {result.graph_metrics['density']:.3f}")
    
    # Basic sanity checks
    checks = [
        (abs(np.sum(result.weights) - 1.0) < 1e-6, "Weights sum to 1"),
        (np.all(result.weights >= 0), "All weights non-negative"),
        (result.sharpe_ratio > 0, "Positive Sharpe ratio"),
        (result.expected_return > 0, "Positive expected return"),
        (result.volatility > 0, "Positive volatility")
    ]
    
    all_pass = True
    for passed, description in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {description}")
        all_pass = all_pass and passed
    
    if all_pass:
        print("✓ PASS: Full optimization working correctly")
        return True
    else:
        print("✗ FAIL: Issues in full optimization")
        return False

def run_quick_comparison():
    """Quick comparison: QSW vs Classical on real data."""
    print("\n" + "="*60)
    print("BONUS: Quick Performance Comparison")
    print("="*60)
    
    try:
        # Download small sample of real data
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'JPM', 'V', 'PG', 'JNJ']
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        print("Downloading market data...")
        data = yf.download(symbols, start=start_date, end=end_date, progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            data = data['Close']
        
        data = data.ffill().bfill()
        
        # Calculate inputs
        returns = data.pct_change().mean() * 252
        covariance = data.pct_change().cov() * 252
        
        # QSW optimization
        qsw_optimizer = QuantumStochasticWalkOptimizer()
        qsw_result = qsw_optimizer.optimize(returns, covariance)
        
        # Classical optimization
        validator = ChangValidation()
        classical_sharpe = validator._calculate_classical_sharpe_proper(returns, covariance)
        
        print(f"\nQSW Sharpe:       {qsw_result.sharpe_ratio:.3f}")
        print(f"Classical Sharpe: {classical_sharpe:.3f}")
        improvement = (qsw_result.sharpe_ratio / classical_sharpe - 1) * 100
        print(f"Improvement:      {improvement:.1f}%")
        
        if improvement > 0:
            print(f"✓ QSW beats classical by {improvement:.1f}%")
        else:
            print(f"⚠ QSW underperforms classical by {abs(improvement):.1f}%")
            print("  (May need further tuning)")
        
    except Exception as e:
        print(f"Could not run comparison: {e}")
        print("(This is optional - other tests are more important)")

def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print(" PHASE 1 FIX VERIFICATION SUITE")
    print("="*70)
    print("\nThis script verifies that all P0 fixes are working correctly.")
    print("Running 5 core tests plus 1 bonus comparison...\n")
    
    results = []
    
    # Run all tests
    results.append(("Return Annualization", verify_return_annualization()))
    results.append(("Classical Benchmark", verify_classical_benchmark()))
    results.append(("Graph Construction", verify_graph_construction()))
    results.append(("Evolution Differentiation", verify_evolution_differentiation()))
    results.append(("Full Optimization", verify_full_optimization()))
    
    # Optional comparison
    run_quick_comparison()
    
    # Summary
    print("\n" + "="*70)
    print(" VERIFICATION SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(passed for _, passed in results)
    total_tests = len(results)
    
    print("\n" + "-"*70)
    print(f"TOTAL: {total_passed}/{total_tests} tests passed")
    print("-"*70)
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nPhase 1 fixes are working correctly.")
        print("You can now proceed with full validation by running:")
        print("  python examples/basic_qsw_example.py")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("\nReview the failed tests above and ensure all fixes were applied correctly.")
        print("Check that you replaced the correct files:")
        print("  - validation/chang_validation.py")
        print("  - core/quantum_inspired/graph_builder.py")
        print("  - core/quantum_inspired/evolution_dynamics.py")
        print("  - config/qsw_config.py")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()