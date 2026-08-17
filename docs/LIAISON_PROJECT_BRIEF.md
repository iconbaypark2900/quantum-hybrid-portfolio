# LIAISON PROJECT BRIEF — quantum-hybrid-portfolio

> Machine: DGX Spark | Org: quantumGlobalGroup | Phase: mvp
> Path: `/home/iconbaypark2900/quantumGlobalGroup/quantum-hybrid-portfolio`
> Last updated: 2026-05-30

---

## Problem statement

Quantum-classical hybrid portfolio optimization lab — QAOA + CVX solvers, paper-trading only.

---

## Happy path

```bash
cd /home/iconbaypark2900/quantumGlobalGroup/quantum-hybrid-portfolio
cd ~/quantumGlobalGroup/quantum-hybrid-portfolio && python -m pytest tests/ -q
```

---

## Non-goals

- Live brokerage trading (paper-trading only)
- Full financial advisory product

---

## Validation profile

| Field | Value |
|-------|-------|
| Profile | `python` |
| Command | `cd ~/quantumGlobalGroup/quantum-hybrid-portfolio && python -m pytest tests/ -q` |

---

## Hub pattern and recommended agents

| Agent | Role |
|-------|------|
| hermes | Agent execution |
| QCA | Agent execution |
| codex | Agent execution |

Pattern: `python-cli`

---

## Open risks

| Risk | Mitigation |
|------|------------|
| financial | See next_actions in project_profile.yaml |
| quantum-sim-vs-hardware | See next_actions in project_profile.yaml |
| paper-trading-boundaries | See next_actions in project_profile.yaml |

---

## Next actions

- Label all portfolio outputs as research; no live trading on DGX
- Wire validation profile after test suite verified

---

## Related

- [project_profile.yaml](/home/iconbaypark2900/quantumGlobalGroup/quantum-hybrid-portfolio/.spark-flow/project_profile.yaml)
- [.spark-flow/README.md](/home/iconbaypark2900/quantumGlobalGroup/quantum-hybrid-portfolio/.spark-flow/README.md)

---

## L4 Domain Risk Review — Financial (2026-05-31)

**Review scope:** financial domain — paper trading gate, API key hygiene, backtest labeling

| Control | Status | Evidence |
|---------|--------|----------|
| No live API keys in `.spark-flow/` | PASS | No IBM Quantum / AWS Braket live credentials wired to trading |
| Backtest outputs labeled as research | PASS | Quantum portfolio outputs are simulation artifacts |
| risk_metric boundaries documented | PASS | Portfolio weights constrained 0–1; no leverage in quantum circuit |
| External service tests ignored in CI | PASS | pytest.ini ignores IBM/Braket/yfinance tests; 118 core tests pass |

**Risk classification:** MEDIUM — hybrid quantum-classical finance research; simulation only; no live execution path.

**Decision:** Accept current risk posture. Ensure `# SIMULATION ONLY` label is present in quantum circuit files (verified).
