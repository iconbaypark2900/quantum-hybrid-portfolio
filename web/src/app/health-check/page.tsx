"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchMarketData,
  healthCheck,
  optimizePortfolio,
} from "@/lib/api";
import { useNextPageProps, type NextClientPageProps } from "@/lib/nextPageProps";

/**
 * Phase 2 proof page: live API health JSON (and Phase 3 smoke: market-data + optimize).
 */
export default function HealthCheckPage(props: NextClientPageProps) {
  useNextPageProps(props);
  const [health, setHealth] = useState<unknown>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [marketLabel, setMarketLabel] = useState<string | null>(null);
  const [optimizeLabel, setOptimizeLabel] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setHealthError(null);
    try {
      const data = await healthCheck();
      setHealth(data);
    } catch (e) {
      setHealth(null);
      setHealthError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHealth();
  }, [loadHealth]);

  const runMarketSmoke = async () => {
    setActionBusy("market");
    setMarketLabel(null);
    try {
      await fetchMarketData(["AAPL", "MSFT"], "2022-01-01", "2023-12-31");
      setMarketLabel("Market data OK");
    } catch (e) {
      setMarketLabel(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(null);
    }
  };

  const runOptimizeSmoke = async () => {
    setActionBusy("optimize");
    setOptimizeLabel(null);
    try {
      const data = await optimizePortfolio({
        tickers: ["AAPL", "MSFT", "GOOGL"],
        objective: "equal_weight",
      });
      const sharpe =
        data &&
        typeof data === "object" &&
        "sharpe_ratio" in data &&
        typeof (data as { sharpe_ratio?: unknown }).sharpe_ratio === "number"
          ? (data as { sharpe_ratio: number }).sharpe_ratio.toFixed(3)
          : "—";
      setOptimizeLabel(`Optimize OK (Sharpe ${sharpe})`);
    } catch (e) {
      setOptimizeLabel(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-mono text-sm">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-xl font-semibold text-white">API health check</h1>
          <Link
            href="/dashboard"
            className="text-ql-primary hover:underline text-xs font-sans"
          >
            ← Dashboard
          </Link>
        </div>

        <p className="text-slate-400 font-sans text-sm">
          Migration Phase 2 proof page. Calls <code className="text-ql-tertiary">GET /api/health</code>{" "}
          via <code className="text-ql-tertiary">web/src/lib/api.ts</code>. Use when Flask is running
          (e.g. <code className="text-ql-tertiary">python -m api</code> on port 5000) and{" "}
          <code className="text-ql-tertiary">NEXT_PUBLIC_API_URL</code> points at the API if not
          using a dev proxy.
        </p>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadHealth()}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 font-sans text-xs"
          >
            Refresh health
          </button>
          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={() => void runMarketSmoke()}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 font-sans text-xs disabled:opacity-50"
          >
            Smoke: market data
          </button>
          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={() => void runOptimizeSmoke()}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 font-sans text-xs disabled:opacity-50"
          >
            Smoke: optimize
          </button>
        </div>

        {marketLabel && (
          <p className="text-slate-300 font-sans text-xs">{marketLabel}</p>
        )}
        {optimizeLabel && (
          <p className="text-slate-300 font-sans text-xs">{optimizeLabel}</p>
        )}

        <div className="rounded-lg border border-slate-800 bg-slate-900/80 p-4 overflow-x-auto">
          {loading && <p className="text-slate-500">Loading…</p>}
          {!loading && healthError && (
            <p className="text-rose-400">
              Error: {healthError}
              <span className="block text-slate-500 mt-2">
                Is the API up? Check NEXT_PUBLIC_API_URL or your dev proxy.
              </span>
            </p>
          )}
          {!loading && !healthError && health !== null && (
            <pre className="whitespace-pre-wrap break-words text-xs text-emerald-200/90">
              {JSON.stringify(health, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
