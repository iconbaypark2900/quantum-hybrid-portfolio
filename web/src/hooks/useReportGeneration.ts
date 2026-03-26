"use client";

import { useCallback, useMemo, useState } from "react";

import { useLedgerSession } from "@/context/LedgerSessionContext";
import { optimizePortfolio } from "@/lib/api";
import { DEFAULT_TICKERS, DEFAULT_WEIGHT_MAX, DEFAULT_WEIGHT_MIN } from "@/lib/defaultUniverse";
import {
  buildReportPayload,
  downloadFile,
  mergeOptimizeResponse,
  reportToCsv,
  type ReportProvenance,
  type ReportType,
  type ReportContext,
} from "@/lib/reportExport";

export type ExportFormat = "json" | "csv";

function buildAndDownload(
  selectedType: ReportType,
  format: ExportFormat,
  data: Record<string, unknown>,
  tickers: string[],
  reportCtx: ReportContext,
  provenance: ReportProvenance,
): Record<string, unknown> {
  const report = buildReportPayload(
    selectedType,
    data,
    tickers,
    reportCtx,
    provenance
  );
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
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
  return report;
}

export function useReportGeneration() {
  const { session } = useLedgerSession();
  const [selectedType, setSelectedType] = useState<ReportType>("full");
  const [format, setFormat] = useState<ExportFormat>("json");
  const [generating, setGenerating] = useState(false);
  const [lastReport, setLastReport] = useState<Record<string, unknown> | null>(
    null
  );
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

      if (session.lastOptimize) {
        data = session.lastOptimize.payload;
        tickers = session.lastOptimize.tickers;
        provenance = {
          source: "snapshot",
          snapshot_at: session.lastOptimize.at,
        };
      } else {
        const useTickers =
          session.tickers.length > 0 ? session.tickers : [...DEFAULT_TICKERS];
        const resp = (await optimizePortfolio({
          tickers: useTickers,
          objective: session.objective || "hybrid",
          weight_min: session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN,
          maxWeight: session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX,
        })) as Record<string, unknown>;
        data = mergeOptimizeResponse(resp);
        tickers = useTickers;
        provenance = { source: "fresh", snapshot_at: null };
      }

      const report = buildAndDownload(
        selectedType,
        format,
        data,
        tickers,
        reportCtx,
        provenance
      );
      setLastReport(report);
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Report generation failed";
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
      const resp = (await optimizePortfolio({
        tickers: useTickers,
        objective: session.objective || "hybrid",
        weight_min: session.constraints.weightMin ?? DEFAULT_WEIGHT_MIN,
        maxWeight: session.constraints.weightMax ?? DEFAULT_WEIGHT_MAX,
      })) as Record<string, unknown>;
      const data = mergeOptimizeResponse(resp);
      const provenance: ReportProvenance = {
        source: "fresh",
        snapshot_at: null,
      };

      const report = buildAndDownload(
        selectedType,
        format,
        data,
        useTickers,
        reportCtx,
        provenance
      );
      setLastReport(report);
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "Report generation failed";
      setError(msg);
    } finally {
      setGenerating(false);
    }
  }, [selectedType, format, session, reportCtx]);

  return {
    selectedType,
    setSelectedType,
    format,
    setFormat,
    generating,
    lastReport,
    error,
    hasSnapshot,
    snapshotAt,
    generateReport,
    generateReportFresh,
  };
}
