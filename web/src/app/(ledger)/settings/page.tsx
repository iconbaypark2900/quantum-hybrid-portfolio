"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import LedgerPageHeader from "@/components/LedgerPageHeader";
import { useNextPageProps, type NextClientPageProps } from "@/lib/nextPageProps";
import {
  setIbmQuantumToken,
  verifyIbmQuantumToken,
  clearIbmQuantumToken,
  getIbmQuantumStatus,
  getIntegrationTenants,
  setActiveIntegrationTenant,
  INTEGRATION_TENANT_STORAGE_KEY,
  runBraketSmokeTest,
  createTenant,
  type BraketSmokeTestResult,
} from "@/lib/api";

const ENV_VARS: { name: string; desc: string; required: boolean }[] = [
  {
    name: "NEXT_PUBLIC_API_URL",
    desc: "Base URL for the Flask backend (empty = same-origin proxy).",
    required: false,
  },
  {
    name: "NEXT_PUBLIC_API_KEY",
    desc: "API key sent as X-API-Key header. Omit for unauthenticated local dev.",
    required: false,
  },
];

export default function SettingsPage(props: NextClientPageProps) {
  useNextPageProps(props);
  const { session } = useLedgerSession();

  const copySessionJson = useCallback(() => {
    navigator.clipboard.writeText(JSON.stringify(session, null, 2));
    toast.success("Session JSON copied to clipboard");
  }, [session]);

  // ── IBM Quantum panel state ──────────────────────────────────────────
  const [ibmToken, setIbmToken] = useState("");
  const [ibmInstance, setIbmInstance] = useState("");
  const [ibmStatus, setIbmStatus] = useState<"idle" | "saving" | "verifying" | "ok" | "error">("idle");
  const [ibmMessage, setIbmMessage] = useState("");
  const [ibmConnected, setIbmConnected] = useState<boolean | null>(null);

  // ── Tenant panel state ───────────────────────────────────────────────
  const [activeTenant, setActiveTenantLocal] = useState(
    () => (typeof window !== "undefined" ? (localStorage.getItem(INTEGRATION_TENANT_STORAGE_KEY) ?? "default") : "default")
  );
  const [tenants, setTenants] = useState<{ id: string; label: string }[]>([]);
  const [newTenantId, setNewTenantId] = useState("");
  const [showCreateTenant, setShowCreateTenant] = useState(false);
  const [creatingTenant, setCreatingTenant] = useState(false);

  // ── Braket panel state ───────────────────────────────────────────────
  const [braketResult, setBraketResult] = useState<BraketSmokeTestResult | null>(null);
  const [braketRunning, setBraketRunning] = useState(false);

  // ── Load IBM status + tenant list on mount ───────────────────────────
  useEffect(() => {
    getIbmQuantumStatus()
      .then((d) => {
        const data = d?.data ?? d;
        setIbmConnected(data?.configured ?? false);
      })
      .catch(() => {});
    getIntegrationTenants()
      .then((d) => setTenants(d.tenants ?? []))
      .catch(() => {});
  }, []);

  // ── IBM handlers ─────────────────────────────────────────────────────
  const handleSaveIbmToken = useCallback(async () => {
    if (!ibmToken.trim()) {
      toast.error("Token is required");
      return;
    }
    setIbmStatus("saving");
    setIbmMessage("");
    try {
      await setIbmQuantumToken(ibmToken, { instance: ibmInstance || undefined });
      setIbmStatus("ok");
      setIbmConnected(true);
      setIbmMessage("Token saved and verified");
      setIbmToken("");
      toast.success("IBM Quantum token saved");
    } catch (err) {
      setIbmStatus("error");
      setIbmMessage(err instanceof Error ? err.message : "Save failed");
      toast.error("Failed to save IBM Quantum token");
    }
  }, [ibmToken, ibmInstance]);

  const handleVerifyIbmToken = useCallback(async () => {
    if (!ibmToken.trim()) {
      toast.error("Enter a token to test");
      return;
    }
    setIbmStatus("verifying");
    setIbmMessage("");
    try {
      const res = await verifyIbmQuantumToken(ibmToken, { instance: ibmInstance || undefined });
      const data = res?.data ?? res;
      setIbmStatus("ok");
      const backends = data?.backends?.length ?? 0;
      setIbmMessage(`Valid — ${backends} backend(s) available`);
      toast.success("IBM Quantum token verified");
    } catch (err) {
      setIbmStatus("error");
      setIbmMessage(err instanceof Error ? err.message : "Verification failed");
      toast.error("IBM Quantum verification failed");
    }
  }, [ibmToken, ibmInstance]);

  const handleClearIbmToken = useCallback(async () => {
    try {
      await clearIbmQuantumToken();
      setIbmConnected(false);
      setIbmStatus("idle");
      setIbmMessage("");
      toast.success("IBM Quantum token cleared");
    } catch {
      toast.error("Failed to clear token");
    }
  }, []);

  // ── Tenant handlers ──────────────────────────────────────────────────
  const handleSwitchTenant = useCallback((tid: string) => {
    setActiveIntegrationTenant(tid);
    setActiveTenantLocal(tid);
    toast.success(`Switched to tenant: ${tid}`);
  }, []);

  const handleCreateTenant = useCallback(async () => {
    if (!newTenantId.trim()) return;
    setCreatingTenant(true);
    try {
      await createTenant(newTenantId.trim());
      toast.success(`Tenant "${newTenantId.trim()}" created`);
      setNewTenantId("");
      setShowCreateTenant(false);
      getIntegrationTenants()
        .then((d) => setTenants(d.tenants ?? []))
        .catch(() => {});
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Create failed";
      if (msg.includes("403") || msg.includes("Forbidden")) {
        toast.error("Admin API key required to create tenants");
      } else {
        toast.error(msg);
      }
    } finally {
      setCreatingTenant(false);
    }
  }, [newTenantId]);

  // ── Braket handler ───────────────────────────────────────────────────
  const handleBraketSmokeTest = useCallback(async () => {
    setBraketRunning(true);
    setBraketResult(null);
    try {
      const res = await runBraketSmokeTest();
      setBraketResult(res);
      if (res.ok) {
        toast.success("Braket smoke test passed");
      } else {
        toast.error(res.error ?? "Braket smoke test failed");
      }
    } catch (err) {
      setBraketResult({ ok: false, error: err instanceof Error ? err.message : "Request failed" });
      toast.error("Braket smoke test request failed");
    } finally {
      setBraketRunning(false);
    }
  }, []);

  return (
    <div className="p-6 lg:p-10 space-y-8 max-w-3xl">
      <LedgerPageHeader
        title="Settings"
        subtitle="Platform configuration, integrations, and active session state"
        labLink={false}
      />

      {/* ── Active Session ────────────────────────────────────────────── */}
      <div className="bg-ql-surface-low rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-headline text-lg font-bold">Active Session</h3>
          <button
            type="button"
            onClick={copySessionJson}
            className="flex items-center gap-1.5 text-[10px] font-bold text-ql-primary uppercase hover:underline"
          >
            <span className="material-symbols-outlined text-sm">content_copy</span>
            Copy JSON
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: "Objective", value: session.objective, desc: "Default optimization method — set in Portfolio Lab" },
            {
              label: "Universe",
              value: `${session.tickers.length} tickers`,
              desc: "Asset list for returns & covariance — set via ticker input",
            },
            {
              label: "Weight Min",
              value: session.constraints.weightMin.toFixed(3),
              desc: "Min allocation per asset — positions below this are excluded",
            },
            {
              label: "Weight Max",
              value: session.constraints.weightMax.toFixed(3),
              desc: "Max allocation per asset — caps concentration risk",
            },
          ].map((item) => (
            <div
              key={item.label}
              className="relative bg-ql-surface-container/60 rounded-lg p-3 border border-ql-outline-variant group cursor-help"
              title={item.desc}
            >
              <p className="text-[10px] text-ql-on-surface-variant uppercase tracking-widest font-bold">
                {item.label}
              </p>
              <p className="text-sm font-mono font-bold mt-1">{item.value}</p>
              <p className="text-[9px] text-ql-on-surface-variant/60 mt-1 leading-snug">{item.desc}</p>
            </div>
          ))}
        </div>
        {session.lastOptimize && (
          <div className="rounded-lg bg-ql-tertiary/10 border border-ql-tertiary/20 px-4 py-3 text-xs font-mono text-ql-tertiary">
            Last optimization: {new Date(session.lastOptimize.at).toLocaleString()}
          </div>
        )}
      </div>

      {/* ── IBM Quantum Integration ───────────────────────────────────── */}
      <div className="bg-ql-surface-low rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-headline text-lg font-bold">IBM Quantum Integration</h3>
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${
              ibmConnected === true
                ? "bg-emerald-500/15 text-emerald-400"
                : ibmConnected === false
                  ? "bg-red-500/15 text-red-400"
                  : "bg-ql-outline-variant/20 text-ql-on-surface-variant"
            }`}
          >
            <span className="material-symbols-outlined text-sm">
              {ibmConnected === true ? "check_circle" : ibmConnected === false ? "cancel" : "pending"}
            </span>
            {ibmConnected === true ? "Connected" : ibmConnected === false ? "Not configured" : "Checking..."}
          </span>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-[10px] text-ql-on-surface-variant uppercase tracking-widest font-bold block mb-1">
              Token
            </label>
            <div className="flex gap-2">
              <input
                type="password"
                value={ibmToken}
                onChange={(e) => setIbmToken(e.target.value)}
                placeholder="Paste IBM Quantum API token"
                className="flex-1 bg-ql-surface-lowest border border-ql-outline-variant rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-ql-primary"
              />
              {ibmConnected && (
                <button
                  type="button"
                  onClick={handleClearIbmToken}
                  className="text-xs text-ql-error hover:underline px-2"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          <div>
            <label className="text-[10px] text-ql-on-surface-variant uppercase tracking-widest font-bold block mb-1">
              Instance CRN (optional)
            </label>
            <input
              type="text"
              value={ibmInstance}
              onChange={(e) => setIbmInstance(e.target.value)}
              placeholder="crn:v1:bluemix:public:quantum-computing:..."
              className="w-full bg-ql-surface-lowest border border-ql-outline-variant rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-ql-primary"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleSaveIbmToken}
              disabled={ibmStatus === "saving" || !ibmToken.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold bg-ql-primary text-ql-on-primary-fixed disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-sm">save</span>
              {ibmStatus === "saving" ? "Saving..." : "Save Token"}
            </button>
            <button
              type="button"
              onClick={handleVerifyIbmToken}
              disabled={ibmStatus === "verifying" || !ibmToken.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold border border-ql-outline-variant hover:bg-ql-surface-container/60 disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-sm">verified</span>
              {ibmStatus === "verifying" ? "Testing..." : "Test Connection"}
            </button>
          </div>

          {ibmMessage && (
            <div
              className={`rounded-lg px-4 py-2 text-xs font-mono ${
                ibmStatus === "ok"
                  ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                  : "bg-red-500/10 border border-red-500/20 text-red-400"
              }`}
            >
              {ibmMessage}
            </div>
          )}
        </div>
      </div>

      {/* ── Active Tenant ─────────────────────────────────────────────── */}
      <div className="bg-ql-surface-low rounded-xl p-6 space-y-4">
        <h3 className="font-headline text-lg font-bold">Active Tenant</h3>
        <p className="text-xs text-ql-on-surface-variant">
          Each tenant has its own IBM Quantum credentials and integration namespace.
          The <code className="text-ql-primary">X-Tenant-Id</code> header is sent automatically on every API call.
        </p>

        <div className="flex items-center gap-3">
          <label className="text-[10px] text-ql-on-surface-variant uppercase tracking-widest font-bold">
            Current
          </label>
          <select
            value={activeTenant}
            onChange={(e) => handleSwitchTenant(e.target.value)}
            className="bg-ql-surface-lowest border border-ql-outline-variant rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-ql-primary"
          >
            {tenants.length > 0 ? (
              tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label} ({t.id})
                </option>
              ))
            ) : (
              <option value={activeTenant}>{activeTenant}</option>
            )}
          </select>
        </div>

        <div>
          {!showCreateTenant ? (
            <button
              type="button"
              onClick={() => setShowCreateTenant(true)}
              className="text-xs font-bold text-ql-primary hover:underline inline-flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-sm">add</span>
              Create new tenant
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newTenantId}
                onChange={(e) => setNewTenantId(e.target.value)}
                placeholder="tenant-id (8-64 chars)"
                className="flex-1 bg-ql-surface-lowest border border-ql-outline-variant rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-ql-primary"
              />
              <button
                type="button"
                onClick={handleCreateTenant}
                disabled={creatingTenant || !newTenantId.trim()}
                className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-bold bg-ql-primary text-ql-on-primary-fixed disabled:opacity-50"
              >
                {creatingTenant ? "Creating..." : "Create"}
              </button>
              <button
                type="button"
                onClick={() => { setShowCreateTenant(false); setNewTenantId(""); }}
                className="text-xs text-ql-on-surface-variant hover:underline px-2"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Braket / AWS Integration ──────────────────────────────────── */}
      <div className="bg-ql-surface-low rounded-xl p-6 space-y-4">
        <h3 className="font-headline text-lg font-bold">AWS Braket / D-Wave Integration</h3>
        <p className="text-xs text-ql-on-surface-variant">
          Braket credentials are configured via environment variables (<code className="text-ql-primary">BRAKET_*</code>, <code className="text-ql-primary">AWS_*</code>).
          Use the smoke test to verify your configuration.
        </p>

        <button
          type="button"
          onClick={handleBraketSmokeTest}
          disabled={braketRunning}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-bold border border-ql-outline-variant hover:bg-ql-surface-container/60 disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-sm">science</span>
          {braketRunning ? "Running..." : "Run Smoke Test"}
        </button>

        {braketResult && (
          <div
            className={`rounded-lg px-4 py-3 text-xs font-mono space-y-1 ${
              braketResult.ok
                ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                : "bg-red-500/10 border border-red-500/20 text-red-400"
            }`}
          >
            <div className="font-bold">{braketResult.ok ? "Passed" : "Failed"}</div>
            {braketResult.backend && <div>Backend: {braketResult.backend}</div>}
            {braketResult.device && <div>Device: {braketResult.device}</div>}
            {braketResult.use_mock != null && <div>Mock mode: {braketResult.use_mock ? "Yes" : "No"}</div>}
            {braketResult.elapsed_ms != null && <div>Elapsed: {braketResult.elapsed_ms}ms</div>}
            {braketResult.n_assets != null && <div>Assets: {braketResult.n_assets}</div>}
            {braketResult.error && <div>Error: {braketResult.error}</div>}
          </div>
        )}
      </div>

      {/* ── Environment Variables ──────────────────────────────────────── */}
      <div className="bg-ql-surface-low rounded-xl p-6 space-y-4">
        <h3 className="font-headline text-lg font-bold">
          Environment Variables
        </h3>
        <p className="text-xs text-ql-on-surface-variant">
          Set these before starting the dev server. Client-side variables use the{" "}
          <code className="text-ql-primary">NEXT_PUBLIC_</code> prefix.
        </p>
        <div className="space-y-3">
          {ENV_VARS.map((v) => (
            <div
              key={v.name}
              className="bg-ql-surface-lowest rounded-lg p-4 border border-ql-outline-variant"
            >
              <div className="flex items-center gap-2 mb-1">
                <code className="text-sm font-mono font-bold text-ql-primary">
                  {v.name}
                </code>
                <span
                  className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                    v.required
                      ? "bg-ql-error/10 text-ql-error"
                      : "bg-ql-outline-variant/20 text-ql-on-surface-variant"
                  }`}
                >
                  {v.required ? "Required" : "Optional"}
                </span>
              </div>
              <p className="text-xs text-ql-on-surface-variant">{v.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── API docs link ─────────────────────────────────────────────── */}
      <div className="bg-ql-surface-low rounded-xl p-6">
        <h3 className="font-headline text-lg font-bold mb-2">
          API Reference
        </h3>
        <p className="text-xs text-ql-on-surface-variant mb-4">
          Interactive OpenAPI documentation for the Flask backend.
        </p>
        <a
          href="/api/docs/openapi"
          target="_blank"
          rel="noopener"
          className="inline-flex items-center gap-2 text-sm font-bold text-ql-primary hover:underline"
        >
          <span className="material-symbols-outlined text-lg">open_in_new</span>
          Open API Docs
        </a>
      </div>
    </div>
  );
}
