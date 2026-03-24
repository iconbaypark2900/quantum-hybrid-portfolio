# Industry-Standard Audit and Implementation Plan

## Audit Summary

The Quantum Portfolio Lab was evaluated against fintech industry standards (Bloomberg Terminal, Axioma, PortfolioEffect, Refinitiv Eikon class). The frontend dashboard is a single ~2,450-line React file (`EnhancedQuantumDashboard.js`) containing all theme definitions, simulation engine logic, ~20 UI components (primitives + panels), and the main dashboard layout. All styling is done via 400+ inline `style={{}}` objects with hardcoded hex values. State is managed exclusively through `useState`/`useMemo` at the top level and threaded through deep prop chains. The dashboard lacks loading skeletons, toast notifications, confirmation dialogs, and a dark/light theme toggle.

The backend API (`api.py`, ~1,400 lines) returns raw JSON payloads on success and inconsistent `{"error": str(e)}` on failure, with no standard response envelope, no `request_id` in responses, and no `duration_ms` metadata. While security (CORS, rate limiting, API key auth, security headers) and monitoring (Prometheus, structured logging, audit trail) have been added, the response contract is not self-describing or consistent.

A VP of Engineering at a hedge fund would reject: (1) the monolithic single-file dashboard, (2) the lack of user feedback during expensive operations, (3) inconsistent API response shapes, and (4) the absence of a dark/light theme toggle and professional chart formatting.

---

## Phase 1: Formalize Audit (this document)

- [x] Create `NEXT_STEPS_INDUSTRY_STANDARD.md` with audit summary and checklists

---

## Phase 2: Refactor Dashboard (split file, styling, state)

**Objective**: Break the 2,450-line monolith into a modular component tree with centralized theme and state.

- [x] Extract `frontend/src/theme.js` (colors, chartColors, benchmarkColors, DashboardThemeContext, light theme)
- [x] Extract `frontend/src/lib/simulationEngine.js` (seededRandom, resetSeed, DEFAULT_TICKERS/SECTORS, generateMarketData, runEnhancedQSWOptimization, helper functions)
- [x] Extract `Slider` to `frontend/src/components/dashboard/Slider.js`
- [x] Extract `MetricCard` to `frontend/src/components/dashboard/MetricCard.js`
- [x] Extract `DataSourceBadge` to `frontend/src/components/dashboard/DataSourceBadge.js`
- [x] Extract `CollapsibleSection` to `frontend/src/components/dashboard/CollapsibleSection.js`
- [x] Extract `TabButton` to `frontend/src/components/dashboard/TabButton.js`
- [x] Extract `SectionTitle` to `frontend/src/components/dashboard/SectionTitle.js`
- [x] Extract `RegimeSelector` to `frontend/src/components/dashboard/RegimeSelector.js`
- [x] Extract `EvolutionMethodSelector` to `frontend/src/components/dashboard/EvolutionMethodSelector.js`
- [x] Extract `ObjectiveSelector` to `frontend/src/components/dashboard/ObjectiveSelector.js`
- [x] Extract `CustomTooltip` to `frontend/src/components/dashboard/CustomTooltip.js`
- [x] Extract `TradeBlotter` to `frontend/src/components/dashboard/TradeBlotter.js`
- [x] Extract `BenchmarkComparison` to `frontend/src/components/dashboard/BenchmarkComparison.js`
- [x] Extract `BacktestPanel` to `frontend/src/components/dashboard/BacktestPanel.js`
- [x] Extract `DrawdownChart` to `frontend/src/components/dashboard/DrawdownChart.js`
- [x] Extract `CorrelationHeatmap` to `frontend/src/components/dashboard/CorrelationHeatmap.js`
- [x] Extract `EfficientFrontier` to `frontend/src/components/dashboard/EfficientFrontier.js`
- [x] Extract `WhatIfAdjuster` to `frontend/src/components/dashboard/WhatIfAdjuster.js`
- [x] Extract `RegimeComparison` to `frontend/src/components/dashboard/RegimeComparison.js`
- [x] Create `frontend/src/components/dashboard/index.js` barrel export
- [x] Slim `EnhancedQuantumDashboard.js` to <500 lines (imports, state, layout only)

---

## Phase 3: Professional UX

**Objective**: Add user feedback, loading states, confirmations, theme toggle, and chart polish.

- [x] Install `react-toastify` and add `<ToastContainer>` in `App.js`
- [x] Add toast notifications to API interceptor (`api.js`) for 401/429/5xx
- [x] Add success toasts after optimize/backtest in dashboard
- [x] Create `LoadingOverlay` component in `frontend/src/components/dashboard/LoadingOverlay.js`
- [x] Add loading overlays to optimize, backtest, and efficient frontier panels
- [x] Create `ConfirmDialog` component in `frontend/src/components/dashboard/ConfirmDialog.js`
- [x] Add confirmation dialog before backtest and reset actions
- [x] Add light theme to `theme.js` and implement dark/light toggle in header
- [x] Persist theme preference in `localStorage`
- [x] Polish chart formatting (axis labels, number formatting, tooltips, aria-labels)

---

## Phase 4: Standardize API Responses

**Objective**: Wrap all API responses in a consistent envelope with request_id and duration_ms.

- [x] Add `success_response()` and `error_response()` helpers to `api.py`
- [x] Add `before_request` hook to generate and store `g.request_id` and `g.start_time`
- [x] Replace all `jsonify(...)` success returns with `success_response(...)`
- [x] Replace all `jsonify({'error': ...})` returns with `error_response(...)`
- [x] Add response unwrap in `frontend/src/services/api.js` interceptor
- [x] Handle new error envelope shape in frontend error interceptor

---

## Phase 5: Performance

**Objective**: Memoize components and review caching.

- [x] Wrap panel components in `React.memo` where props are stable
- [x] Audit `useMemo` dependencies in main dashboard
- [x] Confirm market-data cache is used consistently in `api.py`

---

## Phase 6: Cleanups

**Objective**: Remove debug artifacts and fix warnings.

- [x] Remove stray `console.log` / `console.warn` in frontend
- [x] Remove unused imports in all modified files
- [x] Fix React key warnings if any
- [x] Run ESLint on touched files and fix critical issues
