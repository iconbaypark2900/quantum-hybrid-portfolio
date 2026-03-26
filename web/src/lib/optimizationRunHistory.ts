/**
 * Persists optimization snapshots in the browser so Reports can list past runs
 * (Executive Dashboard, Portfolio Lab, Quantum Engine) with stable IDs.
 * Server-side async lab runs live in SQLite via GET /api/runs — list those separately.
 */

import { mergeOptimizeResponse } from "@/lib/reportExport";

const STORAGE_KEY = "ql-optimization-runs-v1";
const MAX_RUNS = 100;

export type OptimizationRunSource =
  | "executive_dashboard"
  | "portfolio_lab"
  | "quantum_engine";

export interface StoredOptimizationRun {
  id: string;
  at: string;
  source: OptimizationRunSource;
  objective: string;
  tickers: string[];
  constraints: {
    weightMin: number;
    weightMax: number;
    kScreen?: string;
    kSelect?: string;
  };
  /** Raw API snapshot — may be `{ data, meta }`, stringified JSON, or async `{ result }` job output. */
  payload: unknown;
}

function safeParse(raw: string | null): StoredOptimizationRun[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x): x is StoredOptimizationRun =>
        x != null &&
        typeof x === "object" &&
        typeof (x as StoredOptimizationRun).id === "string" &&
        typeof (x as StoredOptimizationRun).at === "string"
    );
  } catch {
    return [];
  }
}

export function getOptimizationRuns(): StoredOptimizationRun[] {
  if (typeof window === "undefined") return [];
  return safeParse(localStorage.getItem(STORAGE_KEY));
}

export function getOptimizationRunById(
  id: string
): StoredOptimizationRun | null {
  return getOptimizationRuns().find((r) => r.id === id) ?? null;
}

export function appendOptimizationRun(
  data: Omit<StoredOptimizationRun, "id" | "source">,
  source: OptimizationRunSource
): StoredOptimizationRun {
  const id =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `run-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

  const entry: StoredOptimizationRun = { ...data, id, source };

  if (typeof window === "undefined") return entry;

  const prev = safeParse(localStorage.getItem(STORAGE_KEY));
  const next = [entry, ...prev.filter((r) => r.id !== id)].slice(0, MAX_RUNS);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return entry;
}

export function clearOptimizationRuns(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

/** Human-readable source for tables */
export function formatOptimizationSource(s: OptimizationRunSource): string {
  switch (s) {
    case "executive_dashboard":
      return "Executive Dashboard";
    case "portfolio_lab":
      return "Portfolio Lab";
    case "quantum_engine":
      return "Quantum Engine";
    default:
      return s;
  }
}

/** Sharpe / return / vol from merged optimize payload */
export function summarizeStoredPayload(payload: unknown): {
  sharpe: number | null;
  retPct: number | null;
  volPct: number | null;
  nActive: number | null;
} {
  const merged = mergeOptimizeResponse(payload) as Record<string, unknown>;
  const sharpe = merged.sharpe_ratio;
  const ret = merged.expected_return;
  const vol = merged.volatility;
  const n = merged.n_active;
  return {
    sharpe: typeof sharpe === "number" && Number.isFinite(sharpe) ? sharpe : null,
    retPct:
      typeof ret === "number" && Number.isFinite(ret) ? ret * 100 : null,
    volPct:
      typeof vol === "number" && Number.isFinite(vol) ? vol * 100 : null,
    nActive: typeof n === "number" && Number.isFinite(n) ? n : null,
  };
}
