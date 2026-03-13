#!/usr/bin/env python3
"""
Quick verification test for braket_backend.py implementation.
Tests the BraketAnnealingOptimizer and API integration.
"""
import os
import sys
import numpy as np

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set test environment
os.environ.pop('API_KEY', None)
os.environ['ADMIN_API_KEY'] = 'test-admin-key'
os.environ['API_KEY_REQUIRED'] = 'false'

def test_braket_optimizer():
    """Test BraketAnnealingOptimizer directly."""
    print("="*60)
    print("TEST 1: BraketAnnealingOptimizer")
    print("="*60)
    
    from core.quantum_inspired.braket_backend import BraketAnnealingOptimizer
    
    # Generate test data
    np.random.seed(42)
    n = 10
    returns = np.random.uniform(0.05, 0.15, n)
    cov = np.random.randn(n, n)
    cov = cov @ cov.T / n  # Positive semi-definite
    
    # Run optimizer
    opt = BraketAnnealingOptimizer()
    result = opt.optimize(returns, cov)
    
    # Verify results
    assert 'weights' in result, "Missing 'weights' in result"
    assert 'sharpe_ratio' in result, "Missing 'sharpe_ratio' in result"
    assert 'expected_return' in result, "Missing 'expected_return' in result"
    assert 'volatility' in result, "Missing 'volatility' in result"
    assert 'n_active' in result, "Missing 'n_active' in result"
    assert 'method' in result, "Missing 'method' in result"
    
    # Verify method is classical_qubo (Braket SDK not installed)
    assert result['method'] in ('braket', 'classical_qubo'), f"Invalid method: {result['method']}"
    
    # Verify weights sum to 1
    weights_sum = np.sum(result['weights'])
    assert abs(weights_sum - 1.0) < 1e-6, f"Weights don't sum to 1: {weights_sum}"
    
    # Verify Sharpe is finite
    assert np.isfinite(result['sharpe_ratio']), "Sharpe ratio is not finite"
    
    print(f"✓ Method: {result['method']}")
    print(f"✓ Sharpe Ratio: {result['sharpe_ratio']:.3f}")
    print(f"✓ Expected Return: {result['expected_return']*100:.2f}%")
    print(f"✓ Volatility: {result['volatility']*100:.2f}%")
    print(f"✓ Active Assets: {result['n_active']}")
    print(f"✓ Weights Sum: {weights_sum:.6f}")
    print()
    return True


def test_qubo_formulation():
    """Test QUBO portfolio formulation."""
    print("="*60)
    print("TEST 2: QUBO Formulation")
    print("="*60)
    
    from core.quantum_inspired.braket_backend import build_qubo_portfolio, QUBOPortfolioConfig
    
    # Generate test data
    np.random.seed(42)
    n = 8
    returns = np.random.uniform(0.05, 0.15, n)
    cov = np.random.randn(n, n)
    cov = cov @ cov.T / n
    
    # Build QUBO
    config = QUBOPortfolioConfig()
    linear, quadratic = build_qubo_portfolio(returns, cov, config)
    
    # Verify structure
    assert len(linear) == n, f"Expected {n} linear terms, got {len(linear)}"
    assert len(quadratic) == n * (n - 1) // 2, f"Expected {n*(n-1)//2} quadratic terms"
    
    print(f"✓ Linear terms: {len(linear)}")
    print(f"✓ Quadratic terms: {len(quadratic)}")
    print(f"✓ Risk Aversion: {config.risk_aversion}")
    print()
    return True


def test_api_integration():
    """Test API integration with braket_annealing objective."""
    print("="*60)
    print("TEST 3: API Integration (braket_annealing)")
    print("="*60)
    
    from api import app
    
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False
    
    # Generate test data
    np.random.seed(42)
    n = 8
    returns = np.random.uniform(0.05, 0.15, n).tolist()
    cov = np.random.randn(n, n)
    cov = cov @ cov.T / n
    cov = cov.tolist()
    
    payload = {
        'returns': returns,
        'covariance': cov,
        'objective': 'braket_annealing',
    }
    
    with app.test_client() as client:
        resp = client.post('/api/portfolio/optimize', json=payload)
        
        # Check response
        assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.data}"
        
        data = resp.get_json()
        assert 'data' in data, "Missing 'data' in response"
        
        result = data['data']
        assert 'qsw_result' in result, "Missing 'qsw_result' in result"
        assert 'backend_type' in result, "Missing 'backend_type' in result"
        
        # Verify backend_type
        backend_type = result['backend_type']
        assert backend_type in ('braket', 'classical_qubo'), f"Invalid backend_type: {backend_type}"
        
        # Verify weights sum to 1
        weights = np.array(result['qsw_result']['weights'])
        weights_sum = np.sum(weights)
        assert abs(weights_sum - 1.0) < 1e-4, f"Weights don't sum to 1: {weights_sum}"
        
        print(f"✓ API Status: {resp.status_code}")
        print(f"✓ Backend Type: {backend_type}")
        print(f"✓ Sharpe Ratio: {result['qsw_result']['sharpe_ratio']:.3f}")
        print(f"✓ Weights Sum: {weights_sum:.6f}")
        print()
    return True


def test_quantum_annealing_comparison():
    """Test quantum annealing comparison."""
    print("="*60)
    print("TEST 4: Quantum Annealing Comparison")
    print("="*60)
    
    from core.quantum_inspired.quantum_annealing import run_quantum_annealing_comparison
    
    # Generate test data
    np.random.seed(42)
    n = 8
    returns = np.random.uniform(0.05, 0.15, n)
    cov = np.random.randn(n, n)
    cov = cov @ cov.T / n
    
    # Run comparison
    comparison = run_quantum_annealing_comparison(returns, cov)
    
    # Verify results
    assert 'quantum_annealing' in comparison, "Missing 'quantum_annealing' in comparison"
    assert 'classical' in comparison, "Missing 'classical' in comparison"
    
    qa = comparison['quantum_annealing']
    classical = comparison['classical']
    
    assert 'sharpe_ratio' in qa, "Missing 'sharpe_ratio' in quantum result"
    assert 'sharpe_ratio' in classical, "Missing 'sharpe_ratio' in classical result"
    
    print(f"✓ Quantum Annealing Sharpe: {qa['sharpe_ratio']:.3f}")
    print(f"✓ Classical Sharpe: {classical['sharpe_ratio']:.3f}")
    
    if classical['sharpe_ratio'] > 0:
        improvement = (qa['sharpe_ratio'] / classical['sharpe_ratio'] - 1) * 100
        print(f"✓ Quantum Advantage: {improvement:+.2f}%")
    print()
    return True


def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("BRAKET_BACKEND.PY VERIFICATION TESTS")
    print("="*60 + "\n")
    
    tests = [
        ("Braket Optimizer", test_braket_optimizer),
        ("QUBO Formulation", test_qubo_formulation),
        ("API Integration", test_api_integration),
        ("Quantum Annealing Comparison", test_quantum_annealing_comparison),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}\n")
            failed += 1
    
    # Summary
    print("="*60)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ All tests passed! braket_backend.py is working correctly.\n")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
