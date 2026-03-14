"""
Unified portfolio optimization service.
Supports multiple objectives (max_sharpe, min_variance, target_return, risk_parity, hrp)
and strategy presets (growth, income, balanced, aggressive, defensive).
Phase 2: sector limits, cardinality, blacklist/whitelist.
"""
import os
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from scipy.optimize import minimize, Bounds

from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer, QSWResult
from config.qsw_config import QSWConfig
from services.constraints import PortfolioConstraints, compute_sector_masks

try:
    from core.quantum_inspired.braket_backend import BraketAnnealingOptimizer
except ImportError:
    BraketAnnealingOptimizer = None

try:
    from core.quantum_inspired.qaoa_optimizer import QAOAOptimizer, QAOAConfig
    QAOA_AVAILABLE = True
except ImportError:
    QAOA_AVAILABLE = False
    QAOAOptimizer = None  # type: ignore
    QAOAConfig = None  # type: ignore


@dataclass
class OptimizationResult:
    """Unified result for any optimization objective."""
    weights: np.ndarray
    sharpe_ratio: float
    expected_return: float
    volatility: float
    turnover: float
    objective: str
    n_active: int
    graph_metrics: Optional[Dict] = None
    evolution_metrics: Optional[Dict] = None
    asset_names: Optional[List[str]] = None  # If set, weights align to these (after filtering)
    backend_type: Optional[str] = None  # e.g. "braket" or "classical_qubo" for braket_annealing


def run_optimization(
    returns: np.ndarray,
    covariance: np.ndarray,
    objective: str = 'max_sharpe',
    target_return: Optional[float] = None,
    market_regime: str = 'normal',
    strategy_preset: str = 'balanced',
    initial_weights: Optional[np.ndarray] = None,
    config: Optional[QSWConfig] = None,
    constraints: Optional[PortfolioConstraints] = None,
    asset_names: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
) -> OptimizationResult:
    """
    Run portfolio optimization with the specified objective and strategy.

    Args:
        returns: Expected returns for each asset.
        covariance: Covariance matrix.
        objective: One of 'max_sharpe', 'min_variance', 'target_return', 'risk_parity'.
        target_return: Required for target_return objective (e.g., 0.15 for 15%).
        market_regime: 'bull', 'bear', 'volatile', 'normal'.
        strategy_preset: 'growth', 'income', 'balanced', 'aggressive', 'defensive'.
        initial_weights: Starting weights for turnover control.
        config: Optional custom config (overrides preset if provided).
        constraints: Phase 2 constraints (sector limits, cardinality, blacklist/whitelist).
        asset_names: Ticker/name per asset (for blacklist/whitelist).
        sectors: Sector per asset (for sector limits).

    Returns:
        OptimizationResult with weights and metrics.
    """
    returns = np.asarray(returns)
    covariance = np.asarray(covariance)
    n = len(returns)
    constraints = constraints or PortfolioConstraints()

    # Apply blacklist/whitelist to filter universe
    kept_indices = None
    n_original = n
    if constraints.blacklist or constraints.whitelist:
        returns, covariance, sectors, initial_weights, kept_indices = _filter_universe(
            returns, covariance, constraints, asset_names, sectors, initial_weights
        )
        n = len(returns)
        n_original = len(asset_names) if asset_names else n
        if n < 2:
            return _equal_weight_result(returns, covariance, objective)

    sectors = sectors or [""] * n
    asset_names = asset_names or [str(i) for i in range(n)]

    # Resolve config from preset or use provided
    if config is None:
        config = get_config_for_preset(strategy_preset)

    min_weight = config.min_weight
    max_weight = config.max_weight

    if objective == 'max_sharpe':
        result = _run_qsw_optimization(
            returns, covariance, config, market_regime, initial_weights
        )
    elif objective == 'min_variance':
        result = _run_min_variance(
            returns, covariance, min_weight, max_weight,
            constraints, sectors
        )
    elif objective == 'target_return':
        if target_return is None:
            target_return = np.mean(returns)
        result = _run_target_return(
            returns, covariance, target_return, min_weight, max_weight,
            constraints, sectors
        )
    elif objective == 'risk_parity':
        result = _run_risk_parity(
            returns, covariance, min_weight, max_weight,
            constraints, sectors
        )
    elif objective in ('hrp', 'hierarchical_risk_parity'):
        result = _run_hrp(
            returns, covariance, min_weight, max_weight,
            constraints, sectors
        )
    elif objective == 'braket_annealing' and BraketAnnealingOptimizer is not None:
        result = _run_braket_annealing(returns, covariance, initial_weights)
    elif objective == 'qaoa_ibm' and QAOAOptimizer is not None:
        result = _run_qaoa_ibm(returns, covariance, initial_weights)
    else:
        result = _run_qsw_optimization(
            returns, covariance, config, market_regime, initial_weights
        )

    # Apply sector limits (post-processing for QSW)
    if objective == 'max_sharpe' and constraints.has_constraints():
        result = _apply_constraints_post(result, constraints, sectors, returns, covariance)

    # Apply cardinality (top-k heuristic)
    if constraints.cardinality is not None:
        result = _apply_cardinality(result, constraints.cardinality)
    elif constraints.max_cardinality is not None:
        result = _apply_cardinality(result, constraints.max_cardinality, exact=False)
    elif constraints.min_cardinality is not None:
        result = _ensure_min_cardinality(result, constraints.min_cardinality)

    # Expand weights to original universe if we filtered
    if kept_indices is not None and n_original > len(result.weights):
        full_weights = np.zeros(n_original)
        full_weights[kept_indices] = result.weights
        result = OptimizationResult(
            weights=full_weights,
            sharpe_ratio=result.sharpe_ratio,
            expected_return=result.expected_return,
            volatility=result.volatility,
            turnover=result.turnover,
            objective=result.objective,
            n_active=int(np.sum(full_weights > 0.005)),
            graph_metrics=result.graph_metrics,
            evolution_metrics=result.evolution_metrics,
            backend_type=result.backend_type,
        )
    return result


def _equal_weight_result(
    returns: np.ndarray, covariance: np.ndarray, objective: str
) -> OptimizationResult:
    """Fallback when universe too small."""
    n = len(returns)
    weights = np.ones(n) / n
    ret = float(np.dot(weights, returns))
    vol = float(np.sqrt(weights @ covariance @ weights)) if n > 0 else 0.0
    sharpe = ret / vol if vol > 0 else 0
    return OptimizationResult(
        weights=weights,
        sharpe_ratio=sharpe,
        expected_return=ret,
        volatility=vol,
        turnover=0.0,
        objective=objective,
        n_active=n,
    )


def _filter_universe(
    returns: np.ndarray,
    covariance: np.ndarray,
    constraints: PortfolioConstraints,
    asset_names: Optional[List[str]],
    sectors: Optional[List[str]],
    initial_weights: Optional[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray, Optional[List[str]], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Apply blacklist/whitelist to reduce universe.
    Returns (returns, covariance, sectors, initial_weights, kept_indices).
    kept_indices is None if no filtering occurred; otherwise indices into original arrays.
    """
    n = len(returns)
    names = asset_names or [str(i) for i in range(n)]
    names_upper = [str(nn).strip().upper() for nn in names]
    keep = np.ones(n, dtype=bool)

    blacklist = set(c for c in constraints.blacklist if c)
    whitelist = set(c for c in constraints.whitelist if c)

    for i in range(n):
        ni = names_upper[i] if i < len(names_upper) else ""
        if blacklist and ni in blacklist:
            keep[i] = False
        if whitelist and ni not in whitelist:
            keep[i] = False

    indices = np.where(keep)[0]
    if len(indices) < 2:
        return returns, covariance, list(sectors) if sectors else None, initial_weights, None

    r = returns[indices]
    c = covariance[np.ix_(indices, indices)]
    s = [sectors[i] for i in indices] if sectors else None
    w0 = initial_weights[indices] if initial_weights is not None else None
    return r, c, s, w0, indices


def _run_qsw_optimization(
    returns: np.ndarray,
    covariance: np.ndarray,
    config: QSWConfig,
    market_regime: str,
    initial_weights: Optional[np.ndarray],
) -> OptimizationResult:
    """Run QSW optimizer for max_sharpe."""
    optimizer = QuantumStochasticWalkOptimizer(config)
    result: QSWResult = optimizer.optimize(
        returns, covariance, market_regime=market_regime,
        initial_weights=initial_weights
    )
    return OptimizationResult(
        weights=result.weights,
        sharpe_ratio=result.sharpe_ratio,
        expected_return=result.expected_return,
        volatility=result.volatility,
        turnover=result.turnover,
        objective='max_sharpe',
        n_active=int(np.sum(result.weights > 0.005)),
        graph_metrics=result.graph_metrics,
        evolution_metrics=result.evolution_metrics,
    )


def _run_qaoa_ibm(
    returns: np.ndarray,
    covariance: np.ndarray,
    initial_weights: Optional[np.ndarray],
) -> OptimizationResult:
    """Run QAOA on IBM Quantum (or simulator) or classical fallback."""
    if QAOAOptimizer is None or QAOAConfig is None:
        raise ValueError(
            "QAOA on IBM requires qiskit and qiskit-ibm-runtime. "
            "Install with: pip install qiskit qiskit-algorithms qiskit-ibm-runtime"
        )
    config = QAOAConfig(
        backend="ibm",
        ibm_backend=os.environ.get("IBM_QUANTUM_BACKEND"),  # e.g. ibm_brisbane, simulator_stabilizer
        max_assets=min(8, len(returns)),  # Limit for hardware
    )
    optimizer = QAOAOptimizer(config)
    out = optimizer.optimize(
        returns, covariance, market_regime="normal", initial_weights=initial_weights
    )
    backend_type = out.get("ibm_backend_name") or out.get("backend", "qaoa_ibm")
    return OptimizationResult(
        weights=out["weights"],
        sharpe_ratio=out["sharpe_ratio"],
        expected_return=out["expected_return"],
        volatility=out["volatility"],
        turnover=out.get("turnover", 0.0),
        objective="qaoa_ibm",
        n_active=out["n_active"],
        backend_type=str(backend_type),
    )


def _run_braket_annealing(
    returns: np.ndarray,
    covariance: np.ndarray,
    initial_weights: Optional[np.ndarray],
) -> OptimizationResult:
    """Run AWS Braket annealing (QUBO) or classical QUBO fallback."""
    if BraketAnnealingOptimizer is None:
        raise ValueError(
            "Braket annealing requires amazon-braket-sdk. "
            "Install with: pip install amazon-braket-sdk"
        )
    optimizer = BraketAnnealingOptimizer()
    out = optimizer.optimize(
        returns, covariance, market_regime="normal", initial_weights=initial_weights
    )
    return OptimizationResult(
        weights=out["weights"],
        sharpe_ratio=out["sharpe_ratio"],
        expected_return=out["expected_return"],
        volatility=out["volatility"],
        turnover=out.get("turnover", 0.0),
        objective="braket_annealing",
        n_active=out["n_active"],
        backend_type=out.get("method"),
    )


def _run_min_variance(
    returns: np.ndarray,
    covariance: np.ndarray,
    min_weight: float,
    max_weight: float,
    constraints: PortfolioConstraints,
    sectors: List[str],
) -> OptimizationResult:
    """Minimum variance portfolio using convex optimization."""
    n = len(returns)
    cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}] + _build_scipy_constraints(
        n, returns, constraints, sectors, eq_only=False
    )
    x0 = np.ones(n) / n

    res = minimize(
        lambda w: w @ covariance @ w,
        x0,
        method='SLSQP',
        bounds=Bounds(np.repeat(min_weight, n), np.repeat(max_weight, n)),
        constraints=cons,
    )

    if not res.success:
        weights = np.ones(n) / n
    else:
        weights = _apply_weight_constraints(res.x, min_weight, max_weight)
    weights = _apply_sector_constraints_post(weights, constraints, sectors)

    ret = float(np.dot(weights, returns))
    vol = float(np.sqrt(weights @ covariance @ weights))
    sharpe = ret / vol if vol > 0 else 0
    return OptimizationResult(
        weights=weights,
        sharpe_ratio=sharpe,
        expected_return=ret,
        volatility=vol,
        turnover=0.0,
        objective='min_variance',
        n_active=int(np.sum(weights > 0.005)),
    )


def _run_target_return(
    returns: np.ndarray,
    covariance: np.ndarray,
    target_return: float,
    min_weight: float,
    max_weight: float,
    constraints: PortfolioConstraints,
    sectors: List[str],
) -> OptimizationResult:
    """Minimize variance subject to target return."""
    n = len(returns)
    cons = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
        {'type': 'eq', 'fun': lambda w: np.dot(w, returns) - target_return},
    ] + _build_scipy_constraints(n, returns, constraints, sectors, eq_only=False)
    x0 = np.ones(n) / n

    res = minimize(
        lambda w: w @ covariance @ w,
        x0,
        method='SLSQP',
        bounds=Bounds(np.repeat(min_weight, n), np.repeat(max_weight, n)),
        constraints=cons,
    )

    if not res.success:
        return _run_min_variance(returns, covariance, min_weight, max_weight, constraints, sectors)

    weights = _apply_weight_constraints(res.x, min_weight, max_weight)
    weights = _apply_sector_constraints_post(weights, constraints, sectors)
    ret = float(np.dot(weights, returns))
    vol = float(np.sqrt(weights @ covariance @ weights))
    sharpe = ret / vol if vol > 0 else 0
    return OptimizationResult(
        weights=weights,
        sharpe_ratio=sharpe,
        expected_return=ret,
        volatility=vol,
        turnover=0.0,
        objective='target_return',
        n_active=int(np.sum(weights > 0.005)),
    )


def _run_risk_parity(
    returns: np.ndarray,
    covariance: np.ndarray,
    min_weight: float,
    max_weight: float,
    constraints: PortfolioConstraints,
    sectors: List[str],
) -> OptimizationResult:
    """
    Risk parity: equal risk contribution per asset.
    """
    n = len(returns)

    def risk_parity_objective(w):
        port_vol = np.sqrt(w @ covariance @ w)
        if port_vol < 1e-12:
            return 1e10
        mcr = (covariance @ w) / port_vol
        rc = w * mcr
        target_rc = port_vol / n
        return np.sum((rc - target_rc) ** 2)

    cons = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}] + _build_scipy_constraints(
        n, returns, constraints, sectors, eq_only=False
    )
    x0 = np.ones(n) / n

    res = minimize(
        risk_parity_objective,
        x0,
        method='SLSQP',
        bounds=Bounds(np.repeat(min_weight, n), np.repeat(max_weight, n)),
        constraints=cons,
    )

    weights = np.ones(n) / n if not res.success else _apply_weight_constraints(res.x, min_weight, max_weight)
    weights = _apply_sector_constraints_post(weights, constraints, sectors)
    ret = float(np.dot(weights, returns))
    vol = float(np.sqrt(weights @ covariance @ weights))
    sharpe = ret / vol if vol > 0 else 0
    return OptimizationResult(
        weights=weights,
        sharpe_ratio=sharpe,
        expected_return=ret,
        volatility=vol,
        turnover=0.0,
        objective='risk_parity',
        n_active=int(np.sum(weights > 0.005)),
    )


def _run_hrp(
    returns: np.ndarray,
    covariance: np.ndarray,
    min_weight: float,
    max_weight: float,
    constraints: PortfolioConstraints,
    sectors: List[str],
) -> OptimizationResult:
    """
    Hierarchical Risk Parity (López de Prado, SSRN 2708678).

    Non-optimization allocation: clustering + recursive inverse-variance
    bisection.  Proven to deliver lower out-of-sample variance than CLA
    and to be more robust than mean-variance optimization.
    """
    from services.hrp import hrp_weights

    weights = hrp_weights(covariance)

    # Apply the same post-processing constraints as other objectives
    weights = _apply_weight_constraints(weights, min_weight, max_weight)
    weights = _apply_sector_constraints_post(weights, constraints, sectors)

    ret = float(np.dot(weights, returns))
    vol = float(np.sqrt(weights @ covariance @ weights))
    sharpe = ret / vol if vol > 0 else 0
    return OptimizationResult(
        weights=weights,
        sharpe_ratio=sharpe,
        expected_return=ret,
        volatility=vol,
        turnover=0.0,
        objective='hrp',
        n_active=int(np.sum(weights > 0.005)),
    )


def _build_scipy_constraints(
    n: int,
    returns: np.ndarray,
    constraints: PortfolioConstraints,
    sectors: List[str],
    eq_only: bool = False,
) -> list:
    """Build scipy constraint dicts for sector limits."""
    out = []
    if eq_only:
        return out
    masks = compute_sector_masks(sectors)
    for sector, indices in masks.items():
        lim = constraints.sector_limits.get(sector)
        if lim is None and constraints.max_sector_weight is not None:
            lim = constraints.max_sector_weight
        if lim is not None:
            arr = np.zeros(n)
            for i in indices:
                arr[i] = 1
            out.append({'type': 'ineq', 'fun': lambda w, a=arr, l=lim: l - np.dot(a, w)})
        mn = constraints.sector_min.get(sector)
        if mn is not None:
            arr = np.zeros(n)
            for i in indices:
                arr[i] = 1
            out.append({'type': 'ineq', 'fun': lambda w, a=arr, m=mn: np.dot(a, w) - m})
    return out


def _apply_sector_constraints_post(
    weights: np.ndarray,
    constraints: PortfolioConstraints,
    sectors: List[str],
) -> np.ndarray:
    """Post-process weights to enforce sector limits (iterative scaling)."""
    masks = compute_sector_masks(sectors)
    weights = weights.copy()
    for _ in range(10):  # Iterations
        changed = False
        for sector, indices in masks.items():
            s = sum(weights[i] for i in indices)
            lim = constraints.sector_limits.get(sector)
            if lim is None and constraints.max_sector_weight is not None:
                lim = constraints.max_sector_weight
            if lim is not None and s > lim + 1e-6:
                scale = lim / s
                for i in indices:
                    weights[i] *= scale
                changed = True
            mn = constraints.sector_min.get(sector)
            if mn is not None and s < mn - 1e-6 and s > 0:
                scale = mn / s
                for i in indices:
                    weights[i] *= scale
                changed = True
        if not changed:
            break
        weights = weights / np.sum(weights)
    return weights


def _apply_constraints_post(
    result: OptimizationResult,
    constraints: PortfolioConstraints,
    sectors: List[str],
    returns: np.ndarray,
    covariance: np.ndarray,
) -> OptimizationResult:
    """Apply sector constraints to QSW result and recompute metrics."""
    w = _apply_sector_constraints_post(result.weights, constraints, sectors)
    ret = float(np.dot(w, returns))
    vol = float(np.sqrt(w @ covariance @ w))
    sharpe = ret / vol if vol > 0 else 0
    return OptimizationResult(
        weights=w,
        sharpe_ratio=sharpe,
        expected_return=ret,
        volatility=vol,
        turnover=result.turnover,
        objective=result.objective,
        n_active=int(np.sum(w > 0.005)),
        graph_metrics=result.graph_metrics,
        evolution_metrics=result.evolution_metrics,
    )


def _apply_cardinality(
    result: OptimizationResult,
    k: int,
    exact: bool = True,
) -> OptimizationResult:
    """Top-k heuristic: keep only k largest weights, renormalize."""
    w = result.weights.copy()
    n = len(w)
    if k >= n:
        return result
    if k < 1:
        k = 1
    idx = np.argpartition(w, -k)[-k:]
    w_new = np.zeros(n)
    w_new[idx] = w[idx]
    w_new = w_new / np.sum(w_new)
    return OptimizationResult(
        weights=w_new,
        sharpe_ratio=result.sharpe_ratio,
        expected_return=result.expected_return,
        volatility=result.volatility,
        turnover=result.turnover,
        objective=result.objective,
        n_active=int(np.sum(w_new > 0.005)),
        graph_metrics=result.graph_metrics,
        evolution_metrics=result.evolution_metrics,
    )


def _ensure_min_cardinality(
    result: OptimizationResult,
    min_k: int,
) -> OptimizationResult:
    """Ensure at least min_k positions. Promote smallest non-zero to fill."""
    w = result.weights.copy()
    n_active = int(np.sum(w > 0.005))
    if n_active >= min_k:
        return result
    # Find zero-weight indices, promote first `need` to small weight
    zero_idx = np.where(w < 0.005)[0]
    need = min_k - n_active
    if len(zero_idx) < need:
        return result
    promote = zero_idx[:need]
    min_w = 0.005  # 0.5% minimum
    # Scale down existing weights to make room, then add promoted
    extra = need * min_w
    w[w > 0] *= (1 - extra) / np.sum(w[w > 0])
    for i in promote:
        w[i] = min_w
    w = w / np.sum(w)
    return OptimizationResult(
        weights=w,
        sharpe_ratio=result.sharpe_ratio,
        expected_return=result.expected_return,
        volatility=result.volatility,
        turnover=result.turnover,
        objective=result.objective,
        n_active=int(np.sum(w > 0.005)),
        graph_metrics=result.graph_metrics,
        evolution_metrics=result.evolution_metrics,
    )


def _apply_weight_constraints(
    weights: np.ndarray,
    min_weight: float,
    max_weight: float,
) -> np.ndarray:
    """Clip and renormalize weights."""
    weights = np.clip(weights, 0, max_weight)
    weights[weights < min_weight] = 0
    s = np.sum(weights)
    if s > 0:
        weights = weights / s
    else:
        n = len(weights)
        weights = np.ones(n) / n
    return weights


def get_config_for_preset(preset: str) -> QSWConfig:
    """
    Return QSWConfig tailored to a strategy preset.

    Presets:
        growth: Higher risk/return, more turnover.
        income: Lower risk, stability focused.
        balanced: Default middle ground.
        aggressive: Maximum responsiveness.
        defensive: Minimum variance, low turnover.
    """
    presets = {
        'growth': QSWConfig(
            default_omega=0.35,
            evolution_time=8,
            max_turnover=0.25,
            stability_blend_factor=0.75,
            max_weight=0.12,
        ),
        'income': QSWConfig(
            default_omega=0.25,
            evolution_time=15,
            max_turnover=0.12,
            stability_blend_factor=0.65,
            max_weight=0.08,
        ),
        'balanced': QSWConfig(),
        'aggressive': QSWConfig(
            default_omega=0.4,
            evolution_time=5,
            max_turnover=0.35,
            stability_blend_factor=0.85,
            max_weight=0.15,
        ),
        'defensive': QSWConfig(
            default_omega=0.22,
            evolution_time=18,
            max_turnover=0.08,
            stability_blend_factor=0.55,
            max_weight=0.07,
        ),
    }
    return presets.get(preset.lower(), QSWConfig())


def compute_efficient_frontier(
    returns: np.ndarray,
    covariance: np.ndarray,
    n_points: int = 15
) -> List[Dict]:
    """
    Compute the efficient frontier by solving for minimum variance portfolios
    at different target return levels.

    Args:
        returns: Expected returns for each asset.
        covariance: Covariance matrix.
        n_points: Number of points to compute on the frontier.

    Returns:
        List of dictionaries containing target_return, volatility, sharpe, and weights.
    """
    from scipy.optimize import minimize
    
    returns = np.asarray(returns)
    covariance = np.asarray(covariance)
    n_assets = len(returns)
    
    # Calculate minimum variance portfolio for min return
    def min_variance_objective(w):
        return np.dot(w, np.dot(covariance, w))
    
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
    ]
    
    bounds = [(0, 1) for _ in range(n_assets)]  # Long-only
    
    # Solve for minimum variance portfolio
    result_min_var = minimize(
        min_variance_objective,
        x0=np.ones(n_assets) / n_assets,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints
    )
    
    if not result_min_var.success:
        raise ValueError("Failed to compute minimum variance portfolio")
    
    min_return = np.dot(result_min_var.x, returns)
    
    # Calculate maximum return portfolio (highest individual return asset)
    max_return = np.max(returns)
    
    # Generate target returns between min and max
    target_returns = np.linspace(min_return, max_return, n_points)
    
    # Calculate efficient frontier points
    frontier_points = []
    
    for target_ret in target_returns:
        # Objective: minimize variance subject to target return
        def objective(w):
            return np.dot(w, np.dot(covariance, w))
        
        # Constraints: sum to 1 and achieve target return
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
            {'type': 'eq', 'fun': lambda w: np.dot(w, returns) - target_ret}  # Target return
        ]
        
        # Solve for this target return
        result = minimize(
            objective,
            x0=np.ones(n_assets) / n_assets,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            portfolio_variance = np.dot(result.x, np.dot(covariance, result.x))
            portfolio_vol = np.sqrt(portfolio_variance)
            
            # Calculate Sharpe ratio (assuming 0 risk-free rate)
            sharpe = target_ret / portfolio_vol if portfolio_vol != 0 else 0
            
            frontier_points.append({
                'target_return': float(target_ret),
                'volatility': float(portfolio_vol),
                'sharpe': float(sharpe),
                'weights': [float(w) for w in result.x]
            })
    
    return frontier_points
