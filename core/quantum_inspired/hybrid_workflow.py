"""
Hybrid Quantum-Classical Workflows for Portfolio Optimization.

This module integrates all quantum-inspired components into cohesive
workflows that combine:
- Quantum and classical optimization
- Machine learning-enhanced optimization
- Multi-stage quantum-classical pipelines
- Adaptive algorithm selection

Workflows include:
- Hybrid QSW-Classical optimization
- ML-guided quantum algorithm selection
- Quantum-enhanced risk management
- End-to-end portfolio construction
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WorkflowConfig:
    """Configuration for hybrid workflows."""
    # Algorithm selection
    primary_method: str = 'qsw'  # 'qsw', 'qaoa', 'braket', 'hybrid'
    fallback_method: str = 'classical'  # 'classical', 'hrp', 'min_variance'
    
    # ML integration
    use_regime_detection: bool = True
    use_quantum_kernel: bool = False
    
    # Risk management
    use_vqe_risk: bool = True
    risk_confidence: float = 0.95
    
    # Performance
    max_runtime_seconds: float = 60.0
    parallel_evaluations: bool = False
    
    # Output
    verbose: bool = True
    return_diagnostics: bool = True


@dataclass
class WorkflowResult:
    """Result from a hybrid workflow execution."""
    # Portfolio results
    weights: np.ndarray
    expected_return: float
    volatility: float
    sharpe_ratio: float
    n_active: int
    
    # Method information
    primary_method: str
    fallback_used: bool = False
    backend: str = 'classical'
    
    # Risk metrics
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    minimum_variance: Optional[float] = None
    
    # Market regime
    market_regime: str = 'normal'
    regime_confidence: float = 0.0
    
    # Diagnostics
    runtime_seconds: float = 0.0
    iterations: int = 0
    diagnostics: Dict = field(default_factory=dict)


class HybridPortfolioWorkflow:
    """
    Hybrid quantum-classical portfolio optimization workflow.
    
    Combines multiple quantum-inspired algorithms with classical
    methods and machine learning for robust portfolio optimization.
    
    Workflow stages:
    1. Market regime detection (ML-enhanced)
    2. Algorithm selection based on regime
    3. Primary optimization (quantum or classical)
    4. Risk analysis (VQE-enhanced)
    5. Result validation and fallback if needed
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        """
        Initialize hybrid workflow.
        
        Args:
            config: Configuration object
        """
        self.config = config or WorkflowConfig()
        self._regime_detector = None
        self._risk_calculator = None
        
    def _detect_regime(
        self,
        returns: np.ndarray,
        prices: Optional[np.ndarray] = None,
    ) -> Tuple[str, float]:
        """Detect market regime using ML."""
        if not self.config.use_regime_detection:
            return 'normal', 0.0
        
        try:
            from core.quantum_inspired.quantum_ml import MarketRegimeDetector
            
            if self._regime_detector is None:
                self._regime_detector = MarketRegimeDetector()
            
            self._regime_detector.fit(returns, prices)
            regime = self._regime_detector.get_current_regime(returns, prices)
            
            # Simplified confidence estimate
            confidence = 0.7  # In production, compute from model
            
            return regime, confidence
            
        except Exception as e:
            logger.warning(f"Regime detection failed: {e}")
            return 'normal', 0.0
    
    def _select_algorithm(self, regime: str) -> str:
        """Select optimization algorithm based on regime."""
        # Regime-specific algorithm selection
        algorithm_map = {
            'bull': 'qsw',       # QSW excels in trending markets
            'bear': 'min_variance',  # Defensive in downturns
            'volatile': 'hrp',   # HRP handles uncertainty well
            'normal': 'qsw',     # Default to QSW
        }
        
        if self.config.primary_method != 'qsw':
            return self.config.primary_method
        
        return algorithm_map.get(regime, 'qsw')
    
    def _run_optimization(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        method: str,
        regime: str,
    ) -> Dict:
        """Run optimization using specified method."""
        try:
            if method == 'qsw':
                from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
                from config.qsw_config import QSWConfig
                
                config = QSWConfig()
                optimizer = QuantumStochasticWalkOptimizer(config)
                result = optimizer.optimize(returns, covariance, market_regime=regime)
                
                return {
                    'weights': result.weights,
                    'expected_return': result.expected_return,
                    'volatility': result.volatility,
                    'sharpe_ratio': result.sharpe_ratio,
                    'n_active': result.n_active,
                    'method': 'qsw',
                    'backend': 'classical',
                    'diagnostics': {
                        'graph_metrics': result.graph_metrics,
                        'evolution_metrics': result.evolution_metrics,
                        'turnover': result.turnover,
                    },
                }
                
            elif method == 'qaoa':
                from core.quantum_inspired.qaoa_optimizer import QAOAOptimizer, QAOAConfig
                
                config = QAOAConfig(p=2, backend='classical')
                optimizer = QAOAOptimizer(config)
                result = optimizer.optimize(returns, covariance, market_regime=regime)
                
                return {
                    'weights': result['weights'],
                    'expected_return': result['expected_return'],
                    'volatility': result['volatility'],
                    'sharpe_ratio': result['sharpe_ratio'],
                    'n_active': result['n_active'],
                    'method': 'qaoa',
                    'backend': result.get('backend', 'classical'),
                    'diagnostics': {
                        'qaoa_layers': config.p,
                    },
                }
                
            elif method == 'braket':
                from core.quantum_inspired.braket_backend import BraketAnnealingOptimizer
                
                optimizer = BraketAnnealingOptimizer()
                result = optimizer.optimize(returns, covariance)
                
                return {
                    'weights': result['weights'],
                    'expected_return': result['expected_return'],
                    'volatility': result['volatility'],
                    'sharpe_ratio': result['sharpe_ratio'],
                    'n_active': result['n_active'],
                    'method': 'braket_annealing',
                    'backend': result.get('method', 'classical_qubo'),
                    'diagnostics': {},
                }
                
            elif method == 'hrp':
                from services.portfolio_optimizer import run_optimization
                
                result = run_optimization(returns, covariance, objective='hrp')
                
                return {
                    'weights': result.weights,
                    'expected_return': result.expected_return,
                    'volatility': result.volatility,
                    'sharpe_ratio': result.sharpe_ratio,
                    'n_active': result.n_active,
                    'method': 'hrp',
                    'backend': 'classical',
                    'diagnostics': {},
                }
                
            elif method == 'min_variance':
                from services.portfolio_optimizer import run_optimization
                
                result = run_optimization(returns, covariance, objective='min_variance')
                
                return {
                    'weights': result.weights,
                    'expected_return': result.expected_return,
                    'volatility': result.volatility,
                    'sharpe_ratio': result.sharpe_ratio,
                    'n_active': result.n_active,
                    'method': 'min_variance',
                    'backend': 'classical',
                    'diagnostics': {},
                }
                
            else:
                # Default to max Sharpe
                from services.portfolio_optimizer import run_optimization
                
                result = run_optimization(returns, covariance, objective='max_sharpe')
                
                return {
                    'weights': result.weights,
                    'expected_return': result.expected_return,
                    'volatility': result.volatility,
                    'sharpe_ratio': result.sharpe_ratio,
                    'n_active': result.n_active,
                    'method': 'max_sharpe',
                    'backend': 'classical',
                    'diagnostics': {},
                }
                
        except Exception as e:
            logger.warning(f"Optimization failed ({method}): {e}")
            raise
    
    def _calculate_risk(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        weights: np.ndarray,
    ) -> Dict:
        """Calculate risk metrics using VQE."""
        if not self.config.use_vqe_risk:
            return {}
        
        try:
            from core.quantum_inspired.vqe_risk import VQEOptimizer
            
            optimizer = VQEOptimizer()
            
            # Minimum variance
            min_var = optimizer.calculate_minimum_variance(covariance)
            
            # VaR and CVaR
            var_result = optimizer.calculate_var(returns, covariance, weights)
            
            return {
                'minimum_variance': min_var.get('minimum_variance'),
                'minimum_volatility': min_var.get('minimum_volatility'),
                'var_95': var_result.get('var_95'),
                'cvar_95': var_result.get('cvar_95'),
                'risk_method': min_var.get('method'),
            }
            
        except Exception as e:
            logger.warning(f"Risk calculation failed: {e}")
            return {}
    
    def optimize(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        prices: Optional[np.ndarray] = None,
        target_return: Optional[float] = None,
        constraints: Optional[Dict] = None,
    ) -> WorkflowResult:
        """
        Run hybrid optimization workflow.
        
        Args:
            returns: Expected returns
            covariance: Covariance matrix
            prices: Historical prices (for regime detection)
            target_return: Target return (optional)
            constraints: Portfolio constraints (optional)
            
        Returns:
            WorkflowResult with optimization results
        """
        start_time = time.perf_counter()
        
        returns = np.asarray(returns)
        covariance = np.asarray(covariance)
        n_assets = len(returns)
        
        # Stage 1: Market regime detection
        regime, regime_confidence = self._detect_regime(returns, prices)
        
        if self.config.verbose:
            logger.info(f"Detected market regime: {regime} (confidence: {regime_confidence:.2f})")
        
        # Stage 2: Algorithm selection
        primary_method = self._select_algorithm(regime)
        
        if self.config.verbose:
            logger.info(f"Selected optimization method: {primary_method}")
        
        # Stage 3: Primary optimization
        fallback_used = False
        try:
            result = self._run_optimization(returns, covariance, primary_method, regime)
        except Exception as e:
            logger.warning(f"Primary method failed, using fallback: {e}")
            fallback_method = self.config.fallback_method
            result = self._run_optimization(returns, covariance, fallback_method, regime)
            fallback_used = True
        
        # Stage 4: Risk analysis
        risk_metrics = self._calculate_risk(
            returns, covariance, result['weights']
        )
        
        # Stage 5: Validation
        # Check weights sum to 1
        weights_sum = np.sum(result['weights'])
        if abs(weights_sum - 1.0) > 0.01:
            logger.warning(f"Weights sum to {weights_sum}, normalizing")
            result['weights'] = result['weights'] / weights_sum
        
        runtime = time.perf_counter() - start_time
        
        # Check runtime constraint
        if runtime > self.config.max_runtime_seconds:
            logger.warning(f"Runtime {runtime:.2f}s exceeded limit {self.config.max_runtime_seconds}s")
        
        # Build result
        workflow_result = WorkflowResult(
            weights=result['weights'],
            expected_return=result['expected_return'],
            volatility=result['volatility'],
            sharpe_ratio=result['sharpe_ratio'],
            n_active=result['n_active'],
            primary_method=result['method'],
            fallback_used=fallback_used,
            backend=result.get('backend', 'classical'),
            var_95=risk_metrics.get('var_95'),
            cvar_95=risk_metrics.get('cvar_95'),
            minimum_variance=risk_metrics.get('minimum_variance'),
            market_regime=regime,
            regime_confidence=regime_confidence,
            runtime_seconds=runtime,
            diagnostics=result.get('diagnostics', {}),
        )
        
        if self.config.verbose:
            logger.info(
                f"Optimization complete: Sharpe={result['sharpe_ratio']:.3f}, "
                f"Vol={result['volatility']*100:.2f}%, Time={runtime:.3f}s"
            )
        
        return workflow_result


class QuantumEnhancedBacktest:
    """
    Backtesting with quantum-enhanced optimization.
    
    Runs portfolio optimization at regular rebalancing intervals
    using hybrid quantum-classical methods.
    """
    
    def __init__(
        self,
        workflow_config: Optional[WorkflowConfig] = None,
        rebalance_frequency: str = 'monthly',
    ):
        """
        Initialize quantum-enhanced backtest.
        
        Args:
            workflow_config: Workflow configuration
            rebalance_frequency: 'weekly', 'monthly', 'quarterly'
        """
        self.workflow_config = workflow_config or WorkflowConfig()
        self.rebalance_frequency = rebalance_frequency
        self.workflow = HybridPortfolioWorkflow(self.workflow_config)
        
    def run(
        self,
        returns: np.ndarray,
        covariance: np.ndarray,
        start_date: str,
        end_date: str,
    ) -> Dict:
        """
        Run quantum-enhanced backtest.
        
        Args:
            returns: Returns matrix (time x assets)
            covariance: Covariance matrix
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            Backtest results
        """
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        n_periods, n_assets = returns.shape
        
        # Generate rebalance dates
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        rebalance_dates = []
        current = start
        while current < end:
            rebalance_dates.append(current)
            if self.rebalance_frequency == 'weekly':
                current += timedelta(weeks=1)
            elif self.rebalance_frequency == 'monthly':
                current += relativedelta(months=1)
            elif self.rebalance_frequency == 'quarterly':
                current += relativedelta(months=3)
            else:
                current += relativedelta(years=1)
        
        # Run optimization at each rebalance
        portfolio_values = [1.0]  # Start with $1
        weights_history = []
        dates_history = []
        
        for i, date in enumerate(rebalance_dates):
            # Get data up to this point
            period_end = min((i + 1) * 21, n_periods)  # Approximate trading days
            period_returns = returns[:period_end]
            
            # Estimate covariance from rolling window
            if period_end >= 60:
                rolling_returns = period_returns[-60:]
                cov_est = np.cov(rolling_returns.T)
            else:
                cov_est = covariance
            
            # Get expected returns
            if period_end >= 252:
                exp_returns = np.mean(period_returns[-252:], axis=0) * 252
            else:
                exp_returns = np.mean(period_returns, axis=0) * 252
            
            # Run optimization
            try:
                result = self.workflow.optimize(exp_returns, cov_est)
                weights = result.weights
            except Exception as e:
                logger.warning(f"Optimization failed at {date}: {e}")
                weights = np.ones(n_assets) / n_assets
            
            weights_history.append(weights.tolist())
            dates_history.append(date.isoformat())
            
            # Calculate portfolio return for next period
            next_period_start = period_end
            next_period_end = min(period_end + 21, n_periods)
            
            if next_period_start < n_periods:
                period_portfolio_return = np.sum(
                    weights * np.mean(returns[next_period_start:next_period_end], axis=0)
                )
                portfolio_values.append(portfolio_values[-1] * (1 + period_portfolio_return))
        
        # Calculate metrics
        portfolio_values = np.array(portfolio_values)
        total_return = portfolio_values[-1] - 1
        n_years = (end - start).days / 365.25
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # Volatility from period returns
        period_returns = np.diff(portfolio_values) / portfolio_values[:-1]
        volatility = np.std(period_returns) * np.sqrt(12) if len(period_returns) > 1 else 0
        sharpe = annual_return / volatility if volatility > 0 else 0
        
        return {
            'portfolio_values': portfolio_values.tolist(),
            'weights_history': weights_history,
            'dates': dates_history,
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe),
            'n_rebalances': len(rebalance_dates),
            'method': self.workflow_config.primary_method,
        }


def run_hybrid_optimization(
    returns: np.ndarray,
    covariance: np.ndarray,
    prices: Optional[np.ndarray] = None,
    config: Optional[WorkflowConfig] = None,
) -> Dict:
    """
    Run hybrid quantum-classical portfolio optimization.
    
    Convenience function for the full hybrid workflow.
    
    Args:
        returns: Expected returns
        covariance: Covariance matrix
        prices: Historical prices (optional)
        config: Workflow configuration
        
    Returns:
        Optimization results dictionary
    """
    workflow = HybridPortfolioWorkflow(config)
    result = workflow.optimize(returns, covariance, prices)
    
    return {
        'weights': result.weights.tolist(),
        'expected_return': result.expected_return,
        'volatility': result.volatility,
        'sharpe_ratio': result.sharpe_ratio,
        'n_active': result.n_active,
        'method': result.primary_method,
        'fallback_used': result.fallback_used,
        'backend': result.backend,
        'market_regime': result.market_regime,
        'var_95': result.var_95,
        'cvar_95': result.cvar_95,
        'runtime_seconds': result.runtime_seconds,
        'diagnostics': result.diagnostics if result.diagnostics else None,
    }


if __name__ == "__main__":
    # Example usage
    np.random.seed(42)
    
    # Generate test data
    n_assets = 15
    returns = np.random.uniform(0.05, 0.15, n_assets)
    cov = np.random.randn(n_assets, n_assets)
    cov = cov @ cov.T / n_assets
    
    # Run hybrid optimization
    config = WorkflowConfig(verbose=True, use_vqe_risk=True)
    result = run_hybrid_optimization(returns, cov, config=config)
    
    print("\nHybrid Optimization Results")
    print("="*50)
    print(f"Method: {result['method']}")
    print(f"Backend: {result['backend']}")
    print(f"Market Regime: {result['market_regime']}")
    print(f"\nPortfolio Metrics:")
    print(f"  Sharpe Ratio: {result['sharpe_ratio']:.3f}")
    print(f"  Expected Return: {result['expected_return']*100:.2f}%")
    print(f"  Volatility: {result['volatility']*100:.2f}%")
    print(f"  Active Assets: {result['n_active']}")
    print(f"\nRisk Metrics:")
    print(f"  VaR (95%): {result['var_95']*100 if result['var_95'] else 'N/A':.2f}%")
    print(f"  CVaR (95%): {result['cvar_95']*100 if result['cvar_95'] else 'N/A':.2f}%")
    print(f"\nRuntime: {result['runtime_seconds']:.3f}s")
