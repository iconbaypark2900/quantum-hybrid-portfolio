"use client";

import { useCallback, useMemo, useState } from "react";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import { optimizePortfolio } from "@/lib/api";
import { DEFAULT_TICKERS, DEFAULT_WEIGHT_MAX, DEFAULT_WEIGHT_MIN } from "@/lib/defaultUniverse";
import {
  buildAnalystRunBundle,
  buildReportPayload,
  downloadAnalystBundle,
  downloadAnalystCsvFromBundle,
  downloadFile,
  mergeOptimizeResponse,
  reportToCsv,
  type AnalystRunBundleV3,
  type ReportProvenance,
  type ReportType,
  type ReportContext,
} from "@/lib/reportExport";

export type ExportFormat = "json" | "csv" | "bundle";

function buildAndDownload(
  selectedType: ReportType,
  format: ExportFormat,
  data: Record<string, unknown>,
  tickers: string[],
  reportCtx: ReportContext,
  provenance: ReportProvenance,
  rawPayload?: unknown,
): { report: Record<string, unknown>; bundle: AnalystRunBundleV3 | null } {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const runId = `session-${ts}`;

  const bundle = buildAnalystRunBundle(data, {
    runId,
    runKind: "session",
    tickers,
    provenance,
    rawPayload,
  });

  if (format === "bundle") {
    downloadAnalystBundle(bundle, "analyst_session");
    return { report: data, bundle };
  }

  const report = buildReportPayload(selectedType, data, tickers, reportCtx, provenance);

  if (format === "json") {
    downloadFile(
      JSON.stringify(report, null, 2),
      `quantum_ledger_${selectedType}_${ts}.json`,
      "application/json"
    );
  } else {
    downloadFile(
      reportToCsv(report as Record<string, unknown>),
      `quantum_ledger_${selectedType}_${ts}.csv`,
      "text/csv"
    );
  }
  return { report: report as Record<string, unknown>, bundle };
}

export function useReportGeneration() {
  const { session } = useLedgerSession();
  const [selectedType, setSelectedType] = useState<ReportType>("full");
  const [format, setFormat] = useState<ExportFormat>("json");
  const [generating, setGenerating] = useState(false);
  const [lastReport, setLastReport] = useState<Record<string, unknown> | null>(null);
  const [lastBundle, setLastBundle] = useState<AnalystRunBundleV3 | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasSnapshot = session.lastOptimize !== null;
  const snapshotAt = session.lastOptimize?.at ?? null;

  const reportCtx = useMemo<ReportContext>(
    () => ({
      objective: session.lastOptimize?.objective ?? session.objective,
      weightMin: session.constraints.weightMin,
      weightMax: session.constraints.weightMax,
    }),
    [session.lastOptimize?.objective, session.objective, session.constraints.weightMin, session.constraints.weightMax]
  );

  const generateReport = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      let data: Record<string, unknown>;
      let tickers: string[];
      let provenance: ReportProvenance;
      let rawPayload: unknown;

      if (session.lastOptimize) {
        rawPayload = session.lastOptimize.payload;
        data = mergeOptimizeResponse(rawPayload) as Record<string, unknown>;
        tickers = session.lastOptimize.tickers;
        provenance = {
          source: "snapshot",
          snapshot_at: session.lastOptimize.at,
        };
      } else {
        const useTickers =
          session.tickers.length > 0 ? session.tickers : [...DEFAULT_TICKERS];
        rawPayload = await optimizePortfolio({
          tickers: useTickers,
          objective: session.objective || "hybrid",
          weight_min: session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN,
          maxWeight: session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX,
        }) as Record<string, unknown>;
        data = mergeOptimizeResponse(rawPayload);
        tickers = useTickers;
        provenance = { source: "fresh", snapshot_at: null };
      }

      const { report, bundle } = buildAndDownload(
        selectedType,
        format,
        data,
        tickers,
        reportCtx,
        provenance,
        rawPayload,
      );
      setLastReport(report);
      setLastBundle(bundle);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Report generation failed";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  }, [selectedType, format, session, reportCtx]);

  const generateReportFresh = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const useTickers =
        session.tickers.length > 0 ? session.tickers : [...DEFAULT_TICKERS];
      const rawPayload = (await optimizePortfolio({
        tickers: useTickers,
        objective: session.objective || "hybrid",
        weight_min: session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN,
        maxWeight: session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX,
      })) as Record<string, unknown>;
      const data = mergeOptimizeResponse(rawPayload);
      const provenance: ReportProvenance = {
        source: "fresh",
        snapshot_at: null,
      };

      const { report, bundle } = buildAndDownload(
        selectedType,
        format,
        data,
        useTickers,
        reportCtx,
        provenance,
        rawPayload,
      );
      setLastReport(report);
      setLastBundle(bundle);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Report generation failed";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  }, [selectedType, format, session, reportCtx]);

  /** Download CSV from the last generated bundle (same merged data as JSON/bundle). */
  const downloadBundleCsv = useCallback(() => {
    if (!lastBundle) return;
    downloadAnalystCsvFromBundle(lastBundle, reportCtx, "analyst_session");
  }, [lastBundle, reportCtx]);

  return {
    selectedType,
    setSelectedType,
    format,
    setFormat,
    generating,
    lastReport,
    lastBundle,
    error,
    hasSnapshot,
    snapshotAt,
    generateReport,
    generateReportFresh,
    downloadBundleCsv,
  };
}
