# 09 — Regime Detection & Adaptive Strategy Selection

**Priority:** Medium  
**Status:** Missing — no regime detection exists; objective is user-selected statically  
**Area:** Backend `services/`, `core/`; Frontend Dashboard

---

## Problem

The platform allows users to pick a single optimization objective (Markowitz, HRP, VQE, QAOA, hybrid, etc.) and run it once. It has no mechanism to:

- Detect which market regime (bull, bear, high-vol, low-vol, crisis) is currently active
- Automatically suggest or switch to an objective better suited to the current regime
- Backtest a regime-switching strategy to quantify the benefit

A quantum-classical hybrid platform that doesn't adapt to market conditions provides no structural advantage over a static optimizer. Regime awareness is a key differentiator for institutional adoption.

---

## Scope

**In scope:**
- Implement a threshold-based regime classifier from market data (no ML training infrastructure required)
- Add an HMM-based regime classifier as an optional upgrade (2-state Hidden Markov Model using `hmmlearn`)
- Map each regime to a recommended objective
- Expose current regime via `GET /api/market/regime`
- Display current regime on the Dashboard with recommendation
- Add regime-switching to walk-forward backtest (from `06-walkforward-backtest.md`)

**Out of scope:**
- Deep learning regime detection (LSTM, Transformer)
- Real-time streaming regime updates (tick-level)
- Options-market regime signals (VIX, skew)

---

## Affected Files

| File | Change |
|------|--------|
| `services/regime_detector.py` | New file — threshold and HMM classifiers |
| `api/app.py` | Add `GET /api/market/regime` endpoint |
| `web/src/app/(ledger)/dashboard/page.tsx` | Add regime indicator widget |
| `web/src/lib/api.ts` | Add `fetchRegime()` call |
| `services/backtest.py` | Integrate regime-switching into walk-forward |

---

## Regime Definitions

### Threshold Classifier (no training required)

```python
def classify_regime_threshold(returns: pd.Series, vol_window=21, ret_window=63) -> str:
    """
    Classify current market regime from recent return series.
    Returns: 'bull_low_vol' | 'bull_high_vol' | 'bear_low_vol' | 'bear_high_vol' | 'crisis'
    """
    recent_vol = returns.iloc[-vol_window:].std() * np.sqrt(252)
    recent_ret = returns.iloc[-ret_window:].mean() * 252

    if recent_vol > 0.35:
        return 'crisis'
    elif recent_ret > 0.10 and recent_vol <= 0.18:
        return 'bull_low_vol'
    elif recent_ret > 0.10 and recent_vol > 0.18:
        return 'bull_high_vol'
    elif recent_ret <= 0.10 and recent_vol <= 0.18:
        return 'bear_low_vol'
    else:
        return 'bear_high_vol'
```

### Regime-to-Objective Mapping

| Regime | Recommended Objective | Rationale |
|--------|----------------------|-----------|
| `bull_low_vol` | `vqe` or `hybrid` | Exploit return momentum, quantum edge |
| `bull_high_vol` | `markowitz` | Control volatility; classical MVO reliable |
| `bear_low_vol` | `hrp` | Equal risk contribution; diversification |
| `bear_high_vol` | `hrp` or `equal_weight` | Minimum complexity, defensive |
| `crisis` | `equal_weight` | Maximum diversification, no model risk |

---

## HMM Classifier (optional, when `hmmlearn` is installed)

```python
from hmmlearn import hmm

def fit_hmm_regime(returns: pd.Series, n_states=2) -> tuple[int, np.ndarray]:
    """
    Fit a 2-state Gaussian HMM to the return series.
    Returns current state index and full state sequence.
    """
    model = hmm.GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=100)
    X = returns.values.reshape(-1, 1)
    model.fit(X)
    states = model.predict(X)
    # Identify which state is "bull" by mean return
    state_means = [returns[states == i].mean() for i in range(n_states)]
    bull_state = int(np.argmax(state_means))
    current_state = int(states[-1])
    return current_state, states
```

---

## API

### `GET /api/market/regime`

Query params: `tickers` (comma-separated), optional `method=threshold|hmm`

Response:
```json
{
  "regime": "bull_low_vol",
  "recommended_objective": "hybrid",
  "confidence": 0.82,
  "metrics": {
    "realized_vol_annualized": 0.14,
    "recent_return_annualized": 0.18,
    "classification_method": "threshold"
  },
  "description": "Low volatility bull market — momentum strategies and hybrid quantum objectives tend to outperform in this regime."
}
```

---

## Implementation Plan

1. **Create `services/regime_detector.py`** with `classify_regime_threshold()` and the HMM path (gated by `try: import hmmlearn`).

2. **Add `GET /api/market/regime`** in `api/app.py`:
   - Fetch recent market returns for the provided tickers (or SPY as proxy if no tickers given)
   - Run classifier
   - Return regime + recommendation

3. **Add to Dashboard** — new `RegimeWidget` in `web/src/app/(ledger)/dashboard/page.tsx`:
   - On mount, call `fetchRegime()` with the session tickers
   - Display regime badge: color-coded (green = bull, yellow = bear, red = crisis)
   - Show recommended objective with a "Switch to this objective" button

4. **Integrate regime-switching into walk-forward backtest** (`services/backtest.py`):
   - At each rebalance point, classify the current regime from training data
   - Select the recommended objective for that regime
   - Run optimization with the selected objective
   - Record which regime/objective was used in the `periods` output

5. **Write tests**:
   - `test_classify_regime_threshold_bull` — positive return, low vol → `bull_low_vol`
   - `test_classify_regime_crisis` — very high vol → `crisis`
   - `test_regime_endpoint_returns_recommendation` — API returns `recommended_objective`
   - `test_walkforward_regime_switching` — periods output includes `regime` field

---

## Acceptance Criteria

- [ ] `GET /api/market/regime` returns a valid regime classification and recommended objective
- [ ] Dashboard shows a regime indicator widget that updates on page load
- [ ] "Switch to this objective" button in the regime widget updates the session objective
- [ ] Walk-forward backtest supports `regime_switching=true` parameter and records per-period regime
- [ ] All four new tests pass
- [ ] Regime detection adds < 500ms to the API response

---

## Parking Lot

- Multi-asset regime (credit spreads, yield curve slope as additional signals)
- LSTM/Transformer regime detector — needs training pipeline (`QUANTUM_LEDGER_MANIFEST.md` deferred item)
- Real-time regime alert: push notification when regime changes
- Regime-conditioned factor tilts (see `08-factor-models.md` parking lot)
