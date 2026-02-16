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
