# Dashboard User Guide

The Quantum Hybrid Portfolio Dashboard is a React application for portfolio optimization, backtesting, risk analysis, and scenario testing.

## Data Modes

- **LIVE (API)** — Real market data from the backend. Select tickers, dates, and run optimization.
- **SIM (Simulation)** — Synthetic market data from regime parameters. Ideal for experimentation.

## Tabs

### Holdings

- **Portfolio Holdings** — Optimized weights and sector allocation
- **Sector Breakdown** — Pie chart by GICS sector
- **Trade Blotter** — Dollar amounts and share counts for execution
- **Benchmark Weight Comparison** — QSW vs Equal Weight, Min Variance, Risk Parity, HRP

### Performance

- **Backtest Panel** — Run historical backtest with tickers and dates
- **Drawdown Chart** — Drawdown from peak
- **Cumulative Performance** — Equity curve (backtest or simulated)
- **Strategy Comparison** — QSW vs benchmarks (bar chart and table)

### Risk

- **Correlation Heatmap** — Pairwise correlation between assets
- **Efficient Frontier** — Risk-return frontier with current portfolio
- **Value at Risk** — Daily VaR and CVaR at 95% confidence
- **Sector Exposure** — Radar chart (portfolio vs equal-weight)
- **Stress Test Scenarios** — Impact under 2008 GFC, COVID Crash, 2022 Rate Shock, Flash Crash

### Analysis

- **What-If Weight Adjuster** — Sliders to tweak weights; see impact on metrics
- **Regime Comparison** — Optimize under bull, bear, normal, volatile regimes

### Sensitivity

- **Omega Sensitivity** — Sharpe vs omega
- **Max Weight / Evolution Time Sensitivity** — How constraints affect Sharpe
- **Correlation Matrix** — Holdings correlation
- **Omega Impact Breakdown** — Return, vol, positions at each omega

**API mode:** "Run API Sensitivity Sweep" — Batch optimize across omega and max-weight.

### Scenarios

- **Index & ETF Scenario Tester** — Define scenarios, run batch backtests, compare
- **Load** — Apply a scenario to the main dashboard

## Left Panel Controls

- **Quantum Parameters:** Omega, Evolution Time
- **Market Regime:** Normal, Bull, Bear, Volatile
- **Evolution Method:** Continuous, Discrete, Decoherent, Adiabatic, Variational
- **Objective:** Max Sharpe, Min Variance, Risk Parity, HRP, Target Return
- **Constraints:** Max Weight, Max Turnover, Universe Size
- **Tickers & Dates:** Search/autocomplete, date range
- **Simulation:** Random seed, reset, portfolio status

## Metric Cards

Sharpe Ratio, Expected Return, Volatility, Active Positions, Daily VaR. Toggle Optimization vs Backtest when backtest is available.

## Informational Bubbles

Hover over info icons next to labels, sections, and cards for short explanations.

## Header Actions

- **Theme toggle** — Dark/light
- **Export** — Download JSON (parameters, holdings, risk, backtest)
- **DataSource badge** — SIM or LIVE

---

*Last updated: 2026-02*
