"use client";

import { useEffect, useMemo, useState } from "react";

import { getObjectives, getPresets } from "@/lib/api";
import {
  normalizeObjectives,
  normalizePresets,
  type ObjectiveInfo,
  type PresetInfo,
} from "@/lib/configApiNormalize";

/** Mirrors Strategy Builder + `/api/config/*` (embedded fallback if API fails). */
export type LabObjectiveOption = {
  value: string;
  label: string;
  group: "classical" | "hybrid" | "quantum";
  slow: boolean;
  badge?: string;
};

export type LabPresetOption = {
  key: string;
  name: string;
  description?: string;
  objective: string;
  minWeight: number;
  maxWeight: number;
  nAssets: number;
  regime: string;
};

const FALLBACK_OBJECTIVES: LabObjectiveOption[] = [
  { value: "equal_weight", label: "Equal Weight", group: "classical", slow: false },
  {
    value: "markowitz",
    label: "Markowitz",
    group: "classical",
    slow: false,
    badge: "1952",
  },
  { value: "min_variance", label: "Min Variance", group: "classical", slow: false },
  { value: "hrp", label: "HRP", group: "classical", slow: false, badge: "2016" },
  {
    value: "qubo_sa",
    label: "QUBO-SA",
    group: "quantum",
    slow: true,
    badge: "NB04",
  },
  { value: "vqe", label: "VQE", group: "quantum", slow: true, badge: "NB04" },
  {
    value: "hybrid",
    label: "Hybrid Pipeline",
    group: "hybrid",
    slow: true,
    badge: "NB05",
  },
];

const FALLBACK_PRESETS: LabPresetOption[] = [
  {
    key: "default",
    name: "Balanced · Hybrid",
    description:
      "3-stage hybrid (screen → QUBO select → allocate). Good default for exploration.",
    objective: "hybrid",
    minWeight: 0.005,
    maxWeight: 0.3,
    nAssets: 15,
    regime: "normal",
  },
  {
    key: "classical",
    name: "Classical · Max Sharpe",
    description: "Markowitz max-Sharpe (SLSQP).",
    objective: "markowitz",
    minWeight: 0.005,
    maxWeight: 0.3,
    nAssets: 15,
    regime: "normal",
  },
  {
    key: "sim_crash_day",
    name: "Stress · Crash day",
    description:
      "Single-day crash narrative: min-var, tight cap (see Simulations stress cards).",
    objective: "min_variance",
    minWeight: 0.02,
    maxWeight: 0.1,
    nAssets: 15,
    regime: "normal",
  },
  {
    key: "sim_gfc_drawdown",
    name: "Stress · Credit drawdown",
    description:
      "Prolonged selloff narrative: HRP (see Simulations: GFC, COVID).",
    objective: "hrp",
    minWeight: 0.005,
    maxWeight: 0.18,
    nAssets: 15,
    regime: "normal",
  },
  {
    key: "sim_relief_rally",
    name: "Stress · Relief rally",
    description:
      "Relief / momentum narrative: max-Sharpe, higher cap (see Simulations).",
    objective: "markowitz",
    minWeight: 0.005,
    maxWeight: 0.35,
    nAssets: 15,
    regime: "normal",
  },
];

function objectivesRecordToOptions(
  map: Record<string, ObjectiveInfo>
): LabObjectiveOption[] {
  return Object.entries(map).map(([id, o]) => ({
    value: id,
    label: o.label,
    group: o.family,
    slow: !o.fast,
  }));
}

function presetsRecordToOptions(
  map: Record<string, PresetInfo>
): LabPresetOption[] {
  return Object.entries(map).map(([key, p]) => ({
    key,
    name: p.label,
    description: p.description,
    objective: p.objective,
    minWeight: p.weight_min,
    maxWeight: p.weight_max,
    nAssets: 15,
    regime: "normal",
  }));
}

export function usePortfolioLabConfig(): {
  objectiveOptions: LabObjectiveOption[];
  presetOptions: LabPresetOption[];
  loading: boolean;
  loadError: string | null;
  usingFallback: boolean;
} {
  const [objectivesMap, setObjectivesMap] = useState<Record<
    string,
    ObjectiveInfo
  > | null>(null);
  const [presetsMap, setPresetsMap] = useState<Record<string, PresetInfo> | null>(
    null
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoadError(null);
    (async () => {
      try {
        const [objPayload, presetPayload] = await Promise.all([
          getObjectives(),
          getPresets(),
        ]);
        if (cancelled) return;
        const om = normalizeObjectives(objPayload);
        const pm = normalizePresets(presetPayload);
        setObjectivesMap(Object.keys(om).length ? om : null);
        setPresetsMap(Object.keys(pm).length ? pm : null);
      } catch (e) {
        if (!cancelled) {
          setLoadError(
            e instanceof Error ? e.message : "Failed to load optimization config"
          );
          setObjectivesMap(null);
          setPresetsMap(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const objectiveOptions = useMemo(() => {
    if (objectivesMap && Object.keys(objectivesMap).length > 0) {
      return objectivesRecordToOptions(objectivesMap);
    }
    return FALLBACK_OBJECTIVES;
  }, [objectivesMap]);

  const presetOptions = useMemo(() => {
    if (presetsMap && Object.keys(presetsMap).length > 0) {
      return presetsRecordToOptions(presetsMap);
    }
    return FALLBACK_PRESETS;
  }, [presetsMap]);

  const usingFallback =
    objectivesMap == null || Object.keys(objectivesMap).length === 0;

  return {
    objectiveOptions,
    presetOptions,
    loading,
    loadError,
    usingFallback,
  };
}
