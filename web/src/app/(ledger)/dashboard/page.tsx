"use client";

import Link from "next/link";
import React, { useEffect, useState, useCallback } from "react";
import { useLedgerSession } from "@/context/LedgerSessionContext";
import LedgerPageHeader from "@/components/LedgerPageHeader";
import { healthCheck, optimizePortfolio } from "@/lib/api";
import { DEFAULT_TICKERS, DEFAULT_WEIGHT_MAX, DEFAULT_WEIGHT_MIN } from "@/lib/defaultUniverse";
import { mergeOptimizeResponse } from "@/lib/reportExport";
import { useNextPageProps, type NextClientPageProps } from "@/lib/nextPageProps";

const QUICK_ACTION_GROUPS: {
  heading: string;
  items: { href: string; label: string; icon: string }[];
}[] = [
  {
    heading: "Optimize & Lab",
    items: [
      { href: "/portfolio", label: "Portfolio Lab — Run Optimization", icon: "science" },
      {
        href: "/strategy",
        label: "Strategy Builder — Open in Lab & manifest",
        icon: "architecture",
      },
    ],
  },
  {
    heading: "Engine & analysis",
    items: [
      {
        href: "/quantum",
        label: "Quantum Engine — Connect IBM & queue jobs",
        icon: "memory",
      },
      {
        href: "/simulations",
        label: "Simulations — Run scenario comparison",
        icon: "query_stats",
      },
      {
        href: "/reports",
        label: "Reports — Generate & export",
        icon: "description",
      },
    ],
  },
  {
    heading: "Settings",
    items: [
      {
        href: "/settings",
        label: "Settings — Session & configuration",
        icon: "settings",
      },
    ],
  },
];

const PLATFORM_TOOLS: {
  href: string;
  icon: string;
  title: string;
  purpose: string;
  when: string;
  primaryLabel: string;
}[] = [
  {
    href: "/portfolio",
    icon: "science",
    title: "Portfolio Lab",
    purpose:
      "Full interactive dashboard: universe, benchmarks, VaR, equity paths, and backend Run Optimization.",
    when: "Use for deep dives, comparing classical vs quantum objectives, and live or mock data.",
    primaryLabel: "Run Optimization (full Lab)",
  },
  {
    href: "/strategy",
    icon: "architecture",
    title: "Strategy Builder",
    purpose:
      "Pick objectives from the API catalog, tune weight bounds and K_screen / K_select, export YAML.",
    when: "Use before Lab when you want a named preset and a shareable Portfolio Lab deep link.",
    primaryLabel: "Open Strategy Builder",
  },
  {
    href: "/quantum",
    icon: "memory",
    title: "Quantum Engine",
    purpose:
      "IBM Quantum token, simulator vs hardware mode, telemetry, and async optimize/backtest jobs.",
    when: "Use when wiring hardware or monitoring queue status outside the Lab.",
    primaryLabel: "Connect / queue jobs",
  },
  {
    href: "/simulations",
    icon: "query_stats",
    title: "Simulations",
    purpose:
      "Side-by-side scenario comparison across objectives and macro stress cards (heuristic).",
    when: "Use to compare strategies and stress-test under narrative scenarios.",
    primaryLabel: "Run scenario comparison",
  },
  {
    href: "/reports",
    icon: "description",
    title: "Reports",
    purpose:
      "Generate JSON or CSV exports with performance, risk, compliance slices, and print-friendly summary.",
    when: "Use for audit trails, spreadsheets, or sharing a frozen snapshot.",
    primaryLabel: "Generate & download",
  },
  {
    href: "/settings",
    icon: "settings",
    title: "Settings",
    purpose: "View last optimization time, session tickers, and constraint snapshot.",
    when: "Use to confirm what the rest of the app will use by default.",
    primaryLabel: "View session & config",
  },
];

interface HealthData {
  status: string;
  dependencies?: Record<string, unknown>;
}

interface OptResult {
  weights?: number[];
  sharpe_ratio?: number;
  expected_return?: number;
  volatility?: number;
  n_active?: number;
  holdings?: Array<{ name: string; sector: string; weight: number }>;
  sector_allocation?: Array<{ sector: string; weight: number }>;
  risk_metrics?: { var_95?: number; cvar?: number };
  qsw_result?: Record<string, unknown>;
}

interface FeedEvent {
  id: string;
  type: "optimization" | "system" | "alert";
  title: string;
  detail: string;
  time: string;
  icon: string;
  iconColor: string;
}

export default function DashboardPage(props: NextClientPageProps) {
  useNextPageProps(props);
  const { session, setLastOptimize } = useLedgerSession();

  const [health, setHealth] = useState<HealthData | null>(null);
  const [result, setResult] = useState<OptResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [feed, setFeed] = useState<FeedEvent[]>([
    {
      id: "boot",
      type: "system",
      title: "System Online",
      detail: "Quantum Ledger initialized. API connection established.",
      time: "just now",
      icon: "task_alt",
      iconColor: "text-ql-tertiary",
    },
  ]);

  useEffect(() => {
    healthCheck()
      .then((d) => setHealth(d))
      .catch(() => setHealth({ status: "unreachable" }));
  }, []);

  const addFeedEvent = useCallback(
    (ev: Omit<FeedEvent, "id" | "time">) => {
      setFeed((prev) => [
        {
          ...ev,
          id: crypto.randomUUID(),
          time: "just now",
        },
        ...prev.slice(0, 19),
      ]);
    },
    []
  );

  const runQuickOptimize = useCallback(async () => {
    setLoading(true);
    addFeedEvent({
      type: "optimization",
      title: "Optimization Started",
      detail: "Running hybrid pipeline optimization...",
      icon: "auto_awesome",
      iconColor: "text-ql-primary",
    });
    try {
      const tickers = session.tickers.length > 0 ? session.tickers : [...DEFAULT_TICKERS];
      const resp = (await optimizePortfolio({
        tickers,
        objective: session.objective || "hybrid",
        weight_min: session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN,
        maxWeight: session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX,
      })) as Record<string, unknown>;
      const data = mergeOptimizeResponse(resp) as unknown as OptResult;
      setResult(data);
      setLastOptimize(
        {
          at: new Date().toISOString(),
          tickers,
          objective: session.objective || "hybrid",
          constraints: {
            weightMin: session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN,
            weightMax: session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX,
          },
          payload: resp,
        },
        { source: "executive_dashboard" }
      );
      addFeedEvent({
        type: "optimization",
        title: "Optimization Complete",
        detail: `Sharpe: ${(data.sharpe_ratio ?? 0).toFixed(3)} | Active: ${data.n_active ?? "?"} positions`,
        icon: "task_alt",
        iconColor: "text-ql-tertiary",
      });
    } catch (err) {
      addFeedEvent({
        type: "alert",
        title: "Optimization Failed",
        detail: err instanceof Error ? err.message : "Unknown error",
        icon: "error",
        iconColor: "text-ql-error",
      });
    } finally {
      setLoading(false);
    }
  }, [addFeedEvent, session, setLastOptimize]);

  const lastOptRef = React.useRef<string | null>(null);
  useEffect(() => {
    if (!session.lastOptimize) return;
    if (lastOptRef.current === session.lastOptimize.at) return;
    lastOptRef.current = session.lastOptimize.at;
    const snap = session.lastOptimize;
    const snapSharpe = Number(
      (snap.payload as Record<string, unknown>).sharpe_ratio ?? 0
    );
    addFeedEvent({
      type: "optimization",
      title: "Lab Run Available",
      detail: `Sharpe ${snapSharpe.toFixed(3)} | ${snap.tickers.length} tickers | ${snap.objective}`,
      icon: "science",
      iconColor: "text-ql-tertiary",
    });
  }, [session.lastOptimize, addFeedEvent]);

  const sharpe = result?.sharpe_ratio ?? 0;
  const ret = (result?.expected_return ?? 0) * 100;
  const vol = (result?.volatility ?? 0) * 100;
  const nActive = result?.n_active ?? 0;
  const var95 = (result?.risk_metrics?.var_95 ?? 0) * 100;

  return (
    <div className="p-6 lg:p-10 space-y-10">
      <section className="border-b border-ql-outline-variant/10 pb-8 space-y-6 min-w-0">
        <LedgerPageHeader
          title="Executive Dashboard"
          subtitle="Quantum Ledger — session-aware optimize, live KPIs, holdings, and workspace shortcuts."
          primaryAction={
            <button
              type="button"
              onClick={runQuickOptimize}
              disabled={loading}
              className="primary-gradient text-ql-on-primary-fixed inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-sm font-bold shadow-lg shadow-ql-primary/20 disabled:opacity-50 w-full sm:w-auto shrink-0"
            >
              <span className="material-symbols-outlined text-lg">bolt</span>
              {loading ? "Running..." : "Run Optimization"}
            </button>
          }
        />
        <div
          className="flex flex-wrap items-center gap-3 rounded-xl bg-ql-surface-low border border-ql-outline-variant/10 px-4 py-3"
          role="status"
        >
          <span
            className={`flex items-center gap-2 text-sm font-bold ${
              health?.status === "healthy"
                ? "text-ql-tertiary"
                : "text-ql-on-surface-variant"
            }`}
          >
            <span className="material-symbols-outlined text-lg">
              {health?.status === "healthy" ? "check_circle" : "pending"}
            </span>
            {health
              ? health.status === "healthy"
                ? "API connected"
                : `API: ${health.status}`
              : "Connecting to API…"}
          </span>
          <span className="text-ql-on-surface-variant text-xs hidden sm:inline">
            Session objective:{" "}
            <span className="font-mono text-ql-on-surface">
              {session.objective || "hybrid"}
            </span>
            {" · "}
            {session.tickers.length || DEFAULT_TICKERS.length} tickers
          </span>
        </div>
      </section>

      {/* KPI Grid — above the fold */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Sharpe Ratio", value: sharpe.toFixed(3), color: sharpe > 1 ? "text-ql-tertiary" : "" },
          { label: "Expected Return", value: `${ret.toFixed(1)}%`, color: "text-ql-primary" },
          { label: "Volatility", value: `${vol.toFixed(1)}%`, color: "" },
          { label: "Active Positions", value: String(nActive), color: "text-ql-secondary" },
          { label: "VaR (95%)", value: `${var95.toFixed(2)}%`, color: "text-ql-error" },
        ].map((m) => (
          <div
            key={m.label}
            className="bg-ql-surface-low rounded-xl p-5 border border-ql-outline-variant/5"
          >
            <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
              {m.label}
            </p>
            <p className={`text-2xl font-headline font-bold mt-1 ${m.color}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>

      {/* Bento grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Holdings */}
        <div className="md:col-span-7 bg-ql-surface-low rounded-xl p-6">
          <h3 className="font-headline text-xl font-bold mb-1">Holdings</h3>
          <p className="text-slate-500 text-xs mb-6">
            {result?.holdings?.length ?? 0} active positions
          </p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {result?.holdings?.length ? (
              result.holdings
                .sort((a, b) => b.weight - a.weight)
                .map((h, i) => (
                  <div
                    key={h.name}
                    className="flex items-center gap-3 py-2 hover:bg-ql-surface-container/40 px-2 rounded transition-colors"
                  >
                    <span className="text-[10px] text-slate-500 font-mono w-5 text-right">
                      {i + 1}
                    </span>
                    <div className="flex-1">
                      <span className="text-sm font-bold">{h.name}</span>
                      <span className="text-[10px] text-slate-500 ml-2">
                        {h.sector}
                      </span>
                    </div>
                    <div className="w-16">
                      <div className="h-1 bg-ql-outline-variant/20 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-ql-primary rounded-full"
                          style={{ width: `${Math.min(h.weight * 500, 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold text-ql-primary w-12 text-right">
                      {(h.weight * 100).toFixed(1)}%
                    </span>
                  </div>
                ))
            ) : (
              <p className="text-slate-500 text-sm text-center py-10">
                Run an optimization to see holdings
              </p>
            )}
          </div>
        </div>

        {/* Optimization Feed */}
        <div className="md:col-span-5 bg-ql-surface-container rounded-xl p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-headline text-lg font-bold">
              Optimization Feed
            </h3>
            <span className="flex items-center gap-1 text-[10px] text-ql-tertiary font-bold uppercase tracking-widest animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-ql-tertiary" />
              Live
            </span>
          </div>
          <div className="space-y-5 max-h-80 overflow-y-auto">
            {feed.map((ev) => (
              <div key={ev.id} className="flex gap-3">
                <div className="mt-0.5 w-8 h-8 rounded-lg bg-ql-surface-high flex items-center justify-center shrink-0">
                  <span
                    className={`material-symbols-outlined text-lg ${ev.iconColor}`}
                  >
                    {ev.icon}
                  </span>
                </div>
                <div className="min-w-0">
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-sm font-bold truncate">{ev.title}</p>
                    <span className="text-[10px] text-slate-500 shrink-0">
                      {ev.time}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{ev.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sector Allocation */}
        <div className="md:col-span-4 bg-ql-surface-low rounded-xl p-6">
          <h3 className="font-headline text-xl font-bold mb-1">
            Sector Allocation
          </h3>
          <p className="text-slate-500 text-xs mb-6">Current distribution</p>
          <div className="space-y-3">
            {result?.sector_allocation?.length ? (
              result.sector_allocation
                .sort((a, b) => b.weight - a.weight)
                .map((s, i) => {
                  const colors = ["bg-ql-primary", "bg-ql-tertiary", "bg-slate-500", "bg-ql-secondary", "bg-ql-error"];
                  return (
                    <div key={s.sector} className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${colors[i % colors.length]}`} />
                      <span className="text-xs flex-1">{s.sector}</span>
                      <span className="text-xs font-bold font-mono">
                        {(s.weight * 100).toFixed(1)}%
                      </span>
                    </div>
                  );
                })
            ) : (
              <p className="text-slate-500 text-sm text-center py-8">
                No allocation data
              </p>
            )}
          </div>
        </div>

        {/* Quick stats */}
        <div className="md:col-span-8 bg-ql-surface-low rounded-xl p-6">
          <h3 className="font-headline text-xl font-bold mb-1">
            System Status
          </h3>
          <p className="text-slate-500 text-xs mb-6">Platform health</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: "API",
                value: health?.status === "healthy" ? "Online" : "Offline",
                color:
                  health?.status === "healthy"
                    ? "text-[#00E475]"
                    : "text-ql-error",
              },
              { label: "Optimizer", value: "Ready", color: "text-[#00E475]" },
              { label: "Market Data", value: "Connected", color: "text-[#00E475]" },
              { label: "Quantum Engine", value: "Simulator", color: "text-ql-primary" },
            ].map((s) => (
              <div key={s.label} className="bg-ql-surface-container/60 backdrop-blur p-4 rounded-lg border border-ql-outline-variant/10">
                <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
                  {s.label}
                </p>
                <p className={`text-lg font-headline font-bold ${s.color}`}>
                  {s.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <section className="space-y-6 border-t border-ql-outline-variant/10 pt-10">
        <div>
          <h3 className="font-headline text-lg font-bold text-ql-on-surface">
            Quick actions
          </h3>
          <p className="text-sm text-ql-on-surface-variant mt-1 max-w-3xl">
            Jump to any workspace — each link opens the same primary workflow as that
            page&apos;s main control.
          </p>
        </div>
        <div className="space-y-6">
          {QUICK_ACTION_GROUPS.map((group) => (
            <div key={group.heading}>
              <p className="text-[10px] font-bold uppercase tracking-widest text-ql-on-surface-variant mb-3">
                {group.heading}
              </p>
              <div className="flex flex-wrap gap-3">
                {group.items.map((item) => (
                  <Link
                    key={item.href + item.label}
                    href={item.href}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold border border-ql-outline-variant/20 bg-ql-surface-low text-ql-on-surface hover:bg-ql-surface-container hover:border-ql-primary/30 transition-colors no-underline"
                  >
                    <span className="material-symbols-outlined text-lg text-ql-primary">
                      {item.icon}
                    </span>
                    <span className="text-left leading-snug">{item.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="font-headline text-lg font-bold text-ql-on-surface">
            Platform tools
          </h3>
          <p className="text-sm text-ql-on-surface-variant mt-1 max-w-3xl">
            What each area does, when to use it, and the primary action to run there.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {PLATFORM_TOOLS.map((tool) => (
            <div
              key={tool.title}
              className="bg-ql-surface-low rounded-xl p-5 border border-ql-outline-variant/10 flex flex-col"
            >
              <div className="flex items-start gap-3 mb-3">
                <span className="material-symbols-outlined text-2xl text-ql-primary shrink-0">
                  {tool.icon}
                </span>
                <div>
                  <h4 className="font-headline font-bold text-ql-on-surface">
                    {tool.title}
                  </h4>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-ql-on-surface-variant mt-1">
                    Primary: {tool.primaryLabel}
                  </p>
                </div>
              </div>
              <p className="text-xs text-ql-on-surface leading-relaxed flex-1">
                {tool.purpose}
              </p>
              <p className="text-[11px] text-ql-on-surface-variant mt-3 pt-3 border-t border-ql-outline-variant/10">
                <span className="font-bold text-ql-secondary">When: </span>
                {tool.when}
              </p>
              <Link
                href={tool.href}
                className="mt-4 inline-flex items-center justify-center gap-2 w-full py-2.5 rounded-lg text-xs font-bold primary-gradient text-ql-on-primary-fixed shadow-md shadow-ql-primary/15 hover:opacity-95 transition-opacity no-underline"
              >
                {tool.primaryLabel}
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
