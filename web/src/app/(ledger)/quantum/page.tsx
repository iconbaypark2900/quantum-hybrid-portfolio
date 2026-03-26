"use client";

import { useQuantumEngine } from "@/hooks/useQuantumEngine";
import {
  formatElapsedSince,
  MAX_IBM_VQE_ASSETS,
} from "@/lib/quantumPortfolioJobs";
import { apiHealthPresentation } from "@/lib/quantumHealth";
import LedgerPageHeader from "@/components/LedgerPageHeader";
import SessionBanner from "@/components/SessionBanner";

export default function QuantumPage() {
  const {
    ibm,
    token,
    setToken,
    connecting,
    bootstrapLoading,
    apiHealth,
    bannerError,
    portfolioJobsContext,
    clockMs,
    jobs,
    ibmWorkloads,
    ibmWorkloadsLoading,
    ibmWorkloadsError,
    refreshIbmWorkloads,
    tenants,
    activeTenantId,
    setActiveTenant,
    integrations,
    handleConnect,
    handleDisconnect,
    submitJob,
  } = useQuantumEngine();

  const braketProvider = integrations?.providers?.find(
    (p) => p.id === "braket"
  ) as
    | {
        configured?: boolean;
        env_enabled?: boolean;
        note?: string;
      }
    | undefined;

  const health = apiHealthPresentation(apiHealth);
  const nowMs = clockMs;

  const healthColor =
    health.tone === "ok"
      ? "text-ql-tertiary"
      : health.tone === "warn"
        ? "text-amber-400"
        : health.tone === "bad"
          ? "text-ql-error"
          : "text-ql-on-surface-variant";

  return (
    <div className="p-6 lg:p-10 space-y-8">
      <LedgerPageHeader
        title="Quantum Engine"
        subtitle="IBM Runtime workloads (your account), portfolio async jobs, and integrations"
      />

      <SessionBanner />

      <div className="flex flex-col sm:flex-row sm:items-end gap-4 bg-ql-surface-low rounded-xl p-4 border border-ql-outline-variant/10">
        <div className="flex-1 min-w-0">
          <label
            htmlFor="enterprise-select"
            className="text-[10px] font-bold uppercase tracking-widest text-ql-on-surface-variant block mb-2"
          >
            Enterprise (tenant)
          </label>
          <select
            id="enterprise-select"
            value={activeTenantId}
            onChange={(e) => void setActiveTenant(e.target.value)}
            disabled={bootstrapLoading || tenants.length === 0}
            className="w-full max-w-md bg-ql-surface-lowest border border-ql-outline-variant/20 rounded-lg px-3 py-2.5 text-sm font-mono focus:border-ql-primary focus:ring-1 focus:ring-ql-primary/30 outline-none"
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
          <p className="text-[10px] text-ql-on-surface-variant mt-2">
            With a static admin API key, pick the tenant for IBM tokens and integration
            status. The browser sends <code className="font-mono">X-Tenant-Id</code> on API
            calls. Portfolio Lab uses the same header so optimizations resolve IBM access
            for that enterprise.
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-ql-surface-container/40 border border-ql-outline-variant/10 px-4 py-3 text-xs text-ql-on-surface-variant">
        <span className="material-symbols-outlined text-sm align-middle mr-1">info</span>
        IBM tokens are stored <strong className="text-ql-on-surface">per tenant</strong> in
        the API SQLite DB (encrypted when{" "}
        <code className="font-mono text-[10px]">INTEGRATION_ENCRYPTION_KEY</code> is set).
        You can also connect from{" "}
        <a href="/portfolio" className="text-ql-primary font-bold hover:underline">Portfolio Lab</a>
        — use the same enterprise selection so the token applies to the same{" "}
        <code className="font-mono text-[10px]">tenant_id</code>.
      </div>

      {bannerError && (
        <div
          className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200"
          role="alert"
        >
          {bannerError}
        </div>
      )}

      <div
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
      >
        {ibm.configured
          ? `IBM Quantum connected, ${ibm.backends?.length ?? 0} backends available.`
          : "IBM Quantum not configured; simulator mode."}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-8 bg-ql-surface-low rounded-xl p-6">
          <h3 className="font-headline text-lg font-bold mb-6">
            Engine Telemetry
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              {
                label: "Enterprise",
                value: activeTenantId || "—",
                color: "text-ql-secondary",
              },
              {
                label: "Mode",
                value: ibm.configured ? "Hardware" : "Simulator",
                color: ibm.configured ? "text-ql-tertiary" : "text-ql-primary",
              },
              {
                label: "Backends",
                value: ibm.backends?.length
                  ? String(ibm.backends.length)
                  : "0",
                color: "",
              },
              {
                label: "API Status",
                value: bootstrapLoading ? "…" : health.label,
                color: bootstrapLoading ? "text-ql-on-surface-variant" : healthColor,
              },
              {
                label: "Portfolio jobs active",
                value: String(
                  jobs.filter(
                    (j) => j.status === "queued" || j.status === "running"
                  ).length
                ),
                color: "text-ql-primary",
              },
              {
                label: "IBM workloads listed",
                value: ibm.configured
                  ? String(ibmWorkloads.length)
                  : "—",
                color: "text-ql-secondary",
              },
            ].map((m) => (
              <div
                key={m.label}
                className="bg-ql-surface-container/60 backdrop-blur p-4 rounded-lg border border-ql-outline-variant/10"
              >
                <p className="text-[10px] text-ql-on-surface-variant uppercase font-bold tracking-widest">
                  {m.label}
                </p>
                <p
                  className={`text-xl font-headline font-bold mt-1 ${m.color}`}
                >
                  {m.value}
                </p>
              </div>
            ))}
          </div>

          {ibm.configured && ibm.backends?.length ? (
            <div className="mt-6">
              <p className="text-[10px] text-ql-on-surface-variant uppercase tracking-widest font-bold mb-2">
                Available Backends
              </p>
              <div className="flex flex-wrap gap-2">
                {ibm.backends.map((b) => (
                  <span
                    key={b}
                    className="px-3 py-1 bg-ql-surface-container text-xs font-mono rounded-lg border border-ql-outline-variant/10"
                  >
                    {b}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {ibm.error ? (
            <p className="mt-4 text-xs text-ql-error font-mono" role="status">
              {ibm.error}
            </p>
          ) : null}
        </div>

        <div className="md:col-span-4 bg-ql-surface-container rounded-xl p-6">
          <h3 className="font-headline text-lg font-bold mb-2">IBM Quantum</h3>
          <p className="text-xs text-ql-on-surface-variant mb-4 leading-relaxed">
            Get a token from{" "}
            <a
              href="https://quantum.ibm.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-ql-primary underline underline-offset-2"
            >
              quantum.ibm.com
            </a>
            . Sent to <code className="text-[10px] font-mono">POST /api/config/ibm-quantum</code>{" "}
            for the <strong className="text-ql-on-surface">selected enterprise</strong>, persisted
            server-side (not in the Next.js bundle).
          </p>
          <div
            className="flex items-center gap-2 mb-6"
            role="status"
            aria-label={
              ibm.configured
                ? "IBM Quantum connected"
                : "Simulator mode, IBM Quantum not connected"
            }
          >
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                ibm.configured ? "bg-ql-tertiary" : "bg-ql-on-surface-variant"
              }`}
              aria-hidden
            />
            <span
              className={`text-xs font-bold uppercase ${
                ibm.configured ? "text-ql-tertiary" : "text-ql-on-surface-variant"
              }`}
            >
              {ibm.configured ? "Connected" : "Simulator Mode"}
            </span>
          </div>

          {!ibm.configured ? (
            <div className="space-y-3">
              <label className="sr-only" htmlFor="ibm-quantum-token">
                IBM Quantum API token
              </label>
              <input
                id="ibm-quantum-token"
                type="password"
                autoComplete="off"
                placeholder="IBM Quantum API token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void handleConnect()}
                className="w-full bg-ql-surface-lowest border border-ql-outline-variant/20 rounded-lg px-3 py-2.5 text-sm font-mono focus:border-ql-primary focus:ring-1 focus:ring-ql-primary/30 outline-none"
              />
              <button
                type="button"
                onClick={() => void handleConnect()}
                disabled={connecting || !token.trim()}
                className="w-full py-2.5 bg-ql-surface-high border border-ql-outline-variant/20 rounded-lg text-sm font-bold text-ql-primary hover:bg-ql-surface-highest transition-colors disabled:opacity-50"
              >
                {connecting ? "Connecting..." : "Connect"}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => void handleDisconnect()}
              disabled={connecting}
              className="w-full py-2.5 border border-ql-outline-variant/20 rounded-lg text-sm font-bold text-ql-error hover:bg-ql-error/10 transition-colors disabled:opacity-50"
            >
              {connecting ? "Disconnecting..." : "Disconnect"}
            </button>
          )}
        </div>

        <div className="md:col-span-12 bg-ql-surface-container rounded-xl p-6 border border-ql-outline-variant/10">
          <h3 className="font-headline text-lg font-bold mb-4">
            Integration coverage
          </h3>
          <p className="text-xs text-ql-on-surface-variant mb-4">
            Status for the active enterprise (
            <span className="font-mono text-ql-primary">{activeTenantId || "—"}</span>
            ). Braket follows the same tenant metadata pattern; AWS credentials typically stay
            in server environment / IAM.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-ql-surface-low rounded-lg p-4 border border-ql-outline-variant/10">
              <p className="text-[10px] font-bold uppercase text-ql-on-surface-variant mb-1">
                IBM Quantum
              </p>
              <p className="text-sm font-bold text-ql-on-surface">
                {ibm.configured ? "Connected" : "Not configured"}
              </p>
              <p className="text-[11px] text-ql-on-surface-variant mt-1">
                {ibm.backends?.length
                  ? `${ibm.backends.length} backends visible`
                  : "No backends listed"}
              </p>
            </div>
            <div className="bg-ql-surface-low rounded-lg p-4 border border-ql-outline-variant/10">
              <p className="text-[10px] font-bold uppercase text-ql-on-surface-variant mb-1">
                AWS Braket
              </p>
              <p className="text-sm font-bold text-ql-on-surface">
                {braketProvider?.configured
                  ? "Enabled (env)"
                  : "Not enabled"}
              </p>
              <p className="text-[11px] text-ql-on-surface-variant mt-1">
                {braketProvider?.note ??
                  "Set BRAKET_ENABLED=true and BRAKET_* on the API server for annealing jobs."}
              </p>
            </div>
          </div>
        </div>

        <div className="md:col-span-12 bg-ql-surface-low rounded-xl p-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-4">
            <div>
              <h3 className="font-headline text-lg font-bold">
                IBM Runtime workloads
              </h3>
              <p className="text-[11px] text-ql-on-surface-variant mt-1 max-w-2xl">
                Recent jobs from your IBM Quantum account (same view as quantum.ibm.com
                &quot;My Recent Workloads&quot;). Requires{" "}
                <code className="font-mono text-[10px]">GET /api/config/ibm-quantum/workloads</code>{" "}
                with API key.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void refreshIbmWorkloads()}
              disabled={!ibm.configured || ibmWorkloadsLoading}
              className="shrink-0 px-4 py-2 bg-ql-surface-container text-xs font-bold rounded-lg hover:bg-ql-surface-high transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {ibmWorkloadsLoading ? "Refreshing…" : "Refresh IBM workloads"}
            </button>
          </div>

          <div
            className="sr-only"
            aria-live="polite"
            aria-atomic="true"
          >
            {ibm.configured && !ibmWorkloadsLoading
              ? `${ibmWorkloads.length} IBM Runtime workloads listed.`
              : ""}
          </div>

          {ibmWorkloadsError ? (
            <p className="text-sm text-ql-error font-mono mb-4" role="status">
              {ibmWorkloadsError}
            </p>
          ) : null}

          {!ibm.configured ? (
            <p className="text-ql-on-surface-variant text-sm py-6 text-center border border-dashed border-ql-outline-variant/30 rounded-lg">
              Connect IBM Quantum to list Runtime jobs for your API token.
            </p>
          ) : ibmWorkloadsLoading && ibmWorkloads.length === 0 ? (
            <p className="text-ql-on-surface-variant text-sm py-8 text-center">
              Loading IBM workloads…
            </p>
          ) : ibmWorkloads.length === 0 ? (
            <p className="text-ql-on-surface-variant text-sm py-6 text-center border border-dashed border-ql-outline-variant/30 rounded-lg">
              No recent IBM Runtime jobs returned for this account (last 20). Submit
              jobs from Qiskit or the IBM console, then refresh.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-ql-outline-variant/10">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-ql-outline-variant/20 text-[10px] uppercase tracking-widest text-ql-on-surface-variant">
                    <th className="py-2 pr-3 font-bold">Job ID</th>
                    <th className="py-2 pr-3 font-bold">Status</th>
                    <th className="py-2 pr-3 font-bold">QPU</th>
                    <th className="py-2 pr-3 font-bold">Created</th>
                    <th className="py-2 pr-3 font-bold">Usage</th>
                    <th className="py-2 font-bold">Instance</th>
                  </tr>
                </thead>
                <tbody>
                  {ibmWorkloads.map((w, idx) => (
                    <tr
                      key={w.job_id ?? `ibm-wl-${idx}`}
                      className="border-b border-ql-outline-variant/10 last:border-0"
                    >
                      <td
                        className="py-2 pr-3 font-mono text-xs max-w-[140px] truncate"
                        title={w.job_id ?? undefined}
                      >
                        {w.job_id ?? "—"}
                      </td>
                      <td className="py-2 pr-3">
                        <span className="text-xs font-bold uppercase">
                          {w.status ?? w.status_error ?? "—"}
                        </span>
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {w.backend ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-xs text-ql-on-surface-variant">
                        {w.created
                          ? new Date(w.created).toLocaleString()
                          : "—"}
                      </td>
                      <td className="py-2 pr-3 text-xs">
                        {w.usage_seconds != null
                          ? `${w.usage_seconds.toFixed(1)}s`
                          : "—"}
                      </td>
                      <td className="py-2 font-mono text-[10px] max-w-[180px] truncate" title={w.instance ?? undefined}>
                        {w.instance ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="md:col-span-12 bg-ql-surface-low rounded-xl p-6 border border-ql-primary/15">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
            <div className="min-w-0 space-y-2">
              <h3 className="font-headline text-lg font-bold">
                IBM VQE — tickers &amp; prices
              </h3>
              <p className="text-[11px] text-ql-on-surface-variant leading-relaxed max-w-3xl">
                Queues the same async optimize job as below, but forces{" "}
                <code className="font-mono text-[10px]">objective: &quot;vqe&quot;</code>. The API
                loads returns and covariance from your Ledger tickers; when an IBM token is stored
                and the universe is small enough, the optimizer may run on IBM hardware (otherwise
                it falls back to classical simulation).
              </p>
              <ul className="text-[10px] text-ql-on-surface-variant space-y-1 font-mono">
                <li>
                  IBM token:{" "}
                  {ibm.configured ? (
                    <span className="text-ql-tertiary">connected</span>
                  ) : (
                    <span className="text-amber-400">not connected — connect above to enable hardware</span>
                  )}
                </li>
                <li>
                  Universe size: {portfolioJobsContext.tickerCount} / {MAX_IBM_VQE_ASSETS} (recommended
                  max for hardware)
                  {portfolioJobsContext.tickerCount > MAX_IBM_VQE_ASSETS ? (
                    <span className="text-amber-400">
                      {" "}
                      — server may fall back to simulation for large N
                    </span>
                  ) : null}
                </li>
              </ul>
            </div>
            <div className="flex flex-col gap-2 shrink-0 sm:items-end">
              <button
                type="button"
                onClick={() => void submitJob("optimize", { vqeIbm: true })}
                disabled={portfolioJobsContext.tickerCount === 0}
                title={
                  portfolioJobsContext.tickerCount === 0
                    ? "Set tickers in Portfolio Lab or Strategy Builder"
                    : "Queue VQE optimize (IBM path when configured)"
                }
                className="px-4 py-2 bg-ql-primary/20 text-ql-primary text-xs font-bold rounded-lg hover:bg-ql-primary/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed border border-ql-primary/30"
              >
                Run VQE optimize job
              </button>
              <button
                type="button"
                onClick={() => void refreshIbmWorkloads()}
                disabled={ibmWorkloadsLoading || !ibm.configured}
                className="px-3 py-1.5 text-[10px] font-bold text-ql-on-surface-variant hover:text-ql-on-surface disabled:opacity-40"
              >
                Refresh IBM workloads
              </button>
            </div>
          </div>
        </div>

        <div className="md:col-span-12 bg-ql-surface-low rounded-xl p-6">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4 mb-4">
            <div className="min-w-0">
              <h3 className="font-headline text-lg font-bold">Portfolio jobs</h3>
              <p className="text-[11px] text-ql-on-surface-variant mt-1 leading-relaxed max-w-3xl">
                Uses the <strong className="text-ql-on-surface">current Ledger session</strong>{" "}
                (same objective, tickers, and weight bounds as the banner above — set them in{" "}
                <a href="/portfolio" className="text-ql-primary font-bold hover:underline">
                  Portfolio Lab
                </a>{" "}
                or{" "}
                <a href="/strategy" className="text-ql-primary font-bold hover:underline">
                  Strategy Builder
                </a>
                ). Async runs call Flask{" "}
                <code className="font-mono text-[10px]">/api/jobs/*</code> (server-side queue, not
                the IBM Runtime list). With IBM connected, objective{" "}
                <code className="font-mono text-[10px]">vqe</code> can use hardware via the API
                optimizer path.
              </p>
              <ul className="mt-2 text-[10px] text-ql-on-surface-variant space-y-0.5 font-mono">
                <li>
                  Session: {portfolioJobsContext.objective.replace(/_/g, " ")} ·{" "}
                  {portfolioJobsContext.tickerCount} ticker
                  {portfolioJobsContext.tickerCount === 1 ? "" : "s"} · weights{" "}
                  {portfolioJobsContext.weightRange}
                </li>
                <li>
                  Backtest window (default): {portfolioJobsContext.backtestStart} →{" "}
                  {portfolioJobsContext.backtestEnd} (monthly rebalance)
                </li>
              </ul>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                type="button"
                onClick={() => void submitJob("optimize")}
                disabled={portfolioJobsContext.tickerCount === 0}
                title={
                  portfolioJobsContext.tickerCount === 0
                    ? "Set tickers in Portfolio Lab or Strategy Builder"
                    : "Queue optimize using current session"
                }
                className="px-4 py-2 bg-ql-surface-container text-xs font-bold rounded-lg hover:bg-ql-surface-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                + Optimize Job
              </button>
              <button
                type="button"
                onClick={() => void submitJob("backtest")}
                disabled={portfolioJobsContext.tickerCount === 0}
                title={
                  portfolioJobsContext.tickerCount === 0
                    ? "Set tickers in Portfolio Lab or Strategy Builder"
                    : "Queue backtest using current session"
                }
                className="px-4 py-2 bg-ql-surface-container text-xs font-bold rounded-lg hover:bg-ql-surface-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                + Backtest Job
              </button>
            </div>
          </div>

          {jobs.length > 0 ? (
            <ul className="space-y-2 list-none p-0 m-0" aria-live="polite">
              {jobs.map((j) => {
                const active = j.status === "queued" || j.status === "running";
                const elapsedFrom = j.startedAtIso ?? j.queuedAtIso;
                const badge =
                  (j.serverStatusLabel ?? j.status).toUpperCase();
                return (
                <li
                  key={j.localId}
                  className="px-4 py-3 bg-ql-surface-container/40 rounded-lg border border-ql-outline-variant/5"
                >
                  <div className="flex items-start gap-3 flex-wrap">
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${
                        j.status === "completed"
                          ? "bg-ql-tertiary"
                          : j.status === "failed"
                            ? "bg-ql-error"
                            : j.status === "running"
                              ? "bg-ql-primary animate-pulse"
                              : "bg-ql-on-surface-variant"
                      }`}
                      aria-hidden
                    />
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <span className="text-xs font-mono text-ql-on-surface-variant">
                          {(j.serverJobId ?? j.localId).slice(0, 8)}
                        </span>
                        <span
                          className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            j.status === "completed"
                              ? "bg-ql-tertiary/10 text-ql-tertiary"
                              : j.status === "failed"
                                ? "bg-ql-error/10 text-ql-error"
                                : j.status === "running"
                                  ? "bg-ql-primary/10 text-ql-primary"
                                  : "bg-ql-on-surface-variant/10 text-ql-on-surface-variant"
                          }`}
                        >
                          {badge}
                        </span>
                        {active ? (
                          <span className="text-[10px] font-mono text-ql-primary">
                            Elapsed {formatElapsedSince(elapsedFrom, nowMs)}
                          </span>
                        ) : null}
                        <span className="text-[10px] text-ql-on-surface-variant ml-auto">
                          Started {j.submitted}
                        </span>
                      </div>
                      <p className="text-xs text-ql-on-surface leading-snug">
                        {j.detailLine}
                      </p>
                      {j.status === "failed" && j.errorMessage ? (
                        <p className="text-[11px] text-ql-error font-mono break-words">
                          {j.errorMessage}
                        </p>
                      ) : null}
                      {j.status === "completed" && j.summaryLine ? (
                        <p className="text-[11px] text-ql-tertiary font-mono font-bold">
                          {j.summaryLine}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </li>
              );
              })}
            </ul>
          ) : (
            <p className="text-ql-on-surface-variant text-sm text-center py-8">
              {portfolioJobsContext.tickerCount === 0
                ? "Choose tickers in Portfolio Lab or Strategy Builder, then queue an optimize or backtest job here."
                : "No jobs submitted yet. Jobs use your Ledger session (shown above)."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
