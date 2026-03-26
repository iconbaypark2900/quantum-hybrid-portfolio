"use client";

import { useCallback, useState } from "react";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import { optimizePortfolio } from "@/lib/api";
import { DEFAULT_TICKERS, DEFAULT_WEIGHT_MAX, DEFAULT_WEIGHT_MIN } from "@/lib/defaultUniverse";

export interface ScenarioResult {
  name: string;
  objective: string;
  sharpe: number;
  ret: number;
  vol: number;
  nActive: number;
}

const OBJECTIVES = [
  "hybrid",
  "markowitz",
  "hrp",
  "qubo_sa",
  "min_variance",
  "equal_weight",
] as const;

function objectiveLabel(obj: string): string {
  return obj
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function mapOptimizeRow(obj: string, resp: Record<string, unknown>): ScenarioResult {
  const inner = (resp.qsw_result as Record<string, unknown> | undefined) || resp;
  const sharpe = Number(inner.sharpe_ratio ?? 0);
  const ret = Number(inner.expected_return ?? 0) * 100;
  const vol = Number(inner.volatility ?? 0) * 100;
  const nActive = Number(inner.n_active ?? 0);
  return {
    name: objectiveLabel(obj),
    objective: obj,
    sharpe,
    ret,
    vol,
    nActive,
  };
}

export function useSimulationComparison() {
  const { session } = useLedgerSession();
  const [scenarios, setScenarios] = useState<ScenarioResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runComparison = useCallback(async () => {
    setRunning(true);
    setError(null);
    const results: ScenarioResult[] = [];
    let failures = 0;

    const tickers =
      session.tickers.length > 0 ? session.tickers : [...DEFAULT_TICKERS];
    const wMin = session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN;
    const wMax = session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX;

    for (const obj of OBJECTIVES) {
      try {
        const resp = (await optimizePortfolio({
          tickers,
          objective: obj,
          weight_min: wMin,
          maxWeight: wMax,
        })) as Record<string, unknown>;
        results.push(mapOptimizeRow(obj, resp));
      } catch {
        failures += 1;
        results.push({
          name: objectiveLabel(obj),
          objective: obj,
          sharpe: 0,
          ret: 0,
          vol: 0,
          nActive: 0,
        });
      }
    }

    setScenarios(results);
    if (failures === OBJECTIVES.length) {
      setError(
        "All optimization calls failed. Is the API running and reachable?"
      );
    } else if (failures > 0) {
      setError(
        `${failures} of ${OBJECTIVES.length} objectives failed (see zeros in table).`
      );
    }
    setRunning(false);
  }, [session]);

  return {
    scenarios,
    running,
    error,
    runComparison,
  };
}
