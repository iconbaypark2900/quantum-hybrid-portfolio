# Portfolio Lab vs backtest — what each answers

This guide clarifies how **dollar figures** and **history** work in Quantum Ledger so “how much money would I have made?” is interpreted correctly.

---

## Portfolio Lab (Next.js `/portfolio`)

### Data modes

- **Simulated:** Synthetic return paths driven by regime + seed — useful for methodology and stress-style narratives, not real markets.
- **Live tickers:** The app loads **historical** prices for your tickers and window, then estimates **expected returns** and **covariance** (same statistical object as production research flows). “Live” here means **fetched-at-request-time history** through the latest available daily bar, not a streaming intraday feed unless you add one later.

### Optimization

- You pick an **objective** (classical, hybrid, quantum, etc., per API/catalog).
- The backend returns **weights** (a portfolio in weight space, subject to min/max and method-specific rules).

### Notional

- **Notional** is **starting capital for display and simulation** in the lab UI.
- Dollar allocation per line is approximately **`weight × notional`** for each asset.
- The **forward simulation** (e.g. equity curves) marks those positions using the **return series loaded in the lab** — a **single coherent window** on the current estimated μ, Σ / price history.

**What Lab is not (by default):** A full **rolling rebalance** backtest that re-optimizes every week/month through time with a no-lookahead discipline. For that, use the backtest API (below).

---

## Rolling backtest (`POST /api/portfolio/backtest`)

### What it does

- Takes **tickers**, **start_date**, **end_date**, **rebalance_frequency**, and a **classical-style objective** (see API allow-list).
- Downloads **price history** over the window, steps through **rebalance dates**, and re-runs optimization on **lookback** windows per the implementation in `services/backtest.py`.

**What it answers:** “If I had followed this **rule-based, periodically rebalanced** strategy over this historical window, what would the **equity curve and summary metrics** look like?”

### Notional in backtest

- The API focuses on **weights and returns**; **dollar P&amp;L** is obtained by **scaling** the same way as in the lab if you multiply by a notional in your own reporting layer.

---

## Classical vs hybrid vs quantum in these two surfaces

- **Portfolio Lab / general optimize:** Can target **many objectives** (including hybrid and quantum), depending on the deployed API and IBM configuration.
- **Backtest endpoint** (today): Typically **classical** objective names only; extending to hybrid/quantum is a **separate effort** (cost, lookahead, runtime limits). See `docs/plans/INTEGRATED_MARKET_DATA_AND_FLOW_TASKS.md` Phase 7.

---

## Quick comparison

| Question | Use |
|----------|-----|
| “What weights should I hold **given this μ and Σ** (or this tickers window)?” | Lab optimize (or `POST` optimize) |
| “What if I **scaled** those weights to **$X** notional on this path?” | Lab **notional** + simulation |
| “What if I **rebalanced monthly** on **real history** with classical rules?” | **`/api/portfolio/backtest`** |

---

## Disclaimer

Simulations and backtests omit transaction costs, slippage, taxes, and corporate actions unless explicitly modeled. Outputs are for research and education, not investment advice.
