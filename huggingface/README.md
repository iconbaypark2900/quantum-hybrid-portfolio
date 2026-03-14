---
title: Quantum Portfolio Lab
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Quantum Portfolio Lab

Quantum-inspired portfolio optimization using Quantum Stochastic Walk (QSW) algorithms. Optimize portfolios with Max Sharpe, Min Variance, Risk Parity, HRP, and more.

## Features

- **Live API** — Real market data optimization
- **Simulation** — Synthetic market data for experimentation
- **Backtest** — Historical performance
- **Risk analysis** — VaR, stress tests, correlation
- **Scenario tester** — Batch backtest index/ETF universes

## Usage

1. Switch between **Simulation** and **Live API** in the header
2. Set tickers and dates (Live) or regime (Simulation)
3. Run optimization and explore tabs: Holdings, Performance, Risk, Analysis, Sensitivity, Scenarios

## Technical

- **Backend:** Flask API (port 7860)
- **Frontend:** React dashboard
- **Methods:** QSW, HRP (López de Prado), Ledoit–Wolf covariance

## Optional: QAOA on IBM Quantum

To run **QAOA on IBM Quantum** (real hardware or simulator):

1. Sign up at [quantum.ibm.com](https://quantum.ibm.com) and copy your API token
2. In this Space, go to **Settings → Variables and secrets**
3. Add a secret: `IBM_QUANTUM_TOKEN` = your token
4. Optionally add `IBM_QUANTUM_BACKEND` (e.g. `simulator_stabilizer` for fast demos, or `ibm_brisbane` for real hardware)
5. Select **QAOA on IBM Quantum** in the objective dropdown when optimizing

Without the token, the app falls back to classical QAOA. Real QPU jobs may take several minutes due to queue time.
