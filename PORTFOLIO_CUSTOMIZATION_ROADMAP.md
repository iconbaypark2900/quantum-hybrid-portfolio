# Portfolio Optimization Customization Roadmap

> A structured plan for evolving the Quantum Hybrid Portfolio into a comprehensive portfolio optimization application.

## Current State Summary

| Component | Status | Notes |
|-----------|--------|-------|
| QSW Optimizer | ✅ Production | Max Sharpe focus, regime-adaptive |
| Enhanced QSW | ✅ Available | Multi-objective, sector-aware; not in main API |
| Market Data | ✅ Working | yfinance, sectors, metadata |
| Backtest | ⚠️ Partial | Only max_sharpe objective implemented |
| Objectives | ⚠️ Stub | min_variance, target_return, risk_parity use same optimizer |
| Constraints | ⚠️ Basic | min/max weight only, no sector limits |
| Strategy Presets | ❌ Missing | No growth/income/balanced presets |

## Customization Goals

### Phase 1: Core Optimization Capabilities ✅ (Implementing)
- [x] Implement **min_variance** (classical convex optimization)
- [x] Implement **target_return** (efficient frontier)
- [x] Implement **risk_parity** (equal risk contribution)
- [x] Add **strategy presets** (growth, income, balanced, aggressive)
- [x] Strategy presets map to config + objective combinations

### Phase 2: Advanced Constraints ✅
- [x] Sector limits (e.g., max 30% Technology)
- [x] Cardinality constraints (exact number of positions)
- [ ] Factor exposure limits (beta, size, value) – deferred (requires factor data)
- [x] Turnover budget per rebalance (via max_turnover)
- [x] Blacklist/whitelist assets

### Phase 3: Data & Analytics
- [ ] Multi-asset class support (equities, ETFs, bonds, commodities)
- [ ] Alternative data sources (beyond yfinance)
- [ ] Transaction cost models in backtest
- [ ] Slippage modeling
- [ ] Performance attribution (sector, factor, timing)

### Phase 4: Integration & UX
- [ ] Integrate Enhanced QSW as optional "advanced" mode
- [ ] Preset selector in dashboard
- [ ] Constraint builder UI
- [ ] Scenario analysis (stress tests, Monte Carlo)
- [ ] Export to CSV/PDF reports

## Implementation Details

### Strategy Presets

| Preset | Objective | Config Notes |
|--------|-----------|--------------|
| **Growth** | max_sharpe | Higher omega, lower evolution_time, higher max_weight |
| **Income** | min_variance | Lower omega, higher stability_blend |
| **Balanced** | max_sharpe | Default config |
| **Aggressive** | max_sharpe | Aggressive config (higher turnover) |
| **Defensive** | min_variance | Conservative config |

### Optimization Objectives

| Objective | Method | Description |
|-----------|--------|-------------|
| max_sharpe | QSW | Quantum-inspired max Sharpe ratio |
| min_variance | Convex (scipy) | Minimum variance portfolio |
| target_return | Convex | Minimize variance at target return |
| risk_parity | Iterative | Equal risk contribution per asset |

### Config Extensions (Planned)

```python
# Strategy preset
strategy_preset: str = 'balanced'  # growth, income, balanced, aggressive, defensive

# Advanced constraints
sector_limits: Dict[str, float] = None  # {'Technology': 0.30}
cardinality: int = None  # Exact number of positions
max_sector_weight: float = 0.40  # Max any single sector
min_sector_weight: float = 0.0   # Min sector weight
```

## File Changes

| File | Changes |
|------|---------|
| `config/qsw_config.py` | Add `get_config_for_preset()`, optional sector limits |
| `services/portfolio_optimizer.py` | **New** – unified optimizer with all objectives |
| `services/backtest.py` | Use `portfolio_optimizer.run_optimization()` |
| `api.py` | Accept `strategy_preset`, route to correct objective |

## Success Metrics

- All four objectives produce distinct, valid portfolios
- Presets yield visibly different allocations
- Backtest runs with any objective
- API accepts and respects strategy_preset and objective
