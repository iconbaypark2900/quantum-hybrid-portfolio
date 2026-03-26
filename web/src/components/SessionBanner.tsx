"use client";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import { DEFAULT_TICKERS } from "@/lib/defaultUniverse";

function objectiveLabel(obj: string): string {
  return obj.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function SessionBanner() {
  const { session } = useLedgerSession();
  const isDefault =
    session.tickers.length === DEFAULT_TICKERS.length &&
    [...session.tickers].sort().join(",") ===
      [...DEFAULT_TICKERS].sort().join(",");

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg bg-ql-surface-container/60 border border-ql-outline-variant/10 px-4 py-2.5 text-xs">
      <span className="text-slate-500 uppercase tracking-widest font-bold text-[9px]">
        Session
      </span>
      <span className="font-mono font-bold text-ql-on-surface">
        {objectiveLabel(session.objective)}
      </span>
      <span className="text-slate-500">|</span>
      <span className="text-ql-on-surface-variant">
        {session.tickers.length} tickers{isDefault ? " (default)" : ""}
      </span>
      <span className="text-slate-500">|</span>
      <span className="text-ql-on-surface-variant">
        wt {session.constraints.weightMin.toFixed(3)}–
        {session.constraints.weightMax.toFixed(2)}
      </span>
      {session.lastOptimize && (
        <>
          <span className="text-slate-500">|</span>
          <span className="flex items-center gap-1 text-ql-tertiary font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-ql-tertiary" />
            Last run{" "}
            {new Date(session.lastOptimize.at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </>
      )}
    </div>
  );
}
