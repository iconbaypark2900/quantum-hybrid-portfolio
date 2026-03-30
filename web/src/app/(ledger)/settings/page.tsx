"use client";

import { useCallback } from "react";
import { toast } from "sonner";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import LedgerPageHeader from "@/components/LedgerPageHeader";
import { useNextPageProps, type NextClientPageProps } from "@/lib/nextPageProps";

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

  return (
    <div className="p-6 lg:p-10 space-y-8 max-w-3xl">
      <LedgerPageHeader
        title="Settings"
        subtitle="Platform configuration and active session state"
        labLink={false}
      />

      {/* Active session */}
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
            { label: "Objective", value: session.objective },
            {
              label: "Universe",
              value: `${session.tickers.length} tickers`,
            },
            {
              label: "Weight Min",
              value: session.constraints.weightMin.toFixed(3),
            },
            {
              label: "Weight Max",
              value: session.constraints.weightMax.toFixed(3),
            },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-ql-surface-container/60 rounded-lg p-3 border border-ql-outline-variant/10"
            >
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                {item.label}
              </p>
              <p className="text-sm font-mono font-bold mt-1">{item.value}</p>
            </div>
          ))}
        </div>
        {session.lastOptimize && (
          <div className="rounded-lg bg-ql-tertiary/10 border border-ql-tertiary/20 px-4 py-3 text-xs font-mono text-ql-tertiary">
            Last optimization: {new Date(session.lastOptimize.at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Environment variables */}
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
              className="bg-ql-surface-lowest rounded-lg p-4 border border-ql-outline-variant/10"
            >
              <div className="flex items-center gap-2 mb-1">
                <code className="text-sm font-mono font-bold text-ql-primary">
                  {v.name}
                </code>
                <span
                  className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                    v.required
                      ? "bg-ql-error/10 text-ql-error"
                      : "bg-slate-500/10 text-slate-400"
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

      {/* API docs link */}
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
