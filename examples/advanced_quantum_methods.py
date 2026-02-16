#!/usr/bin/env python3
"""
Example demonstrating advanced quantum-inspired portfolio optimization methods.
Shows the new quantum annealing and discrete-time quantum walk capabilities.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from core.quantum_inspired.quantum_annealing import QuantumAnnealingOptimizer, run_quantum_annealing_comparison
from config.qsw_config import QSWConfig
from core.quantum_inspired.evolution_dynamics import QuantumEvolution


def generate_test_data(n_assets=10):
    """Generate test portfolio data."""
    np.random.seed(42)
    
    # Generate returns with some correlation structure
    returns = np.random.randn(n_assets) * 0.1 + 0.05  # 5% base return + noise
    
    # Generate covariance matrix with realistic correlation structure
    A = np.random.randn(n_assets, n_assets) * 0.3
    # Add some correlation between assets
    for i in range(n_assets):
        for j in range(i+1, n_assets):
            # Add some correlation based on index proximity
            A[i, j] += 0.1 * np.exp(-abs(i-j)/5)
            A[j, i] += 0.1 * np.exp(-abs(i-j)/5)
    
    covariance = np.dot(A.T, A) / n_assets
    
    return returns, covariance


def compare_evolution_methods():
    """Compare different quantum evolution methods."""
    print("="*60)
    print("COMPARING QUANTUM EVOLUTION METHODS")
    print("="*60)
    
    returns, covariance = generate_test_data(n_assets=15)
    
    # Continuous evolution (original method)
    config_cont = QSWConfig(evolution_method='continuous', evolution_time=10)
    optimizer_cont = QuantumStochasticWalkOptimizer(config_cont)
    result_cont = optimizer_cont.optimize(returns, covariance)
    
    # Discrete-time evolution
    config_disc = QSWConfig(evolution_method='discrete', evolution_time=10)
    optimizer_disc = QuantumStochasticWalkOptimizer(config_disc)
    result_disc = optimizer_disc.optimize(returns, covariance)
    
    # Decoherent evolution
    config_decoh = QSWConfig(evolution_method='decoherent', evolution_time=10, decoherence_rate=0.15)
    optimizer_decoh = QuantumStochasticWalkOptimizer(config_decoh)
    result_decoh = optimizer_decoh.optimize(returns, covariance)
    
    print(f"Continuous Evolution:  Sharpe={result_cont.sharpe_ratio:.3f}, "
          f"Return={result_cont.expected_return*100:.2f}%, Vol={result_cont.volatility*100:.2f}%")
    print(f"Discrete Evolution:    Sharpe={result_disc.sharpe_ratio:.3f}, "
          f"Return={result_disc.expected_return*100:.2f}%, Vol={result_disc.volatility*100:.2f}%")
    print(f"Decoherent Evolution:  Sharpe={result_decoh.sharpe_ratio:.3f}, "
          f"Return={result_decoh.expected_return*100:.2f}%, Vol={result_decoh.volatility*100:.2f}%")
    
    # Show weight differences
    print(f"\nWeight differences (L1 norm):")
    cont_disc_diff = np.sum(np.abs(result_cont.weights - result_disc.weights))
    cont_decoh_diff = np.sum(np.abs(result_cont.weights - result_decoh.weights))
    disc_decoh_diff = np.sum(np.abs(result_disc.weights - result_decoh.weights))
    
    print(f"  Continuous vs Discrete:  {cont_disc_diff:.3f}")
    print(f"  Continuous vs Decoherent: {cont_decoh_diff:.3f}")
    print(f"  Discrete vs Decoherent:  {disc_decoh_diff:.3f}")


def demonstrate_quantum_annealing():
    """Demonstrate quantum annealing optimization."""
    print("\n" + "="*60)
    print("DEMONSTRATING QUANTUM ANNEALING")
    print("="*60)
    
    returns, covariance = generate_test_data(n_assets=12)
    
    # Run quantum annealing
    qa_optimizer = QuantumAnnealingOptimizer()
    qa_result = qa_optimizer.optimize(returns, covariance)
    
    # Run classical optimization for comparison
    comparison = run_quantum_annealing_comparison(returns, covariance)
    
    print(f"Quantum Annealing:  Sharpe={qa_result['sharpe_ratio']:.3f}, "
          f"Return={qa_result['expected_return']*100:.2f}%, Vol={qa_result['volatility']*100:.2f}%")
    print(f"Classical Opt:      Sharpe={comparison['classical']['sharpe_ratio']:.3f}, "
          f"Return={comparison['classical']['expected_return']*100:.2f}%, Vol={comparison['classical']['volatility']*100:.2f}%")
    
    print(f"Improvement:        {(qa_result['sharpe_ratio']/comparison['classical']['sharpe_ratio'] - 1)*100:.2f}%")


def demonstrate_large_portfolio():
    """Demonstrate performance on larger portfolios."""
    print("\n" + "="*60)
    print("DEMONSTRATING LARGE PORTFOLIO OPTIMIZATION")
    print("="*60)
    
    # Create a larger portfolio
    returns, covariance = generate_test_data(n_assets=50)
    
    # Use sparse matrix evolution for efficiency
    config_sparse = QSWConfig(evolution_method='continuous', evolution_time=8)
    optimizer_sparse = QuantumStochasticWalkOptimizer(config_sparse)
    result_sparse = optimizer_sparse.optimize(returns, covariance)
    
    print(f"Large Portfolio (50 assets):")
    print(f"  Sharpe Ratio: {result_sparse.sharpe_ratio:.3f}")
    print(f"  Expected Return: {result_sparse.expected_return*100:.2f}%")
    print(f"  Volatility: {result_sparse.volatility*100:.2f}%")
    print(f"  Active Assets: {result_sparse.n_active}")
    print(f"  Top 5 Holdings: {np.argsort(result_sparse.weights)[-5:][::-1]}")
    print(f"  Top 5 Weights: {np.sort(result_sparse.weights)[-5:][::-1]*100:.2f}%")


def show_new_features():
    """Show new features and capabilities."""
    print("\n" + "="*60)
    print("NEW FEATURES & CAPABILITIES")
    print("="*60)
    
    print("1. Multiple Evolution Methods:")
    print("   - Continuous (original)")
    print("   - Discrete-time quantum walks")
    print("   - Decoherent evolution with tunable noise")
    
    print("\n2. Quantum Annealing Optimizer:")
    print("   - Quantum fluctuations to escape local minima")
    print("   - Configurable temperature schedules")
    print("   - Better for combinatorial problems")
    
    print("\n3. Performance Enhancements:")
    print("   - Sparse matrix operations for large portfolios")
    print("   - Risk-aware Hamiltonian construction")
    print("   - Additional diversification metrics")
    
    print("\n4. Advanced Configuration:")
    print("   - Evolution method selection")
    print("   - Decoherence rate tuning")
    print("   - Quantum fluctuation strength adjustment")


def main():
    """Run all demonstrations."""
    print("🧪 ADVANCED QUANTUM-INPIRED PORTFOLIO OPTIMIZATION DEMO")
    print("This demo showcases the new quantum methods added to the system.\n")
    
    show_new_features()
    compare_evolution_methods()
    demonstrate_quantum_annealing()
    demonstrate_large_portfolio()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nThe quantum-inspired optimization system now includes:")
    print("• Multiple quantum evolution methods")
    print("• Quantum annealing optimization") 
    print("• Enhanced performance for large portfolios")
    print("• Advanced configuration options")
    print("\nTry adjusting the configuration parameters to see how they affect results!")


if __name__ == "__main__":
    main()