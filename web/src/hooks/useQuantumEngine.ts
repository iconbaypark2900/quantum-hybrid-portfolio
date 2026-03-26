"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import type { LedgerConstraints } from "@/context/LedgerSessionContext";
import {
  clearIbmQuantumToken,
  getActiveIntegrationTenant,
  getIbmQuantumStatus,
  getIbmQuantumWorkloads,
  getIntegrationTenants,
  getIntegrationsCatalog,
  getJobStatus,
  healthCheck,
  setActiveIntegrationTenant,
  setIbmQuantumToken,
  submitBacktestJob,
  submitOptimizeJob,
  type IbmWorkloadRow,
} from "@/lib/api";
import {
  buildBacktestJobPayload,
  buildOptimizeJobPayload,
  buildVqeIbmOptimizePayload,
  defaultBacktestDateRange,
  formatBacktestDetailLine,
  formatOptimizeDetailLine,
  formatVqeIbmOptimizeDetailLine,
  mapApiJobStatus,
  summarizePortfolioJobResult,
} from "@/lib/quantumPortfolioJobs";

export interface QuantumIbmStatus {
  configured: boolean;
  backends?: string[];
  error?: string;
  tenant_id?: string;
}

export interface IntegrationTenant {
  id: string;
  label: string;
}

export interface QuantumJobEntry {
  localId: string;
  serverJobId: string | null;
  type: "optimize" | "backtest";
  status: "queued" | "running" | "completed" | "failed";
  submitted: string;
  objective?: string;
  /** Human-readable line: optimize vs backtest context */
  detailLine: string;
  /** When the row was created (client), for elapsed if server has no started_at yet */
  queuedAtIso: string;
  startedAtIso?: string | null;
  /** Raw status from API while polling */
  serverStatusLabel?: string;
  errorMessage?: string | null;
  /** Short line after success (e.g. Sharpe) */
  summaryLine?: string | null;
}

type PendingOptimizeMeta = {
  tickers: string[];
  objective: string;
  constraints: LedgerConstraints;
  payload: Record<string, unknown>;
};

/** Options for {@link useQuantumEngine}'s `submitJob` (optimize only). */
export type SubmitJobOptions = {
  /** Force `objective: "vqe"` for IBM-capable path; same async queue as optimize. */
  vqeIbm?: boolean;
};

export function useQuantumEngine() {
  const { session, setLastOptimize } = useLedgerSession();
  const [ibm, setIbm] = useState<QuantumIbmStatus>({ configured: false });
  const [token, setToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [bootstrapLoading, setBootstrapLoading] = useState(true);
  const [apiHealth, setApiHealth] = useState<Record<string, unknown> | null>(
    null
  );
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<QuantumJobEntry[]>([]);
  const [tenants, setTenants] = useState<IntegrationTenant[]>([]);
  const [activeTenantId, setActiveTenantIdState] = useState<string>("");
  const [integrations, setIntegrations] = useState<{
    tenant_id: string;
    providers: Array<Record<string, unknown>>;
  } | null>(null);
  const [ibmWorkloads, setIbmWorkloads] = useState<IbmWorkloadRow[]>([]);
  const [ibmWorkloadsLoading, setIbmWorkloadsLoading] = useState(false);
  const [ibmWorkloadsError, setIbmWorkloadsError] = useState<string | null>(
    null
  );

  const pollTimersRef = useRef<Map<string, ReturnType<typeof setInterval>>>(
    new Map()
  );
  const pendingOptimizeMetaRef = useRef<Map<string, PendingOptimizeMeta>>(
    new Map()
  );

  const [clockMs, setClockMs] = useState(() => Date.now());
  useEffect(() => {
    const active = jobs.some(
      (j) => j.status === "queued" || j.status === "running"
    );
    if (!active) return;
    const id = window.setInterval(() => {
      setClockMs(Date.now());
    }, 1000);
    return () => window.clearInterval(id);
  }, [jobs]);

  const clearJobPoll = useCallback((localId: string) => {
    const t = pollTimersRef.current.get(localId);
    if (t) {
      clearInterval(t);
      pollTimersRef.current.delete(localId);
    }
  }, []);

  const refreshIbmAndIntegrations = useCallback(async () => {
    const status = (await getIbmQuantumStatus()) as QuantumIbmStatus;
    setIbm(status);
    try {
      const cat = await getIntegrationsCatalog();
      setIntegrations(cat);
    } catch {
      setIntegrations(null);
    }
  }, []);

  const refreshIbmWorkloads = useCallback(async () => {
    setIbmWorkloadsLoading(true);
    setIbmWorkloadsError(null);
    try {
      const data = await getIbmQuantumWorkloads(20);
      setIbmWorkloads(data.workloads ?? []);
    } catch (e) {
      setIbmWorkloads([]);
      setIbmWorkloadsError(
        e instanceof Error ? e.message : "Failed to load IBM workloads"
      );
    } finally {
      setIbmWorkloadsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setBootstrapLoading(true);
    setBannerError(null);

    (async () => {
      try {
        const health = (await healthCheck()) as Record<string, unknown>;
        if (!cancelled) {
          setApiHealth(health);
        }
      } catch (e) {
        if (!cancelled) {
          setApiHealth(null);
          setBannerError(
            e instanceof Error ? e.message : "Could not reach API health endpoint."
          );
        }
      }

      try {
        const data = await getIntegrationTenants();
        const list = data.tenants ?? [];
        let tid = getActiveIntegrationTenant();
        if (!tid && list.length) tid = list[0].id;
        if (tid && list.length && !list.some((x) => x.id === tid)) {
          tid = list[0].id;
        }
        if (tid) setActiveIntegrationTenant(tid);
        if (!cancelled) {
          setTenants(list);
          setActiveTenantIdState(tid ?? "");
        }
      } catch {
        if (!cancelled) {
          setTenants([{ id: "default", label: "Default" }]);
          setActiveTenantIdState("default");
        }
      }

      try {
        await refreshIbmAndIntegrations();
      } catch (e) {
        if (!cancelled) {
          setIbm((prev) => ({
            ...prev,
            error:
              e instanceof Error
                ? e.message
                : "Could not load IBM Quantum status.",
          }));
        }
      } finally {
        if (!cancelled) {
          setBootstrapLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [refreshIbmAndIntegrations]);

  useEffect(() => {
    if (!ibm.configured) {
      setIbmWorkloads([]);
      setIbmWorkloadsError(null);
      setIbmWorkloadsLoading(false);
      return;
    }
    let cancelled = false;
    void (async () => {
      setIbmWorkloadsLoading(true);
      setIbmWorkloadsError(null);
      try {
        const data = await getIbmQuantumWorkloads(20);
        if (!cancelled) {
          setIbmWorkloads(data.workloads ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          setIbmWorkloads([]);
          setIbmWorkloadsError(
            e instanceof Error ? e.message : "Failed to load IBM workloads"
          );
        }
      } finally {
        if (!cancelled) {
          setIbmWorkloadsLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ibm.configured, activeTenantId]);

  useEffect(() => {
    const timersRef = pollTimersRef;
    return () => {
      const pending = timersRef.current;
      pending.forEach((t) => clearInterval(t));
      pending.clear();
    };
  }, []);

  const setActiveTenant = useCallback(
    async (tenantId: string) => {
      setActiveIntegrationTenant(tenantId);
      setActiveTenantIdState(tenantId);
      setBannerError(null);
      try {
        await refreshIbmAndIntegrations();
      } catch (e) {
        setBannerError(
          e instanceof Error ? e.message : "Could not refresh tenant context."
        );
      }
    },
    [refreshIbmAndIntegrations]
  );

  const handleConnect = useCallback(async () => {
    if (!token.trim()) return;
    setConnecting(true);
    setBannerError(null);
    try {
      await setIbmQuantumToken(token.trim());
      await refreshIbmAndIntegrations();
      setToken("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Connection failed";
      setBannerError(msg);
    } finally {
      setConnecting(false);
    }
  }, [token, refreshIbmAndIntegrations]);

  const handleDisconnect = useCallback(async () => {
    setConnecting(true);
    setBannerError(null);
    try {
      await clearIbmQuantumToken();
      await refreshIbmAndIntegrations();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Disconnect failed";
      setBannerError(msg);
    } finally {
      setConnecting(false);
    }
  }, [refreshIbmAndIntegrations]);

  const submitJob = useCallback(
    async (type: "optimize" | "backtest", options?: SubmitJobOptions) => {
      if (!session.tickers.length) {
        setBannerError(
          "No tickers in the current Ledger session. Set your universe in Portfolio Lab or Strategy Builder first."
        );
        return;
      }

      const localId = crypto.randomUUID();
      const vqeIbm = type === "optimize" && Boolean(options?.vqeIbm);
      const payload =
        type === "optimize"
          ? vqeIbm
            ? buildVqeIbmOptimizePayload(session)
            : buildOptimizeJobPayload(session)
          : buildBacktestJobPayload(session);

      const queuedAtIso = new Date().toISOString();
      const detailLine =
        type === "optimize"
          ? vqeIbm
            ? formatVqeIbmOptimizeDetailLine(session)
            : formatOptimizeDetailLine(session)
          : formatBacktestDetailLine(payload);

      const entryObjective =
        type === "optimize" && vqeIbm ? "vqe" : session.objective;

      const entry: QuantumJobEntry = {
        localId,
        serverJobId: null,
        type,
        status: "queued",
        submitted: new Date().toLocaleTimeString(),
        objective: entryObjective,
        detailLine,
        queuedAtIso,
      };
      setJobs((prev) => [entry, ...prev]);
      setBannerError(null);

      if (type === "optimize") {
        pendingOptimizeMetaRef.current.set(localId, {
          tickers: [...session.tickers],
          objective: entryObjective,
          constraints: { ...session.constraints },
          payload: { ...payload },
        });
      }

      try {
        const data =
          type === "optimize"
            ? await submitOptimizeJob(payload)
            : await submitBacktestJob(payload);
        const serverJobId = data.job_id;
        const initialUi = mapApiJobStatus(data.status || "queued");
        setJobs((prev) =>
          prev.map((j) =>
            j.localId === localId
              ? {
                  ...j,
                  serverJobId,
                  status: initialUi,
                  serverStatusLabel: data.status ?? "queued",
                }
              : j
          )
        );

        const pollOnce = async () => {
          try {
            const job = await getJobStatus(serverJobId);
            const st = job.status;
            const ui = mapApiJobStatus(st);
            const summary =
              ui === "completed"
                ? summarizePortfolioJobResult(type, job.result)
                : null;

            setJobs((prev) =>
              prev.map((j) => {
                if (j.localId !== localId) return j;
                return {
                  ...j,
                  status: ui,
                  serverStatusLabel: st,
                  startedAtIso: job.started_at ?? j.startedAtIso ?? null,
                  errorMessage:
                    ui === "failed"
                      ? (job.error != null && String(job.error).trim() !== ""
                          ? String(job.error)
                          : "Job failed")
                      : null,
                  summaryLine:
                    ui === "completed" ? (summary ?? j.summaryLine) : j.summaryLine,
                };
              })
            );

            if (st === "completed" || st === "failed") {
              clearJobPoll(localId);
              if (type === "optimize" && st === "completed") {
                const meta = pendingOptimizeMetaRef.current.get(localId);
                pendingOptimizeMetaRef.current.delete(localId);
                if (meta) {
                  setLastOptimize(
                    {
                      at: new Date().toISOString(),
                      tickers: meta.tickers,
                      objective: meta.objective,
                      constraints: meta.constraints,
                      payload: {
                        ...meta.payload,
                        result: job.result ?? undefined,
                      },
                    },
                    { source: "quantum_engine" }
                  );
                }
              } else if (type === "optimize" && st === "failed") {
                pendingOptimizeMetaRef.current.delete(localId);
              }
            }
          } catch {
            clearJobPoll(localId);
            pendingOptimizeMetaRef.current.delete(localId);
            setJobs((prev) =>
              prev.map((j) =>
                j.localId === localId
                  ? {
                      ...j,
                      status: "failed" as const,
                      errorMessage: "Lost connection to job status",
                    }
                  : j
              )
            );
          }
        };
        void pollOnce();
        const interval = setInterval(() => {
          void pollOnce();
        }, 2000);
        pollTimersRef.current.set(localId, interval);
      } catch (e) {
        pendingOptimizeMetaRef.current.delete(localId);
        const msg = e instanceof Error ? e.message : "Job submission failed";
        setBannerError(msg);
        setJobs((prev) =>
          prev.map((j) =>
            j.localId === localId ? { ...j, status: "failed" as const } : j
          )
        );
      }
    },
    [clearJobPoll, session, setLastOptimize]
  );

  const br = defaultBacktestDateRange();
  const portfolioJobsContext = {
    tickerCount: session.tickers.length,
    objective: session.objective,
    backtestStart: br.start_date,
    backtestEnd: br.end_date,
    weightRange: `${session.constraints.weightMin.toFixed(3)}–${session.constraints.weightMax.toFixed(2)}`,
  };

  return {
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
  };
}
