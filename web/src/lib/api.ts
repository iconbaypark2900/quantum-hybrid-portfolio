/**
 * API client for Quantum Portfolio backend — parity with `frontend/src/services/api.js`.
 * Uses `NEXT_PUBLIC_API_URL` (empty = same-origin; dev often proxies to Flask :5000).
 *
 * Secrets: only `NEXT_PUBLIC_*` vars are embedded in the client bundle; never import
 * server-only keys here (Phase 3 / Checkpoint 3).
 */
import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { toast } from "sonner";

import { extractApiErrorMessage } from "./apiError";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

const defaultHeaders: Record<string, string> = { "Content-Type": "application/json" };
if (API_KEY) {
  defaultHeaders["X-API-Key"] = API_KEY;
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

const api = axios.create({
  baseURL: API_BASE,
  headers: defaultHeaders,
  timeout: 60000,
});

/** When set (e.g. admin static API key), sent as X-Tenant-Id for per-enterprise IBM / integrations. */
export const INTEGRATION_TENANT_STORAGE_KEY = "ql_active_tenant";

export function setActiveIntegrationTenant(tenantId: string | null): void {
  if (typeof window === "undefined") return;
  if (tenantId) {
    localStorage.setItem(INTEGRATION_TENANT_STORAGE_KEY, tenantId);
  } else {
    localStorage.removeItem(INTEGRATION_TENANT_STORAGE_KEY);
  }
}

export function getActiveIntegrationTenant(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(INTEGRATION_TENANT_STORAGE_KEY);
}

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const t = localStorage.getItem(INTEGRATION_TENANT_STORAGE_KEY);
    if (t) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)["X-Tenant-Id"] = t;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    const d = response.data;
    if (d && typeof d === "object" && "data" in d && "meta" in d) {
      response.data = (d as { data: unknown }).data;
    }
    return response;
  },
  async (error: AxiosError) => {
    const status = error.response?.status;
    const config = error.config as RetriableConfig | undefined;

    if (status === 401) {
      toast.error("Unauthorized (401). Check your API key configuration.");
    }
    if (status === 429) {
      toast.warning("Rate limited (429). Please slow down requests.");
    }
    if (status && status >= 500 && config && !config._retried) {
      config._retried = true;
      toast.info("Server error — retrying once...");
      return api(config);
    }

    const respData = error.response?.data;
    const message = extractApiErrorMessage(error, respData);

    return Promise.reject(new Error(message));
  }
);

export async function fetchMarketData(
  tickers: string | string[],
  startDate: string | null = null,
  endDate: string | null = null
) {
  const res = await api.post("/api/market-data", {
    tickers: Array.isArray(tickers)
      ? tickers
      : tickers.split(",").map((t) => t.trim()).filter(Boolean),
    start_date: startDate,
    end_date: endDate,
  });
  return res.data;
}

export async function optimizePortfolio(params: Record<string, unknown>) {
  const res = await api.post("/api/portfolio/optimize", params);
  return res.data;
}

export async function runBacktest(params: Record<string, unknown>) {
  const res = await api.post("/api/portfolio/backtest", params);
  return res.data;
}

export async function runBacktestBatch(
  requests: unknown[],
  stopOnError = false
) {
  const res = await api.post("/api/portfolio/backtest/batch", {
    requests,
    stop_on_error: stopOnError,
  });
  return res.data;
}

export async function optimizeBatch(requests: unknown[], stopOnError = false) {
  const res = await api.post("/api/portfolio/optimize/batch", {
    requests,
    stop_on_error: stopOnError,
  });
  return res.data;
}

export async function getObjectives() {
  const res = await api.get("/api/config/objectives");
  return res.data;
}

export async function getPresets() {
  const res = await api.get("/api/config/presets");
  return res.data;
}

export async function getConstraintsSchema() {
  const res = await api.get("/api/config/constraints");
  return res.data;
}

export async function getEfficientFrontier(
  tickers: string | string[],
  startDate: string | null,
  endDate: string | null,
  nPoints = 15
) {
  const res = await api.post("/api/portfolio/efficient-frontier", {
    tickers: Array.isArray(tickers)
      ? tickers
      : tickers.split(",").map((t) => t.trim()).filter(Boolean),
    start_date: startDate,
    end_date: endDate,
    n_points: nPoints,
  });
  return res.data;
}

export async function setIbmQuantumToken(token: string) {
  const res = await api.post("/api/config/ibm-quantum", { token });
  return res.data;
}

export async function clearIbmQuantumToken() {
  const res = await api.delete("/api/config/ibm-quantum");
  return res.data;
}

export async function getIbmQuantumStatus() {
  const res = await api.get("/api/config/ibm-quantum/status");
  return res.data;
}

/** Row shape from GET /api/config/ibm-quantum/workloads (IBM Runtime job list). */
export interface IbmWorkloadRow {
  job_id: string | null;
  status: string | null;
  status_error?: string;
  backend?: string | null;
  created?: string | null;
  usage_seconds?: number | null;
  instance?: string | null;
  program_id?: string | null;
}

/** Recent IBM Quantum Runtime jobs for the tenant (requires API key; same as token POST). */
export async function getIbmQuantumWorkloads(limit = 20) {
  const res = await api.get("/api/config/ibm-quantum/workloads", {
    params: { limit },
  });
  return res.data as {
    ok: boolean;
    configured: boolean;
    workloads: IbmWorkloadRow[];
    tenant_id?: string;
    error?: string;
  };
}

export async function getIntegrationTenants() {
  const res = await api.get("/api/config/tenants");
  return res.data as { tenants: { id: string; label: string }[] };
}

export async function getIntegrationsCatalog() {
  const res = await api.get("/api/config/integrations");
  return res.data as {
    tenant_id: string;
    providers: Array<Record<string, unknown>>;
  };
}

export async function healthCheck() {
  const res = await api.get("/api/health");
  return res.data;
}

/** Async job queue — see `api.py` `/api/jobs/*`. Body uses `payload` for optimize/backtest params. */
export async function submitOptimizeJob(payload: Record<string, unknown>) {
  const res = await api.post("/api/jobs/optimize", { payload });
  return res.data as { job_id: string; status: string };
}

export async function submitBacktestJob(payload: Record<string, unknown>) {
  const res = await api.post("/api/jobs/backtest", { payload });
  return res.data as { job_id: string; status: string };
}

export async function getJobStatus(jobId: string) {
  const res = await api.get(`/api/jobs/${encodeURIComponent(jobId)}`);
  return res.data as {
    job_id: string;
    job_type: string;
    status: string;
    error?: string | null;
    result?: unknown;
    created_at?: string | null;
    started_at?: string | null;
    finished_at?: string | null;
  };
}

// ─── Lab Runs (durable experiment registry) ─────────────────────────────────

export interface LabRunSpec {
  objective: string;
  weight_min: number;
  weight_max: number;
  seed: number;
  data_mode?: string;
  regime?: string;
  tickers?: string[] | null;
  n_assets?: number | null;
  K?: number | null;
  K_screen?: number | null;
  K_select?: number | null;
  backend_name?: string | null;
  ibm_backend_mode?: string;
}

export interface LabRun {
  id: string;
  tenant_id: string;
  status: "queued" | "running" | "completed" | "failed";
  execution_kind: string;
  spec: LabRunSpec | null;
  result: Record<string, unknown> | null;
  error: string | null;
  external_job_id: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export async function createLabRun(
  payload: Record<string, unknown>,
  options?: { execution_kind?: string }
) {
  const body: Record<string, unknown> = { payload };
  if (options?.execution_kind) {
    body.execution_kind = options.execution_kind;
  }
  const res = await api.post("/api/runs", body);
  return res.data as { run_id: string; status: string };
}

export async function getLabRun(runId: string) {
  const res = await api.get(`/api/runs/${encodeURIComponent(runId)}`);
  return res.data as LabRun;
}

export async function listLabRuns(limit = 20) {
  const res = await api.get("/api/runs", { params: { limit } });
  return res.data as { runs: LabRun[]; count: number };
}

export default api;
