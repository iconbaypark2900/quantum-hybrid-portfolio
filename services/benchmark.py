"""
Performance Benchmarking Suite for Quantum-Inspired Portfolio Optimization.

This module provides comprehensive benchmarking tools for:
- Comparing quantum-inspired vs classical methods
- Measuring runtime performance
- Tracking solution quality metrics
- Generating benchmark reports

Benchmarks include:
- QSW vs classical optimization
- QAOA performance analysis
- VQE risk calculation accuracy
- Linear algebra routine comparison
"""
import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""
    name: str
    method: str
    runtime_seconds: float
    sharpe_ratio: float
    expected_return: float
    volatility: float
    n_active: int
    additional_metrics: Dict = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    timestamp: str
    n_assets: int
    n_runs: int
    results: List[BenchmarkResult]
    summary: Dict = field(default_factory=dict)


class PortfolioBenchmark:
    """
    Benchmarking suite for portfolio optimization methods.
    
    Provides standardized benchmarks for comparing:
    - Quantum-inspired algorithms (QSW, QAOA, VQE)
    - Classical optimization methods
    - Hybrid approaches
    """
    
    def __init__(self, n_runs: int = 5):
        """
        Initialize benchmark suite.
        
        Args:
            n_runs: Number of runs per benchmark for averaging
        """
        self.n_runs = n_runs
        self.results_history: List[BenchmarkReport] = []
        
    def generate_test_data(
        self,
        n_assets: int = 20,
        correlation_level: float = 0.3,
        seed: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic portfolio data for benchmarking.
        
        Args:
            n_assets: Number of assets
            correlation_level: Average correlation between assets
            seed: Random seed for reproducibility
            
        Returns:
            Tuple of (returns, covariance)
        """
        if seed is not None:
            np.random.seed(seed)
        
        # Generate returns (5-15% annualized)
        returns = np.random.uniform(0.05, 0.15, n_assets)
        
        # Generate covariance matrix with controlled correlation
        volatilities = np.random.uniform(0.10, 0.30, n_assets)
        
        # Build correlation matrix
        correlation = np.ones((n_assets, n_assets)) * correlation_level
        np.fill_diagonal(correlation, 1.0)
        
        # Ensure positive semi-definite
        eigenvalues = np.linalg.eigvalsh(correlation)
        if np.min(eigenvalues) < 0:
            correlation += np.eye(n_assets) * (-np.min(eigenvalues) + 0.01)
        
        # Build covariance
        covariance = np.outer(volatilities, volatilities) * correlation
        
        return returns, covariance
    
    def benchmark_qsw(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        n_runs: Optional[int] = None,
    ) -> BenchmarkResult:
        """
        Benchmark Quantum Stochastic Walk optimization.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            n_runs: Override default n_runs
            
        Returns:
            Benchmark result
        """
        from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
        from config.qsw_config import QSWConfig
        
        n_runs = n_runs or self.n_runs
        runtimes = []
        sharpe_ratios = []
        
        for _ in range(n_runs):
            start = time.perf_counter()
            
            config = QSWConfig()
            optimizer = QuantumStochasticWalkOptimizer(config)
            result = optimizer.optimize(returns, covariance)
            
            runtime = time.perf_counter() - start
            runtimes.append(runtime)
            sharpe_ratios.append(result.sharpe_ratio)
        
        return BenchmarkResult(
            name="QSW Benchmark",
            method="quantum_stochastic_walk",
            runtime_seconds=np.mean(runtimes),
            sharpe_ratio=np.mean(sharpe_ratios),
            expected_return=result.expected_return,
            volatility=result.volatility,
            n_active=result.n_active,
            additional_metrics={
                "runtime_std": np.std(runtimes),
                "sharpe_std": np.std(sharpe_ratios),
                "turnover": result.turnover,
            },
        )
    
    def benchmark_qaoa(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        n_runs: Optional[int] = None,
    ) -> BenchmarkResult:
        """
        Benchmark QAOA optimization.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            n_runs: Override default n_runs
            
        Returns:
            Benchmark result
        """
        from core.quantum_inspired.qaoa_optimizer import QAOAOptimizer, QAOAConfig
        
        n_runs = n_runs or self.n_runs
        runtimes = []
        sharpe_ratios = []
        
        config = QAOAConfig(p=2, backend='classical')
        optimizer = QAOAOptimizer(config)
        
        for _ in range(n_runs):
            start = time.perf_counter()
            
            result = optimizer.optimize(returns, covariance)
            
            runtime = time.perf_counter() - start
            runtimes.append(runtime)
            sharpe_ratios.append(result['sharpe_ratio'])
        
        return BenchmarkResult(
            name="QAOA Benchmark",
            method="qaoa",
            runtime_seconds=np.mean(runtimes),
            sharpe_ratio=np.mean(sharpe_ratios),
            expected_return=result['expected_return'],
            volatility=result['volatility'],
            n_active=result['n_active'],
            additional_metrics={
                "runtime_std": np.std(runtimes),
                "sharpe_std": np.std(sharpe_ratios),
                "qaoa_layers": config.p,
            },
        )
    
    def benchmark_braket(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        n_runs: Optional[int] = None,
    ) -> BenchmarkResult:
        """
        Benchmark Braket annealing optimization.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            n_runs: Override default n_runs
            
        Returns:
            Benchmark result
        """
        from core.quantum_inspired.braket_backend import BraketAnnealingOptimizer
        
        n_runs = n_runs or self.n_runs
        runtimes = []
        sharpe_ratios = []
        
        optimizer = BraketAnnealingOptimizer()
        
        for _ in range(n_runs):
            start = time.perf_counter()
            
            result = optimizer.optimize(returns, covariance)
            
            runtime = time.perf_counter() - start
            runtimes.append(runtime)
            sharpe_ratios.append(result['sharpe_ratio'])
        
        return BenchmarkResult(
            name="Braket Benchmark",
            method=result.get('method', 'unknown'),
            runtime_seconds=np.mean(runtimes),
            sharpe_ratio=np.mean(sharpe_ratios),
            expected_return=result['expected_return'],
            volatility=result['volatility'],
            n_active=result['n_active'],
            additional_metrics={
                "runtime_std": np.std(runtimes),
                "sharpe_std": np.std(sharpe_ratios),
            },
        )
    
    def benchmark_classical(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        n_runs: Optional[int] = None,
    ) -> List[BenchmarkResult]:
        """
        Benchmark classical optimization methods.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            n_runs: Override default n_runs
            
        Returns:
            List of benchmark results for different classical methods
        """
        from services.portfolio_optimizer import run_optimization
        from scipy.optimize import minimize
        
        n_runs = n_runs or self.n_runs
        results = []
        
        # Mean-Variance Optimization
        runtimes_mvo = []
        for _ in range(n_runs):
            start = time.perf_counter()
            result = run_optimization(returns, covariance, objective='max_sharpe')
            runtimes_mvo.append(time.perf_counter() - start)
        
        results.append(BenchmarkResult(
            name="Mean-Variance Optimization",
            method="mvo",
            runtime_seconds=np.mean(runtimes_mvo),
            sharpe_ratio=result.sharpe_ratio,
            expected_return=result.expected_return,
            volatility=result.volatility,
            n_active=result.n_active,
            additional_metrics={"runtime_std": np.std(runtimes_mvo)},
        ))
        
        # Minimum Variance
        runtimes_minvar = []
        for _ in range(n_runs):
            start = time.perf_counter()
            result = run_optimization(returns, covariance, objective='min_variance')
            runtimes_minvar.append(time.perf_counter() - start)
        
        results.append(BenchmarkResult(
            name="Minimum Variance",
            method="min_variance",
            runtime_seconds=np.mean(runtimes_minvar),
            sharpe_ratio=result.sharpe_ratio,
            expected_return=result.expected_return,
            volatility=result.volatility,
            n_active=result.n_active,
            additional_metrics={"runtime_std": np.std(runtimes_minvar)},
        ))
        
        # Risk Parity
        runtimes_rp = []
        for _ in range(n_runs):
            start = time.perf_counter()
            result = run_optimization(returns, covariance, objective='risk_parity')
            runtimes_rp.append(time.perf_counter() - start)
        
        results.append(BenchmarkResult(
            name="Risk Parity",
            method="risk_parity",
            runtime_seconds=np.mean(runtimes_rp),
            sharpe_ratio=result.sharpe_ratio,
            expected_return=result.expected_return,
            volatility=result.volatility,
            n_active=result.n_active,
            additional_metrics={"runtime_std": np.std(runtimes_rp)},
        ))
        
        # HRP
        runtimes_hrp = []
        for _ in range(n_runs):
            start = time.perf_counter()
            result = run_optimization(returns, covariance, objective='hrp')
            runtimes_hrp.append(time.perf_counter() - start)
        
        results.append(BenchmarkResult(
            name="Hierarchical Risk Parity",
            method="hrp",
            runtime_seconds=np.mean(runtimes_hrp),
            sharpe_ratio=result.sharpe_ratio,
            expected_return=result.expected_return,
            volatility=result.volatility,
            n_active=result.n_active,
            additional_metrics={"runtime_std": np.std(runtimes_hrp)},
        ))
        
        # Equal Weight (baseline)
        n = len(returns)
        ew_weights = np.ones(n) / n
        ew_return = np.dot(ew_weights, returns)
        ew_vol = np.sqrt(ew_weights @ covariance @ ew_weights)
        ew_sharpe = ew_return / ew_vol if ew_vol > 0 else 0
        
        results.append(BenchmarkResult(
            name="Equal Weight",
            method="equal_weight",
            runtime_seconds=0.0,
            sharpe_ratio=ew_sharpe,
            expected_return=ew_return,
            volatility=ew_vol,
            n_active=n,
            additional_metrics={"baseline": True},
        ))
        
        return results
    
    def benchmark_vqe_risk(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        weights: np.ndarray,
        n_runs: Optional[int] = None,
    ) -> BenchmarkResult:
        """
        Benchmark VQE risk calculations.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            weights: Portfolio weights
            n_runs: Override default n_runs
            
        Returns:
            Benchmark result
        """
        from core.quantum_inspired.vqe_risk import VQEOptimizer
        
        n_runs = n_runs or self.n_runs
        runtimes = []
        
        optimizer = VQEOptimizer()
        
        for _ in range(n_runs):
            start = time.perf_counter()
            
            result = optimizer.calculate_minimum_variance(covariance)
            
            runtime = time.perf_counter() - start
            runtimes.append(runtime)
        
        return BenchmarkResult(
            name="VQE Risk Benchmark",
            method=result.get('method', 'unknown'),
            runtime_seconds=np.mean(runtimes),
            sharpe_ratio=0.0,  # Not applicable for risk calculation
            expected_return=0.0,
            volatility=result.get('minimum_volatility', 0.0),
            n_active=0,
            additional_metrics={
                "runtime_std": np.std(runtimes),
                "minimum_variance": result.get('minimum_variance', 0),
            },
        )
    
    def run_full_benchmark(
        self,
        n_assets: int = 20,
        seed: Optional[int] = None,
    ) -> BenchmarkReport:
        """
        Run complete benchmark suite.
        
        Args:
            n_assets: Number of assets for test data
            seed: Random seed
            
        Returns:
            Complete benchmark report
        """
        logger.info(f"Running full benchmark with {n_assets} assets")
        
        # Generate test data
        returns, covariance = self.generate_test_data(n_assets, seed=seed)
        
        all_results: List[BenchmarkResult] = []
        
        # Run benchmarks
        try:
            all_results.append(self.benchmark_qsw(returns, covariance))
        except Exception as e:
            logger.warning(f"QSW benchmark failed: {e}")
        
        try:
            all_results.append(self.benchmark_qaoa(returns, covariance))
        except Exception as e:
            logger.warning(f"QAOA benchmark failed: {e}")
        
        try:
            all_results.append(self.benchmark_braket(returns, covariance))
        except Exception as e:
            logger.warning(f"Braket benchmark failed: {e}")
        
        try:
            classical_results = self.benchmark_classical(returns, covariance)
            all_results.extend(classical_results)
        except Exception as e:
            logger.warning(f"Classical benchmark failed: {e}")
        
        try:
            n = len(returns)
            weights = np.ones(n) / n
            all_results.append(self.benchmark_vqe_risk(returns, covariance, weights))
        except Exception as e:
            logger.warning(f"VQE risk benchmark failed: {e}")
        
        # Generate summary
        summary = self._generate_summary(all_results)
        
        report = BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            n_assets=n_assets,
            n_runs=self.n_runs,
            results=all_results,
            summary=summary,
        )
        
        self.results_history.append(report)
        
        return report
    
    def _generate_summary(
        self,
        results: List[BenchmarkResult],
    ) -> Dict:
        """Generate benchmark summary statistics."""
        if not results:
            return {"error": "No results"}
        
        # Find best Sharpe ratio
        best_sharpe = max(r.sharpe_ratio for r in results if r.sharpe_ratio > 0)
        best_method = next(r.method for r in results if r.sharpe_ratio == best_sharpe)
        
        # Find fastest method
        fastest = min(r.runtime_seconds for r in results if r.runtime_seconds > 0)
        fastest_method = next(
            r.method for r in results if r.runtime_seconds == fastest
        )
        
        # Calculate average metrics
        avg_sharpe = np.mean([r.sharpe_ratio for r in results if r.sharpe_ratio > 0])
        avg_runtime = np.mean([r.runtime_seconds for r in results if r.runtime_seconds > 0])
        
        return {
            "best_sharpe_ratio": best_sharpe,
            "best_method": best_method,
            "fastest_method": fastest_method,
            "fastest_runtime": fastest,
            "average_sharpe": avg_sharpe,
            "average_runtime": avg_runtime,
            "total_methods": len(results),
            "quantum_methods": sum(
                1 for r in results
                if 'quantum' in r.method or 'qsw' in r.method.lower()
                or 'qaoa' in r.method.lower()
            ),
            "classical_methods": sum(
                1 for r in results
                if 'quantum' not in r.method
                and 'qsw' not in r.method.lower()
                and 'qaoa' not in r.method.lower()
            ),
        }
    
    def print_report(self, report: BenchmarkReport):
        """Print formatted benchmark report."""
        print("\n" + "="*70)
        print("QUANTUM HYBRID PORTFOLIO - BENCHMARK REPORT")
        print("="*70)
        print(f"Timestamp:    {report.timestamp}")
        print(f"Assets:       {report.n_assets}")
        print(f"Runs:         {report.n_runs}")
        print("-"*70)
        
        print(f"\n{'Method':<35} {'Sharpe':>10} {'Time (s)':>12} {'Return':>10} {'Vol':>10}")
        print("-"*70)
        
        # Sort by Sharpe ratio
        sorted_results = sorted(
            report.results, key=lambda x: -x.sharpe_ratio if x.sharpe_ratio > 0 else 0
        )
        
        for result in sorted_results:
            sharpe_str = f"{result.sharpe_ratio:.3f}" if result.sharpe_ratio > 0 else "N/A"
            time_str = f"{result.runtime_seconds:.4f}" if result.runtime_seconds > 0 else "N/A"
            print(f"{result.name:<35} {sharpe_str:>10} {time_str:>12} "
                  f"{result.expected_return*100:>9.2f}% {result.volatility*100:>9.2f}%")
        
        print("\n" + "-"*70)
        print("SUMMARY")
        print("-"*70)
        summary = report.summary
        print(f"Best Sharpe Ratio:  {summary.get('best_sharpe_ratio', 'N/A'):.3f} "
              f"({summary.get('best_method', 'N/A')})")
        print(f"Fastest Method:     {summary.get('fastest_method', 'N/A')} "
              f"({summary.get('fastest_runtime', 0):.4f}s)")
        print(f"Average Sharpe:     {summary.get('average_sharpe', 0):.3f}")
        print(f"Average Runtime:    {summary.get('average_runtime', 0):.4f}s")
        print(f"Total Methods:      {summary.get('total_methods', 0)}")
        print("="*70 + "\n")
    
    def save_report(
        self,
        report: BenchmarkReport,
        filename: str,
    ):
        """Save benchmark report to JSON file."""
        data = {
            "timestamp": report.timestamp,
            "n_assets": report.n_assets,
            "n_runs": report.n_runs,
            "results": [
                {
                    "name": r.name,
                    "method": r.method,
                    "runtime_seconds": r.runtime_seconds,
                    "sharpe_ratio": r.sharpe_ratio,
                    "expected_return": r.expected_return,
                    "volatility": r.volatility,
                    "n_active": r.n_active,
                    "additional_metrics": r.additional_metrics,
                }
                for r in report.results
            ],
            "summary": report.summary,
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Benchmark report saved to {filename}")


def run_benchmark(
    n_assets: int = 20,
    n_runs: int = 5,
    seed: int = 42,
    save_to: Optional[str] = None,
) -> BenchmarkReport:
    """
    Run benchmark suite and optionally save results.
    
    Args:
        n_assets: Number of assets
        n_runs: Number of runs per benchmark
        seed: Random seed
        save_to: Optional filename to save results
        
    Returns:
        Benchmark report
    """
    benchmark = PortfolioBenchmark(n_runs=n_runs)
    report = benchmark.run_full_benchmark(n_assets=n_assets, seed=seed)
    benchmark.print_report(report)
    
    if save_to:
        benchmark.save_report(report, save_to)
    
    return report


if __name__ == "__main__":
    # Run benchmark when executed directly
    run_benchmark(n_assets=15, n_runs=3, seed=42)
