/**
 * Payload builders for Quantum Engine async portfolio jobs (/api/jobs/*).
 * Aligns with Ledger session and API expectations in api.py.
 */

import type { LedgerSession } from "@/context/LedgerSessionContext";

/** Backtest API allows these objectives (see _run_backtest_payload). */
export function mapSessionObjectiveToBacktest(sessionObjective: string): string {
  const o = (sessionObjective || "").toLowerCase();
  if (o === "hrp") return "hrp";
  if (o === "min_variance") return "min_variance";
  if (o === "risk_parity") return "risk_parity";
  if (o === "braket_annealing" || o === "qubo_sa") return "braket_annealing";
  if (o === "markowitz" || o === "max_sharpe") return "max_sharpe";
  return "max_sharpe";
}

/** Default walk-forward window: end = today, start = 2 years earlier (YYYY-MM-DD). */
export function defaultBacktestDateRange(): {
  start_date: string;
  end_date: string;
} {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(start.getFullYear() - 2);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { start_date: fmt(start), end_date: fmt(end) };
}

export function buildOptimizeJobPayload(session: LedgerSession): Record<string, unknown> {
  const c = session.constraints;
  const p: Record<string, unknown> = {
    tickers: [...session.tickers],
    objective: session.objective,
    weight_min: c.weightMin,
    maxWeight: c.weightMax,
  };
  if (c.kScreen != null && String(c.kScreen).trim() !== "") {
    const n = Number(c.kScreen);
    if (!Number.isNaN(n)) p.K_screen = n;
  }
  if (c.kSelect != null && String(c.kSelect).trim() !== "") {
    const n = Number(c.kSelect);
    if (!Number.isNaN(n)) p.K_select = n;
  }
  return p;
}

/** Max assets the API may send to IBM hardware for VQE (`methods/vqe.py` MAX_IBM_QUBITS). */
export const MAX_IBM_VQE_ASSETS = 20;

/**
 * Same as optimize payload but forces `objective: "vqe"` so the API runs the VQE path
 * (IBM hardware when a token is configured; otherwise classical simulation).
 */
export function buildVqeIbmOptimizePayload(
  session: LedgerSession,
  opts?: { n_layers?: number; n_restarts?: number }
): Record<string, unknown> {
  const p = buildOptimizeJobPayload({ ...session, objective: "vqe" });
  if (opts?.n_layers != null && Number.isFinite(opts.n_layers)) {
    p.n_layers = Math.max(1, Math.floor(opts.n_layers));
  }
  if (opts?.n_restarts != null && Number.isFinite(opts.n_restarts)) {
    p.n_restarts = Math.max(1, Math.floor(opts.n_restarts));
  }
  return p;
}

export function formatVqeIbmOptimizeDetailLine(session: LedgerSession): string {
  const n = session.tickers.length;
  return `VQE · ${n} ticker${n === 1 ? "" : "s"} · weights ${session.constraints.weightMin.toFixed(3)}–${session.constraints.weightMax.toFixed(2)} (IBM path if connected)`;
}

export function buildBacktestJobPayload(session: LedgerSession): Record<string, unknown> {
  const range = defaultBacktestDateRange();
  return {
    tickers: [...session.tickers],
    objective: mapSessionObjectiveToBacktest(session.objective),
    start_date: range.start_date,
    end_date: range.end_date,
    rebalance_frequency: "monthly",
  };
}

export function formatOptimizeDetailLine(session: LedgerSession): string {
  const o = session.objective.replace(/_/g, " ");
  return `Optimize · ${o} · ${session.tickers.length} tickers`;
}

export function formatBacktestDetailLine(payload: Record<string, unknown>): string {
  const start = String(payload.start_date ?? "");
  const end = String(payload.end_date ?? "");
  const obj = String(payload.objective ?? "").replace(/_/g, " ");
  return `Backtest · ${start} → ${end} · ${obj}`;
}

export type UiPortfolioJobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed";

/** Map Flask async job status to UI status. */
export function mapApiJobStatus(apiStatus: string): UiPortfolioJobStatus {
  const s = (apiStatus || "").toLowerCase();
  if (s === "completed") return "completed";
  if (s === "failed") return "failed";
  if (s === "running") return "running";
  return "queued";
}

export function formatElapsedSince(
  iso: string | null | undefined,
  nowMs: number
): string {
  if (!iso) return "—";
  const t0 = Date.parse(iso);
  if (Number.isNaN(t0)) return "—";
  const sec = Math.max(0, Math.floor((nowMs - t0) / 1000));
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${s}s`;
}

/** One-line summary after job completes (best-effort from API result shape). */
export function summarizePortfolioJobResult(
  jobType: "optimize" | "backtest",
  result: unknown
): string | null {
  if (result == null || typeof result !== "object") return null;
  const r = result as Record<string, unknown>;
  if (jobType === "optimize") {
    const metrics = r.metrics as Record<string, unknown> | undefined;
    const sr =
      (metrics?.sharpe_ratio as number | undefined) ??
      (r.sharpe_ratio as number | undefined);
    if (typeof sr === "number" && Number.isFinite(sr)) {
      return `Sharpe ${sr.toFixed(3)}`;
    }
  }
  if (jobType === "backtest") {
    const sm = r.summary_metrics as Record<string, unknown> | undefined;
    const sh = sm?.sharpe as number | undefined;
    if (typeof sh === "number" && Number.isFinite(sh)) {
      return `Sharpe ${sh.toFixed(3)}`;
    }
  }
  return "Completed";
}
