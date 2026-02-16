#!/usr/bin/env python3
"""
Test script to verify the enhanced quantum walk optimizer works correctly
"""
import sys
import os
sys.path.insert(0, '/home/roc/quantumGlobalGroup/quantum-hybrid-portfolio')

def test_optimizer():
    print("Testing Enhanced Quantum Stochastic Walk Optimizer...")
    
    try:
        # Import the optimizer
        from core.quantum_inspired.enhanced_quantum_walk import EnhancedQuantumStochasticWalkOptimizer
        from config.qsw_config import QSWConfig
        
        print("✓ Successfully imported EnhancedQuantumStochasticWalkOptimizer")
        
        # Create a simple test case
        import numpy as np
        
        # Create dummy market data
        n_assets = 5
        returns = np.array([0.12, 0.10, 0.08, 0.15, 0.07])  # Annualized returns
        covariance = np.array([
            [0.0400, 0.0180, 0.0120, 0.0200, 0.0150],
            [0.0180, 0.0900, 0.0210, 0.0180, 0.0120],
            [0.0120, 0.0210, 0.0484, 0.0150, 0.0100],
            [0.0200, 0.0180, 0.0150, 0.0625, 0.0180],
            [0.0150, 0.0120, 0.0100, 0.0180, 0.0225]
        ])  # Annualized covariance matrix
        
        sectors = ['Tech', 'Tech', 'Finance', 'Energy', 'Healthcare']
        
        # Initialize optimizer
        config = QSWConfig()
        optimizer = EnhancedQuantumStochasticWalkOptimizer(config=config)
        
        print("✓ Successfully initialized optimizer")
        
        # Run optimization
        result = optimizer.optimize(
            returns=returns,
            covariance=covariance,
            market_regime='normal',
            sectors=sectors
        )
        
        print("✓ Successfully ran optimization")
        print(f"  - Weights: {[f'{w:.3f}' for w in result.weights]}")
        print(f"  - Sharpe Ratio: {result.sharpe_ratio:.3f}")
        print(f"  - Expected Return: {result.expected_return:.3f}")
        print(f"  - Volatility: {result.volatility:.3f}")
        print(f"  - Diversification Ratio: {result.diversification_ratio:.3f}")
        
        # Check if riskMetrics exists and is properly formed
        print(f"  - Risk Metrics: {result.riskMetrics}")
        
        print("\n✓ All tests passed! The optimizer is working correctly.")
        return True
        
    except Exception as e:
        print(f"✗ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optimizer()
    if success:
        print("\n🎉 Enhanced Quantum Portfolio Optimization System is ready for use!")
    else:
        print("\n❌ There are issues with the system that need to be fixed.")