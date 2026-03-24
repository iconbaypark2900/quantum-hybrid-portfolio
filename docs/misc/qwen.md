# CORE FEATURES IMPLEMENTATION SPECIFICATION

**Quantum Hybrid Portfolio Optimization System**

17 features across 5 modules | 20-week implementation timeline

P0 = Critical (fix first) | P1 = High (enables production) | P2 = Standard (full feature set)

February 2026

---

## Module 1: Optimizer Core Fixes

The optimizer currently underperforms classical Markowitz by approximately 34%. These P0 features directly address the root causes. Nothing else in the system matters until the optimizer produces competitive risk-adjusted returns.

### [P0] 1.1 Covariance Shrinkage Estimator

**What it does:** Replace raw sample covariance with Ledoit-Wolf shrinkage estimation. Sample covariance matrices are notoriously noisy for portfolio optimization (estimation error can be 70% of true values). Shrinkage pulls extreme eigenvalues toward a structured target, dramatically improving out-of-sample portfolio stability. Implement both Ledoit-Wolf (linear shrinkage toward scaled identity) and Oracle Approximating Shrinkage (OAS). Add optional Marchenko-Pastur denoising via Random Matrix Theory for large universes.

**File:** `core/estimators/covariance.py`  
**Dependencies:** numpy, scipy, sklearn.covariance

### [P0] 1.2 Hamiltonian Redesign

**What it does:** Redesign the quantum Hamiltonian to use Sharpe-ratio-weighted node potentials instead of raw returns. Current implementation uses V[i,i] = return_potential which ignores risk entirely. New design: V[i,i] = return_i / risk_i (asset-level Sharpe). Additionally, introduce off-diagonal coupling terms that encode diversification benefit: H_ij = -correlation_ij * sqrt(sharpe_i * sharpe_j). This gives the quantum walk a Hamiltonian that naturally flows probability toward high-Sharpe, low-correlation portfolios.

**File:** `core/quantum_inspired/evolution_dynamics.py`  
**Dependencies:** Modifies `_construct_hamiltonian` method

### [P0] 1.3 Regime Detection Engine

**What it does:** Replace manual market_regime parameter with automated detection. Implement a Hidden Markov Model with 3-4 states (bull, bear, high-vol, normal) trained on rolling 60-day windows of market returns, volatility, and correlation dispersion. Output regime probabilities rather than hard labels, allowing the optimizer to blend regime-specific parameters proportionally. Fall back to rolling volatility Z-score classifier if HMM is unstable.

**File:** `core/regime/detector.py`  
**Dependencies:** hmmlearn, numpy, pandas

### [P0] 1.4 Extended Benchmark Suite

**What it does:** Add four additional benchmarks beyond Markowitz mean-variance: (1) Equal-weight (1/N) portfolio, (2) Global Minimum Variance (min-vol, no return estimate needed), (3) Risk Parity (equal risk contribution per asset using Roncalli method), (4) Hierarchical Risk Parity (Lopez de Prado tree-based clustering). All benchmarks must use identical data, constraints, and evaluation windows for fair comparison.

**File:** `core/benchmarks/classical.py`  
**Dependencies:** scipy.optimize, numpy, scikit-learn

---

## Module 2: Backtesting Engine

Without proper out-of-sample backtesting, all performance claims are speculative. This module provides the rigorous statistical framework required to validate (or invalidate) the QSW approach with institutional credibility.

### [P0] 2.1 Walk-Forward Backtester

**What it does:** Implement rolling-window walk-forward analysis: (1) Train on N days of history (default 252), (2) Generate portfolio weights, (3) Evaluate on next M days (default 63 = 1 quarter), (4) Roll forward by M days and repeat. Track cumulative returns, drawdowns, and all standard metrics across the entire out-of-sample period. Support configurable train/test split, rebalance frequency, and warmup periods. Enforce strict temporal separation.

**File:** `core/backtesting/engine.py`  
**Dependencies:** pandas, numpy, core/quantum_inspired/

### [P0] 2.2 Transaction Cost Model

**What it does:** Model three layers of execution cost: (1) Fixed commission per trade (configurable, default 0.1 bps), (2) Half bid-ask spread (default 5 bps for liquid equities, configurable per asset), (3) Market impact using square-root model: impact = sigma * sqrt(trade_size / ADV) * eta. Deduct total cost from portfolio returns at each rebalance. Report gross vs. net Sharpe separately.

**File:** `core/backtesting/costs.py`  
**Dependencies:** numpy, pandas

### [P1] 2.3 Statistical Significance Testing

**What it does:** Implement bootstrap confidence intervals for all performance metrics. For each metric (Sharpe, Sortino, max DD, alpha): resample daily returns with replacement 10,000 times, compute the metric on each sample, report 95% CI. Additionally implement the Deflated Sharpe Ratio (Bailey and Lopez de Prado) which adjusts for the number of strategy variants tested.

**File:** `core/backtesting/statistics.py`  
**Dependencies:** numpy, scipy.stats

### [P1] 2.4 Performance Metrics Suite

**What it does:** Calculate comprehensive risk-adjusted metrics beyond Sharpe: (1) Sortino ratio (downside deviation only), (2) Calmar ratio (return / max drawdown), (3) Information ratio (active return / tracking error vs. benchmark), (4) Omega ratio, (5) Maximum drawdown and recovery time, (6) Win rate and profit factor, (7) Tail ratio. All metrics computed on rolling and cumulative basis.

**File:** `core/backtesting/metrics.py`  
**Dependencies:** numpy, pandas

---

## Module 3: Risk Management Engine

Risk management is the primary concern of institutional allocators. A portfolio system without VaR, stress testing, and factor decomposition will not pass due diligence at any serious fund or allocator.

### [P1] 3.1 VaR / CVaR Engine

**What it does:** Implement three VaR methodologies: (1) Historical simulation (non-parametric), (2) Parametric (variance-covariance method, assumes normal returns), (3) Monte Carlo simulation (10,000 scenarios). For each method, compute VaR and CVaR (Expected Shortfall) at 95% and 99% confidence levels. CVaR is the regulatory standard under Basel III/IV. Report both portfolio-level and position-level risk contribution.

**File:** `core/risk/var_engine.py`  
**Dependencies:** numpy, scipy.stats, pandas

### [P1] 3.2 Stress Testing Framework

**What it does:** Pre-built historical stress scenarios: (1) 2008 GFC (equity -50%, credit spreads +400bps), (2) 2020 COVID crash (equity -34% in 23 days), (3) 2022 rate shock (bonds -13%, growth stocks -33%), (4) Flash crash 2010 (intraday -9%). Support custom scenario builder where user specifies factor shocks and system computes portfolio impact using current factor exposures.

**File:** `core/risk/stress_testing.py`  
**Dependencies:** numpy, pandas, core/risk/var_engine.py

### [P1] 3.3 Factor Risk Decomposition

**What it does:** Decompose portfolio risk into systematic factor exposures using PCA-based factor model: (1) Extract principal components from return covariance (top 5-10 factors explaining >80% variance), (2) Project portfolio weights onto factor loadings, (3) Compute factor contribution to total risk, (4) Report factor exposure table and risk attribution chart. Support style factors (value, growth, momentum, size) if factor data available.

**File:** `core/risk/factor_model.py`  
**Dependencies:** numpy, scipy, scikit-learn, pandas

### [P2] 3.4 Advanced Constraint Engine

**What it does:** Extend basic box constraints to institutional requirements: (1) Sector/industry limits (e.g., max 20% tech, min 5% utilities), (2) Tracking error constraint (max active risk vs. benchmark), (3) Cardinality constraint (max N positions), (4) Turnover limits (max rebalance cost), (5) Long-short constraints. All constraints must be compatible with quantum walk optimization.

**File:** `core/constraints/engine.py`  
**Dependencies:** numpy, scipy.optimize

---

## Module 4: Data Pipeline

Reliable, point-in-time data is non-negotiable for backtesting validity. This module ensures data quality and eliminates survivorship bias.

### [P1] 4.1 Data Pipeline & Storage

**What it does:** Build robust data ingestion pipeline: (1) Daily price/volume data from yfinance or alternative source, (2) SQLite database for historical storage with schema versioning, (3) Data quality checks (missing values, outliers, corporate actions), (4) Automated daily update via schedule or cron, (5) Data validation reports. Support multiple data sources and failover.

**File:** `data/pipeline.py`, `data/storage.py`  
**Dependencies:** pandas, sqlite3, yfinance, schedule

### [P2] 4.2 Universe Management

**What it does:** Maintain point-in-time investment universe to eliminate survivorship bias: (1) Track S&P 500 constituent changes over time, (2) For any historical date return the universe as it existed, (3) Handle delistings, mergers, ticker changes. This is essential for backtesting validity. Without it, backtesting on today's winners inflates results by 1-3% annually.

**File:** `data/universe.py`  
**Dependencies:** pandas, beautifulsoup4

---

## Module 5: Reporting & Deployment

These features bridge the gap between a working system and one that stakeholders can evaluate, monitor, and trust.

### [P1] 5.1 Performance Attribution

**What it does:** Implement Brinson-Fachler attribution to decompose portfolio returns into: (1) Allocation effect, (2) Selection effect, (3) Interaction effect. Report monthly and cumulative attribution. Additionally implement returns-based style analysis (Sharpe 1992) to decompose returns against factor indices.

**File:** `core/reporting/attribution.py`  
**Dependencies:** pandas, numpy

### [P1] 5.2 Dashboard (Streamlit)

**What it does:** Interactive web dashboard with four main views: (1) Portfolio view: current holdings, weights, sector breakdown, (2) Performance view: cumulative returns vs. benchmarks, rolling Sharpe, drawdown chart, (3) Risk view: VaR/CVaR gauges, factor exposure chart, stress test results, (4) Backtest view: walk-forward equity curve, monthly return heatmap, statistics table. Deploy via Streamlit Cloud or Docker.

**File:** `dashboard/app.py`  
**Dependencies:** streamlit, plotly, pandas, all core modules

### [P2] 5.3 Automated Tear Sheets

**What it does:** Generate PDF/HTML one-page tear sheets: (1) Performance summary table, (2) Cumulative return chart vs. benchmark, (3) Monthly return heatmap, (4) Current top 10 holdings, (5) Sector allocation, (6) Risk metrics. Auto-generate on each backtest run or monthly schedule.

**File:** `core/reporting/tearsheet.py`  
**Dependencies:** matplotlib, reportlab or quantstats

---

## Proposed Directory Structure

The following structure organizes the 17 features into a clean, modular architecture:

```
quantum-hybrid-portfolio/
├── core/
│   ├── quantum_inspired/          # Existing QSW engine
│   │   ├── quantum_walk.py
│   │   ├── evolution_dynamics.py  # Modified: Hamiltonian redesign (1.2)
│   │   ├── graph_builder.py
│   │   └── stability_enhancer.py
│   ├── estimators/                # NEW
│   │   └── covariance.py          # Ledoit-Wolf, OAS, RMT (1.1)
│   ├── regime/                    # NEW
│   │   └── detector.py            # HMM regime detection (1.3)
│   ├── benchmarks/                # NEW
│   │   └── classical.py           # EW, MinVar, RP, HRP (1.4)
│   ├── backtesting/               # NEW
│   │   ├── engine.py              # Walk-forward (2.1)
│   │   ├── costs.py               # Transaction costs (2.2)
│   │   ├── statistics.py          # Bootstrap, DSR (2.3)
│   │   └── metrics.py             # Sortino, Calmar, etc. (2.4)
│   ├── risk/                      # NEW
│   │   ├── var_engine.py          # VaR/CVaR (3.1)
│   │   ├── stress_testing.py      # Scenarios (3.2)
│   │   └── factor_model.py        # PCA factors (3.3)
│   ├── constraints/               # NEW
│   │   └── engine.py              # Sector, TE, cardinality (3.4)
│   └── reporting/                 # NEW
│       ├── attribution.py         # Brinson-Fachler (5.1)
│       └── tearsheet.py           # PDF generation (5.3)
├── data/
│   ├── pipeline.py                # Data ingestion (4.1)
│   ├── storage.py                 # Database layer (4.1)
│   └── universe.py                # Point-in-time universe (4.2)
└── dashboard/
    └── app.py                     # Streamlit dashboard (5.2)
```

---

## Implementation Sequence

Features must be built in dependency order. Each sprint delivers testable value.

### Sprint 1 (Weeks 1-2): Foundation Fixes

**Goal:** Make the optimizer competitive with classical methods.

- Build covariance shrinkage estimator (1.1) and integrate into quantum_walk.py optimize() method
- Redesign Hamiltonian in evolution_dynamics.py to use Sharpe-weighted potentials (1.2)
- Run existing tests to verify no regressions; measure Sharpe improvement

**Exit criteria:** QSW Sharpe within 10% of classical Markowitz on 10-stock synthetic data

### Sprint 2 (Weeks 3-4): Benchmarks & Regime

**Goal:** Know exactly where QSW stands against all standard approaches.

- Implement benchmark suite (1.4): equal-weight, min-variance, risk-parity, HRP
- Build regime detector (1.3) with HMM and rolling volatility fallback
- Integrate regime detector into optimization pipeline (replace manual labels)

**Exit criteria:** Automated comparison table: QSW vs. 5 benchmarks across 4 detected regimes

### Sprint 3 (Weeks 5-8): Backtesting

**Goal:** Prove (or disprove) QSW advantage with out-of-sample evidence.

- Build walk-forward backtester (2.1) with configurable windows
- Add transaction cost model (2.2) with commission + spread + impact
- Implement metrics suite (2.4): Sortino, Calmar, information ratio, max drawdown
- Add bootstrap confidence intervals (2.3) and deflated Sharpe ratio

**Exit criteria:** 3-year walk-forward backtest with net-of-cost results and 95% CI on all metrics

### Sprint 4 (Weeks 9-12): Risk Engine

**Goal:** Institutional-grade risk management layer.

- Build VaR/CVaR engine (3.1) with historical, parametric, and Monte Carlo methods
- Implement stress testing framework (3.2) with 4 historical scenarios + custom builder
- Add PCA-based factor decomposition (3.3)
- Upgrade constraint engine (3.4): sector limits, tracking error, cardinality

**Exit criteria:** Risk report showing VaR, CVaR, factor exposures, and stress test results for any portfolio

### Sprint 5 (Weeks 13-16): Data & Reporting

**Goal:** Automated pipeline and investor-ready outputs.

- Build data pipeline (4.1) with SQLite storage, quality checks, and daily scheduling
- Add survivorship-bias-free universe management (4.2)
- Implement Brinson-Fachler performance attribution (5.1)
- Build Streamlit dashboard (5.2) with portfolio, performance, risk, and backtest views
- Add automated tear sheet generation (5.3)

**Exit criteria:** Live dashboard showing real portfolio with attribution, risk metrics, and downloadable tear sheet

---

## Summary: All 17 Features

| # | Pri | Feature | Module | Sprint |
|---|-----|---------|--------|--------|
| 1.1 | P0 | Covariance Shrinkage | Optimizer | Sprint 1 |
| 1.2 | P0 | Hamiltonian Redesign | Optimizer | Sprint 1 |
| 1.3 | P0 | Regime Detection | Optimizer | Sprint 2 |
| 1.4 | P0 | Benchmark Suite | Optimizer | Sprint 2 |
| 2.1 | P0 | Walk-Forward Backtester | Backtesting | Sprint 3 |
| 2.2 | P0 | Transaction Cost Model | Backtesting | Sprint 3 |
| 2.3 | P1 | Statistical Significance | Backtesting | Sprint 3 |
| 2.4 | P1 | Metrics Suite | Backtesting | Sprint 3 |
| 3.1 | P1 | VaR / CVaR Engine | Risk | Sprint 4 |
| 3.2 | P1 | Stress Testing | Risk | Sprint 4 |
| 3.3 | P1 | Factor Decomposition | Risk | Sprint 4 |
| 3.4 | P2 | Constraint Engine | Risk | Sprint 4 |
| 4.1 | P1 | Data Pipeline & Storage | Data | Sprint 5 |
| 4.2 | P2 | Universe Management | Data | Sprint 5 |
| 5.1 | P1 | Performance Attribution | Reporting | Sprint 5 |
| 5.2 | P1 | Streamlit Dashboard | Reporting | Sprint 5 |
| 5.3 | P2 | Automated Tear Sheets | Reporting | Sprint 5 |

---

**Quantum Global Group | Core Features Spec | February 2026**
