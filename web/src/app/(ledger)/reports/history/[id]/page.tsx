"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import LedgerPageHeader from "@/components/LedgerPageHeader";
import {
  buildReportPayload,
  downloadFile,
  mergeOptimizeResponse,
  type ReportContext,
} from "@/lib/reportExport";
import {
  formatOptimizationSource,
  getOptimizationRunById,
  summarizeStoredPayload,
  type StoredOptimizationRun,
} from "@/lib/optimizationRunHistory";
import {
  useNextPageProps,
  type NextClientPagePropsWithId,
} from "@/lib/nextPageProps";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ql-outline-variant/15 bg-ql-surface-container/60 p-3">
      <div className="text-[10px] uppercase tracking-wider text-ql-on-surface-variant mb-1">
        {label}
      </div>
      <div className="text-lg font-headline font-bold text-ql-on-surface tabular-nums">
        {value}
      </div>
    </div>
  );
}

export default function BrowserRunDetailPage(props: NextClientPagePropsWithId) {
  const { params } = useNextPageProps(props);
  const rawId = params.id;
  const id = typeof rawId === "string" ? decodeURIComponent(rawId) : "";
  const [run, setRun] = useState<StoredOptimizationRun | null | undefined>(
    undefined
  );

  useEffect(() => {
    if (!id) {
      setRun(null);
      return;
    }
    setRun(getOptimizationRunById(id));
  }, [id]);

  const merged = useMemo(() => {
    if (!run) return null;
    return mergeOptimizeResponse(run.payload) as Record<string, unknown>;
  }, [run]);

  const metrics = useMemo(() => {
    if (!run) return null;
    return summarizeStoredPayload(run.payload);
  }, [run]);

  const reportCtx = useMemo<ReportContext>(
    () =>
      run
        ? {
            objective: run.objective,
            weightMin: run.constraints.weightMin,
            weightMax: run.constraints.weightMax,
          }
        : {},
    [run]
  );

  const downloadPayloadJson = useCallback(() => {
    if (!run) return;
    downloadFile(
      JSON.stringify(run.payload, null, 2),
      `browser_run_${run.id.slice(0, 8)}_payload.json`,
      "application/json"
    );
  }, [run]);

  const downloadFullReportJson = useCallback(() => {
    if (!run || !merged) return;
    const report = buildReportPayload(
      "full",
      merged,
      run.tickers,
      reportCtx,
      { source: "snapshot", snapshot_at: run.at }
    );
    downloadFile(
      JSON.stringify(report, null, 2),
      `quantum_ledger_full_${run.id.slice(0, 8)}.json`,
      "application/json"
    );
  }, [run, merged, reportCtx]);

  if (run === undefined) {
    return (
      <div className="p-6 lg:p-10 max-w-3xl mx-auto">
        <p className="text-ql-on-surface-variant text-sm animate-pulse">
          Loading…
        </p>
      </div>
    );
  }

  if (run === null) {
    return (
      <div className="p-6 lg:p-10 max-w-3xl mx-auto space-y-4">
        <LedgerPageHeader
          title="Run not found"
          subtitle="This browser run id is missing from local storage (cleared data, another device, or invalid link)."
        />
        <Link
          href="/reports"
          className="inline-block text-sm font-bold text-ql-primary hover:underline"
        >
          ← Back to Reports
        </Link>
      </div>
    );
  }

  const stageInfo = merged?.stage_info;
  const qmeta = merged?.quantum_metadata;

  return (
    <div className="p-6 lg:p-10 max-w-4xl mx-auto space-y-8 print:p-8">
      <LedgerPageHeader
        title="Optimization run (browser)"
        subtitle={`${formatOptimizationSource(run.source)} · ${new Date(run.at).toLocaleString()}`}
      />

      <section className="rounded-xl border border-ql-outline-variant/15 bg-ql-surface-low p-5 space-y-4">
        <h3 className="text-xs uppercase tracking-widest text-ql-on-surface-variant font-bold">
          Run identity
        </h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm font-mono">
          <div>
            <dt className="text-ql-on-surface-variant text-[10px] uppercase mb-0.5">
              Run id
            </dt>
            <dd className="break-all text-ql-on-surface">{run.id}</dd>
          </div>
          <div>
            <dt className="text-ql-on-surface-variant text-[10px] uppercase mb-0.5">
              Source
            </dt>
            <dd className="text-ql-on-surface">
              {formatOptimizationSource(run.source)}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-ql-on-surface-variant text-[10px] uppercase mb-0.5">
              Objective
            </dt>
            <dd className="text-ql-on-surface">{run.objective}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-ql-on-surface-variant text-[10px] uppercase mb-0.5">
              Tickers
            </dt>
            <dd className="break-all text-ql-on-surface">{run.tickers.join(", ")}</dd>
          </div>
          <div>
            <dt className="text-ql-on-surface-variant text-[10px] uppercase mb-0.5">
              Weight bounds
            </dt>
            <dd className="text-ql-on-surface">
              {run.constraints.weightMin} … {run.constraints.weightMax}
            </dd>
          </div>
        </dl>
      </section>

      {metrics && (
        <section className="rounded-xl border border-ql-outline-variant/15 bg-ql-surface-low p-5 space-y-4">
          <h3 className="text-xs uppercase tracking-widest text-ql-on-surface-variant font-bold">
            Key metrics
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Metric
              label="Sharpe"
              value={metrics.sharpe != null ? metrics.sharpe.toFixed(3) : "—"}
            />
            <Metric
              label="Return"
              value={
                metrics.retPct != null ? `${metrics.retPct.toFixed(2)}%` : "—"
              }
            />
            <Metric
              label="Volatility"
              value={
                metrics.volPct != null ? `${metrics.volPct.toFixed(2)}%` : "—"
              }
            />
            <Metric
              label="Active"
              value={
                metrics.nActive != null ? String(metrics.nActive) : "—"
              }
            />
          </div>
        </section>
      )}

      {stageInfo != null && (
        <details className="rounded-xl border border-ql-outline-variant/15 bg-ql-surface-low p-5 text-sm">
          <summary className="cursor-pointer font-bold text-ql-on-surface">
            Pipeline / stage_info
          </summary>
          <pre className="mt-3 text-xs font-mono overflow-auto max-h-64 text-ql-on-surface-variant">
            {JSON.stringify(stageInfo, null, 2)}
          </pre>
        </details>
      )}

      {qmeta != null && typeof qmeta === "object" && (
        <details className="rounded-xl border border-ql-outline-variant/15 bg-ql-surface-low p-5 text-sm">
          <summary className="cursor-pointer font-bold text-ql-on-surface">
            Quantum metadata
          </summary>
          <pre className="mt-3 text-xs font-mono overflow-auto max-h-64 text-ql-on-surface-variant">
            {JSON.stringify(qmeta, null, 2)}
          </pre>
        </details>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={downloadPayloadJson}
          className="px-4 py-2 rounded-lg text-sm font-bold bg-ql-primary/20 text-ql-primary border border-ql-primary/30 hover:bg-ql-primary/30 transition-colors"
        >
          Download raw API payload (JSON)
        </button>
        <button
          type="button"
          onClick={downloadFullReportJson}
          className="px-4 py-2 rounded-lg text-sm font-bold primary-gradient text-[#001D33] shadow-md shadow-ql-primary/15 hover:opacity-95 transition-opacity"
        >
          Download full report bundle (JSON)
        </button>
        <Link
          href="/reports"
          className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-bold border border-ql-outline-variant/30 text-ql-on-surface-variant hover:bg-ql-surface-container no-underline"
        >
          Back to Reports
        </Link>
      </div>
    </div>
  );
}
