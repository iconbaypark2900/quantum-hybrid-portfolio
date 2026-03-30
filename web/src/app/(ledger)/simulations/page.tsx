"use client";

import { useEffect } from "react";

import { useSimulationComparison } from "@/hooks/useSimulationComparison";
import LedgerPageHeader from "@/components/LedgerPageHeader";
import SessionBanner from "@/components/SessionBanner";
import {
  type StressScenario,
  STRESS_BEAR_SCENARIOS,
  STRESS_BULL_SCENARIOS,
} from "@/lib/stressScenarios";
import { useNextPageProps, type NextClientPageProps } from "@/lib/nextPageProps";

function heuristicImpact(shock: number, baseVol: number): number {
  return shock * (0.5 + baseVol * 3) * 100;
}

function StressCard({
  s,
  baseVol,
}: {
  s: StressScenario;
  baseVol: number;
}) {
  const impact = heuristicImpact(s.shock, baseVol);
  const isGain = s.shock >= 0;
  const pctLabel = `${impact.toFixed(1)}%`;
  const barPct = Math.min(Math.abs(impact), 60);

  return (
    <div className="bg-ql-surface-container rounded-lg p-5 border border-ql-outline-variant/5">
      <p className="text-sm font-bold">{s.name}</p>
      <p className="text-[10px] text-ql-on-surface-variant mt-1 mb-4">
        {s.desc}
      </p>
      <p
        className={`text-3xl font-headline font-bold ${
          isGain ? "text-ql-tertiary" : "text-ql-error"
        }`}
      >
        {pctLabel}
      </p>
      <p className="text-[10px] text-ql-on-surface-variant mt-1">
        {isGain ? "Est. gain (heuristic)" : "Est. loss (heuristic)"}
      </p>
      <div className="mt-3 h-1 bg-ql-outline-variant/20 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${
            isGain ? "bg-ql-tertiary" : "bg-ql-error"
          }`}
          style={{ width: `${barPct}%` }}
        />
      </div>
    </div>
  );
}

export default function SimulationsPage(props: NextClientPageProps) {
  useNextPageProps(props);
  const { scenarios, error, runComparison } = useSimulationComparison();

  useEffect(() => {
    void runComparison();
  }, [runComparison]);

  const bestSharpe = Math.max(...scenarios.map((s) => s.sharpe), 0.001);
  const baseVol = scenarios.length ? scenarios[0].vol / 100 : 0.15;

  return (
    <div className="p-6 lg:p-10 space-y-8">
      <LedgerPageHeader
        title="Simulations"
        subtitle="Compare strategies side-by-side and stress-test under macro scenarios"
      />

      <SessionBanner />

      {error && (
        <div
          className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200"
          role="status"
        >
          {error}
        </div>
      )}

      {/* Strategy comparison table */}
      {scenarios.length > 0 && (
        <div className="bg-ql-surface-low rounded-xl p-6 overflow-x-auto">
          <h3 className="font-headline text-lg font-bold mb-4">
            Strategy Comparison
          </h3>
          <table className="w-full text-sm font-mono">
            <thead>
              <tr>
                {["Strategy", "Sharpe", "Return", "Volatility", "Positions"].map(
                  (h) => (
                    <th
                      key={h}
                      className={`pb-3 text-[10px] uppercase tracking-widest text-ql-on-surface-variant font-bold ${
                        h === "Strategy" ? "text-left" : "text-right"
                      }`}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {scenarios
                .sort((a, b) => b.sharpe - a.sharpe)
                .map((s) => {
                  const isBest = s.sharpe >= bestSharpe - 0.001;
                  return (
                    <tr
                      key={s.objective}
                      className="hover:bg-ql-surface-container/40 transition-colors"
                    >
                      <td className="py-3 font-bold">
                        {s.name}
                        {isBest && (
                          <span className="ml-2 text-[9px] bg-ql-tertiary/10 text-ql-tertiary px-1.5 py-0.5 rounded font-bold">
                            BEST
                          </span>
                        )}
                      </td>
                      <td
                        className={`py-3 text-right ${
                          isBest ? "text-ql-tertiary" : ""
                        }`}
                      >
                        {s.sharpe.toFixed(3)}
                      </td>
                      <td className="py-3 text-right">{s.ret.toFixed(1)}%</td>
                      <td className="py-3 text-right">{s.vol.toFixed(1)}%</td>
                      <td className="py-3 text-right">{s.nActive}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-ql-surface-low rounded-xl p-6 space-y-8">
        <div>
          <h3 className="font-headline text-lg font-bold mb-1">
            Stress Scenarios
          </h3>
          <p className="text-ql-on-surface-variant text-xs">
            Illustrative heuristic based on historical shocks and current
            volatility — not a live backtest
          </p>
        </div>

        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">
            Down days / crises
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {STRESS_BEAR_SCENARIOS.map((s) => (
              <StressCard key={s.name} s={s} baseVol={baseVol} />
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">
            Relief / rally days
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {STRESS_BULL_SCENARIOS.map((s) => (
              <StressCard key={s.name} s={s} baseVol={baseVol} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
