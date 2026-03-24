# Frontend Guide

## Stack

- React (Create React App)
- Recharts for charts
- Axios via `frontend/src/services/api.js`
- react-toastify for notifications

## Key files

```
frontend/src/
├── App.js                                    Entry — ErrorBoundary, ToastContainer
├── CustomizableQuantumDashboard.js           Main dashboard (state, tabs, layout)
├── theme.js                                  Design tokens, DashboardThemeContext
├── lib/
│   └── simulationEngine.js                   Synthetic data + JS optimiser approx
├── services/
│   └── api.js                                Axios client — DO NOT change URLs
└── components/dashboard/
    ├── index.js                              Barrel export
    ├── Slider.js
    ├── MetricCard.js
    ├── TabButton.js
    ├── SectionTitle.js
    ├── DataSourceBadge.js
    ├── LoadingOverlay.js
    ├── ConfirmDialog.js
    ├── ObjectiveSelector.js
    ├── RegimeSelector.js
    ├── BacktestPanel.js
    ├── DrawdownChart.js
    ├── CorrelationHeatmap.js
    ├── EfficientFrontier.js
    ├── WhatIfAdjuster.js
    ├── BenchmarkComparison.js
    ├── TradeBlotter.js
    └── RegimeComparison.js
```

## Proxy

`frontend/package.json` contains:
```json
"proxy": "http://localhost:5000"
```
All `/api/*` calls in development go to the Flask server on port 5000.
Never hardcode `http://localhost:5000` in component code.

## simulationEngine.js — API

```js
generateMarketData(nAssets, nDays, regime, seed) → data

runOptimisation(data, { objective, K, KScreen, KSelect, wMin, wMax }) → {
  weights, sharpe_ratio, expected_return, volatility,
  n_active, objective, stage_info
}

runBenchmarks(data) → { equal_weight, min_variance, markowitz, hrp }

resetSeed(s)
```

## Control panel state

Remove QSW-specific state:
```js
// REMOVE these
const [omega, setOmega] = useState(0.3);
const [evolutionTime, setEvolutionTime] = useState(50);
const [evolutionMethod, setEvolutionMethod] = useState('continuous');
```

Add new state:
```js
const [objective, setObjective] = useState('hybrid');
const [cardinality, setCardinality] = useState(null);    // K for qubo_sa/hybrid
const [kScreen, setKScreen] = useState(null);            // K_screen for hybrid
const [kSelect, setKSelect] = useState(null);            // K_select for hybrid
const [weightMin, setWeightMin] = useState(0.005);
const [weightMax, setWeightMax] = useState(0.30);
const [lambdaRisk, setLambdaRisk] = useState(1.0);
const [gamma, setGamma] = useState(8.0);
const [seed, setSeed] = useState(42);
```

## Objective options

```js
const OBJECTIVE_OPTIONS = [
  { value: 'hybrid',        label: 'Hybrid Pipeline',    badge: 'NB05', fast: false },
  { value: 'markowitz',     label: 'Markowitz',          badge: '1952', fast: true  },
  { value: 'hrp',           label: 'HRP',                badge: '2016', fast: true  },
  { value: 'min_variance',  label: 'Min Variance',       badge: null,   fast: true  },
  { value: 'qubo_sa',       label: 'QUBO-SA',            badge: 'NB04', fast: false },
  { value: 'vqe',           label: 'VQE',                badge: 'NB04', fast: false },
  { value: 'equal_weight',  label: 'Equal Weight',       badge: null,   fast: true  },
];
```

Fetch live from `/api/config/objectives` on mount. Fall back to this list
on failure. Show a "slow" badge on `fast: false` methods to set expectations.

## K_screen / K_select inputs

Show only when `objective === 'hybrid'`:
```jsx
{objective === 'hybrid' && (
  <div className="hybrid-params">
    <label>Screening size (K_screen)</label>
    <input type="number" min={2} max={20} value={kScreen ?? ''} placeholder="auto"
      onChange={e => setKScreen(e.target.value ? +e.target.value : null)} />
    <label>Selection size (K_select)</label>
    <input type="number" min={2} max={10} value={kSelect ?? ''} placeholder="auto"
      onChange={e => setKSelect(e.target.value ? +e.target.value : null)} />
  </div>
)}
```

Show `cardinality` (K) only when `objective === 'qubo_sa'`.

## API payload (optimize)

```js
const payload = {
  tickers,
  start_date: startDate,
  end_date:   endDate,
  objective,
  ...(cardinality  ? { K: cardinality }     : {}),
  ...(kScreen      ? { K_screen: kScreen }  : {}),
  ...(kSelect      ? { K_select: kSelect }  : {}),
  weight_min:   weightMin,
  weight_max:   weightMax,
  lambda_risk:  lambdaRisk,
  gamma,
  seed,
  ...(objective === 'target_return' ? { targetReturn } : {}),
};
```

Do NOT include: `omega`, `evolutionTime`, `evolutionMethod`, `regime`, `strategyPreset`.

## stage_info display (Holdings tab)

```jsx
{result?.stage_info && (
  <div className="stage-info">
    <span>Stage 1: screened {result.stage_info.stage1_screened_count} assets by IC</span>
    <span>Stage 2: selected {result.stage_info.stage2_selected_names?.join(', ')}</span>
    <span>Stage 3 Sharpe: {result.stage_info.stage3_sharpe?.toFixed(3)}</span>
  </div>
)}
```

## Do not change

- `frontend/src/services/api.js` — endpoint URLs and interceptors
- `frontend/package.json` proxy setting
- Chart rendering logic in existing components
- `theme.js` design tokens (use them; don't duplicate)

## Build and verify

```bash
cd frontend
npm install
npx eslint src/CustomizableQuantumDashboard.js  # fix warnings first
npm run build                                    # must be 0 errors
npm start                                        # requires backend on :5000
```