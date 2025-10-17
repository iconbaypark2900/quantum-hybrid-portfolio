"""
Validation against Chang et al. (2025) results - FIXED VERSION
Key fixes:
1. Returns properly annualized (×252)
2. Classical benchmark uses proper Markowitz optimization
3. Covariance also annualized
"""
import numpy as np
import pandas as pd
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from scipy.optimize import minimize

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer
from config.qsw_config import QSWConfig

class ChangValidation:
    """
    Validates QSW implementation against Chang et al. (2025) results:
    - 27% Sharpe improvement (best case)
    - 15% average improvement
    - 90% turnover reduction
    """
    
    def __init__(self):
        self.qsw_optimizer = QuantumStochasticWalkOptimizer()
        self.results = {}
        
    def run_full_validation(self, 
                           market_data: pd.DataFrame,
                           n_iterations: int = 100) -> Dict:
        """
        Run complete validation suite.
        
        Args:
            market_data: Historical price data
            n_iterations: Number of validation iterations
            
        Returns:
            Validation results dictionary
        """
        print("Starting Chang et al. validation suite...")
        
        # Test 1: Sharpe ratio improvement
        sharpe_results = self.validate_sharpe_improvement(market_data, n_iterations)
        
        # Test 2: Turnover reduction
        turnover_results = self.validate_turnover_reduction(market_data)
        
        # Test 3: Parameter sensitivity
        parameter_results = self.validate_parameter_ranges(market_data)
        
        # Test 4: Market regime adaptation
        regime_results = self.validate_regime_adaptation(market_data)
        
        # Compile results
        self.results = {
            'sharpe_improvement': sharpe_results,
            'turnover_reduction': turnover_results,
            'parameter_sensitivity': parameter_results,
            'regime_adaptation': regime_results
        }
        
        # Generate report
        self.generate_validation_report()
        
        return self.results
    
    def validate_sharpe_improvement(self,
                                   market_data: pd.DataFrame,
                                   n_iterations: int = 100) -> Dict:
        """Validate Sharpe ratio improvement claims."""
        print("\nValidating Sharpe ratio improvement...")
        
        improvements = []
        
        for i in tqdm(range(n_iterations)):
            # Random sampling of time periods
            start_idx = np.random.randint(0, len(market_data) - 252)
            data_slice = market_data.iloc[start_idx:start_idx + 252]
            
            # FIX 1: Properly annualize returns and covariance
            returns = data_slice.pct_change().mean() * 252  # Annualized
            covariance = data_slice.pct_change().cov() * 252  # Annualized
            
            # Skip if data quality issues
            if np.any(np.isnan(returns)) or np.any(np.isnan(covariance)):
                continue
                
            # QSW optimization
            qsw_result = self.qsw_optimizer.optimize(returns, covariance)
            
            # FIX 2: Classical mean-variance optimization (proper benchmark)
            classical_sharpe = self._calculate_classical_sharpe_proper(returns, covariance)
            
            # Calculate improvement
            if classical_sharpe > 0:
                improvement = (qsw_result.sharpe_ratio / classical_sharpe - 1) * 100
                improvements.append(improvement)
        
        results = {
            'mean_improvement': np.mean(improvements),
            'median_improvement': np.median(improvements),
            'best_improvement': np.max(improvements),
            'worst_improvement': np.min(improvements),
            'std_improvement': np.std(improvements),
            'success_rate': np.mean([i > 0 for i in improvements]),
            'raw_improvements': improvements
        }
        
        print(f"Average Sharpe improvement: {results['mean_improvement']:.1f}%")
        print(f"Best case improvement: {results['best_improvement']:.1f}%")
        print(f"Success rate: {results['success_rate']*100:.1f}%")
        
        # Validate against Chang et al. claims
        results['validates_15_avg'] = results['mean_improvement'] >= 13  # Allow small margin
        results['validates_27_best'] = results['best_improvement'] >= 25
        
        return results
    
    def validate_turnover_reduction(self, market_data: pd.DataFrame) -> Dict:
        """Validate turnover reduction claims."""
        print("\nValidating turnover reduction...")
        
        # Simulate monthly rebalancing for 1 year
        rebalance_dates = pd.date_range(
            start=market_data.index[-252],
            end=market_data.index[-1],
            freq='M'
        )
        
        qsw_turnovers = []
        classical_turnovers = []
        
        prev_qsw_weights = None
        prev_classical_weights = None
        
        for date in tqdm(rebalance_dates[1:]):  # Skip first month
            # Get data up to rebalance date
            historical_data = market_data[market_data.index <= date].iloc[-252:]
            
            # FIX: Properly annualize
            returns = historical_data.pct_change().mean() * 252
            covariance = historical_data.pct_change().cov() * 252
            
            # QSW optimization
            qsw_result = self.qsw_optimizer.optimize(
                returns, covariance,
                initial_weights=prev_qsw_weights
            )
            
            # Classical optimization
            classical_weights = self._classical_optimize_proper(returns, covariance)
            
            # Calculate turnovers
            if prev_qsw_weights is not None:
                qsw_turnover = np.sum(np.abs(qsw_result.weights - prev_qsw_weights)) / 2
                qsw_turnovers.append(qsw_turnover)
                
            if prev_classical_weights is not None:
                classical_turnover = np.sum(np.abs(classical_weights - prev_classical_weights)) / 2
                classical_turnovers.append(classical_turnover)
            
            prev_qsw_weights = qsw_result.weights
            prev_classical_weights = classical_weights
        
        results = {
            'qsw_avg_turnover': np.mean(qsw_turnovers),
            'classical_avg_turnover': np.mean(classical_turnovers),
            'turnover_reduction': 1 - np.mean(qsw_turnovers) / np.mean(classical_turnovers),
            'qsw_turnovers': qsw_turnovers,
            'classical_turnovers': classical_turnovers
        }
        
        print(f"QSW average turnover: {results['qsw_avg_turnover']*100:.1f}%")
        print(f"Classical average turnover: {results['classical_avg_turnover']*100:.1f}%")
        print(f"Turnover reduction: {results['turnover_reduction']*100:.1f}%")
        
        # Validate against Chang et al. claim of 90% reduction
        results['validates_90_reduction'] = results['turnover_reduction'] >= 0.85
        
        return results
    
    def validate_parameter_ranges(self, market_data: pd.DataFrame) -> Dict:
        """Validate optimal parameter ranges from Chang et al."""
        print("\nValidating parameter ranges...")
        
        # Test omega range [0.2, 0.4]
        omega_values = np.linspace(0.1, 0.5, 20)
        omega_sharpes = []
        
        # Use fixed dataset for fair comparison
        returns = market_data.iloc[-252:].pct_change().mean() * 252  # FIX: Annualized
        covariance = market_data.iloc[-252:].pct_change().cov() * 252  # FIX: Annualized
        
        for omega in tqdm(omega_values):
            config = QSWConfig(default_omega=omega)
            optimizer = QuantumStochasticWalkOptimizer(config)
            result = optimizer.optimize(returns, covariance)
            omega_sharpes.append(result.sharpe_ratio)
        
        # Find optimal omega
        optimal_omega_idx = np.argmax(omega_sharpes)
        optimal_omega = omega_values[optimal_omega_idx]
        
        results = {
            'optimal_omega': optimal_omega,
            'omega_in_range': 0.2 <= optimal_omega <= 0.4,
            'omega_values': omega_values.tolist(),
            'omega_sharpes': omega_sharpes
        }
        
        print(f"Optimal omega: {optimal_omega:.2f}")
        print(f"In Chang range [0.2, 0.4]: {results['omega_in_range']}")
        
        return results
    
    def validate_regime_adaptation(self, market_data: pd.DataFrame) -> Dict:
        """Validate regime-adaptive performance."""
        print("\nValidating regime adaptation...")
        
        regimes = ['bull', 'bear', 'volatile', 'normal']
        regime_results = {}
        
        for regime in regimes:
            # Simulate regime-specific data characteristics
            if regime == 'bull':
                # Rising market, lower volatility
                returns_mult = 1.2
                vol_mult = 0.8
            elif regime == 'bear':
                # Falling market, higher volatility
                returns_mult = 0.8
                vol_mult = 1.3
            elif regime == 'volatile':
                # High volatility
                returns_mult = 1.0
                vol_mult = 1.5
            else:  # normal
                returns_mult = 1.0
                vol_mult = 1.0
            
            # FIX: Properly annualize
            returns = market_data.iloc[-252:].pct_change().mean() * 252 * returns_mult
            covariance = market_data.iloc[-252:].pct_change().cov() * 252 * vol_mult
            
            result = self.qsw_optimizer.optimize(returns, covariance, market_regime=regime)
            
            regime_results[regime] = {
                'sharpe_ratio': result.sharpe_ratio,
                'volatility': result.volatility,
                'n_edges': result.graph_metrics['n_edges'],
                'graph_density': result.graph_metrics['density']
            }
        
        print("\nRegime-specific performance:")
        for regime, metrics in regime_results.items():
            print(f"{regime}: Sharpe={metrics['sharpe_ratio']:.3f}, "
                  f"Density={metrics['graph_density']:.3f}")
        
        return regime_results
    
    def _calculate_classical_sharpe_proper(self, returns: np.ndarray, covariance: np.ndarray) -> float:
        """
        FIX 2: Proper Markowitz mean-variance optimization.
        This is the correct baseline, not equal-weight.
        """
        n = len(returns)
        
        def neg_sharpe(weights):
            """Negative Sharpe ratio for minimization."""
            portfolio_return = np.dot(weights, returns)
            portfolio_variance = np.dot(weights, np.dot(covariance, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            if portfolio_volatility < 1e-10:
                return 1e10  # Invalid portfolio
            
            return -portfolio_return / portfolio_volatility
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # Bounds: all weights between 0 and 1
        bounds = tuple((0, 1) for _ in range(n))
        
        # Initial guess: equal weight
        x0 = np.ones(n) / n
        
        # Optimize
        result = minimize(
            neg_sharpe,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            return -result.fun  # Return positive Sharpe
        else:
            # Fallback to equal weight if optimization fails
            weights = np.ones(n) / n
            portfolio_return = np.dot(weights, returns)
            portfolio_variance = np.dot(weights, np.dot(covariance, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)
            return portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
    
    def _classical_optimize_proper(self, returns: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """
        FIX 2: Proper Markowitz optimization for turnover comparison.
        """
        n = len(returns)
        
        def neg_sharpe(weights):
            portfolio_return = np.dot(weights, returns)
            portfolio_variance = np.dot(weights, np.dot(covariance, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            if portfolio_volatility < 1e-10:
                return 1e10
            
            return -portfolio_return / portfolio_volatility
        
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = tuple((0, 1) for _ in range(n))
        x0 = np.ones(n) / n
        
        result = minimize(
            neg_sharpe,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            return result.x
        else:
            return np.ones(n) / n
    
    def generate_validation_report(self):
        """Generate validation report with visualizations."""
        if not self.results:
            print("No results to report")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Sharpe improvement distribution
        ax = axes[0, 0]
        improvements = self.results['sharpe_improvement']['raw_improvements']
        ax.hist(improvements, bins=30, edgecolor='black', alpha=0.7)
        ax.axvline(x=15, color='r', linestyle='--', label='Chang avg: 15%')
        ax.axvline(x=27, color='g', linestyle='--', label='Chang best: 27%')
        ax.set_xlabel('Sharpe Improvement (%)')
        ax.set_ylabel('Frequency')
        ax.set_title('Sharpe Ratio Improvement Distribution')
        ax.legend()
        
        # Turnover comparison
        ax = axes[0, 1]
        if 'turnover_reduction' in self.results:
            turnovers = self.results['turnover_reduction']
            x = range(len(turnovers['qsw_turnovers']))
            ax.plot(x, turnovers['qsw_turnovers'], label='QSW', linewidth=2)
            ax.plot(x, turnovers['classical_turnovers'], label='Classical', linewidth=2)
            ax.set_xlabel('Rebalance Period')
            ax.set_ylabel('Turnover')
            ax.set_title('Turnover Comparison')
            ax.legend()
        
        # Omega parameter sensitivity
        ax = axes[1, 0]
        if 'parameter_sensitivity' in self.results:
            params = self.results['parameter_sensitivity']
            ax.plot(params['omega_values'], params['omega_sharpes'], linewidth=2)
            ax.axvspan(0.2, 0.4, alpha=0.3, color='green', label='Chang range')
            ax.set_xlabel('Omega')
            ax.set_ylabel('Sharpe Ratio')
            ax.set_title('Parameter Sensitivity')
            ax.legend()
        
        # Regime performance
        ax = axes[1, 1]
        if 'regime_adaptation' in self.results:
            regimes = list(self.results['regime_adaptation'].keys())
            sharpes = [self.results['regime_adaptation'][r]['sharpe_ratio'] for r in regimes]
            ax.bar(regimes, sharpes)
            ax.set_xlabel('Market Regime')
            ax.set_ylabel('Sharpe Ratio')
            ax.set_title('Regime-Adaptive Performance')
        
        plt.tight_layout()
        plt.savefig('chang_validation_report.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Print summary
        print("\n" + "="*60)
        print("CHANG ET AL. (2025) VALIDATION SUMMARY")
        print("="*60)
        
        validations = []
        if 'sharpe_improvement' in self.results:
            validations.append(('15% avg Sharpe improvement', 
                              self.results['sharpe_improvement']['validates_15_avg']))
            validations.append(('27% best Sharpe improvement',
                              self.results['sharpe_improvement']['validates_27_best']))
        
        if 'turnover_reduction' in self.results:
            validations.append(('90% turnover reduction',
                              self.results['turnover_reduction']['validates_90_reduction']))
        
        if 'parameter_sensitivity' in self.results:
            validations.append(('Omega in [0.2, 0.4] range',
                              self.results['parameter_sensitivity']['omega_in_range']))
        
        for test, passed in validations:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{test}: {status}")
        
        print("="*60)