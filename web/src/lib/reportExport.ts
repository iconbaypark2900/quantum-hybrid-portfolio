/**
 * Client-side report payload + download helpers for the Reports page.
 * Data comes from `optimizePortfolio` (already unwrapped in `api.ts`).
 */

export type ReportType = "performance" | "risk" | "compliance" | "full";

export interface ReportContext {
  objective?: string;
  weightMin?: number;
  weightMax?: number;
}

export type ReportDataSource = "snapshot" | "fresh";

export interface ReportProvenance {
  source: ReportDataSource;
  /** ISO timestamp of Lab snapshot when source is snapshot; otherwise null */
  snapshot_at: string | null;
}

export interface ReportMetaV2 {
  schema_version: "2";
  data_source: ReportDataSource;
  snapshot_at: string | null;
  objective: string | undefined;
  /** Tickers / universe from API metadata when present */
  tickers?: string[];
  n_assets?: unknown;
  weight_min?: number;
  weight_max?: number;
}

const EPS = 1e-9;

export type WeightViolationIssue = "above_max" | "below_min";

export interface WeightViolationCheck {
  name: string;
  weight: number;
  issue: WeightViolationIssue;
}

export function computeWeightViolations(
  holdings: unknown,
  minW: number,
  maxW: number
): { checks: WeightViolationCheck[]; violation_count: number } {
  const checks: WeightViolationCheck[] = [];
  if (!Array.isArray(holdings)) {
    return { checks, violation_count: 0 };
  }
  for (const h of holdings) {
    if (!h || typeof h !== "object") continue;
    const rec = h as Record<string, unknown>;
    const name = String(rec.name ?? "");
    const w = typeof rec.weight === "number" ? rec.weight : Number(rec.weight);
    if (!Number.isFinite(w)) continue;
    if (w > maxW + EPS) {
      checks.push({ name, weight: w, issue: "above_max" });
    } else if (w < minW - EPS) {
      checks.push({ name, weight: w, issue: "below_min" });
    }
  }
  return { checks, violation_count: checks.length };
}

function resolveObjective(
  data: Record<string, unknown>,
  ctx?: ReportContext
): string | undefined {
  const direct = data.objective;
  if (typeof direct === "string") return direct;
  const qr = data.qsw_result as Record<string, unknown> | undefined;
  if (qr && typeof qr.objective === "string") return qr.objective;
  return ctx?.objective;
}

/** Drop per-benchmark weights in JSON for smaller payloads. */
export function sanitizeBenchmarksForJson(
  benchmarks: Record<string, unknown>
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(benchmarks)) {
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      const rec = { ...(v as Record<string, unknown>) };
      delete rec.weights;
      out[k] = rec;
    } else {
      out[k] = v;
    }
  }
  return out;
}

/** Normalize API payloads that may be JSON strings, `{ data, meta }` envelopes, or async job shapes. */
function normalizeOptimizePayloadToRecord(raw: unknown): Record<string, unknown> {
  if (raw == null) return {};
  if (typeof raw === "string") {
    try {
      return normalizeOptimizePayloadToRecord(JSON.parse(raw) as unknown);
    } catch {
      return {};
    }
  }
  if (typeof raw !== "object" || Array.isArray(raw)) return {};
  return raw as Record<string, unknown>;
}

/**
 * Merge top-level API response with `qsw_result` so holdings/risk remain while metrics prefer QSW fields.
 * Also unwraps `{ data: { ... }, meta }` (axios-style envelope) and folds async optimize `result` / `result.metrics`.
 */
export function mergeOptimizeResponse(resp: unknown): Record<string, unknown> {
  let r = normalizeOptimizePayloadToRecord(resp);

  const innerData = r.data;
  if (
    innerData != null &&
    typeof innerData === "object" &&
    !Array.isArray(innerData)
  ) {
    const d = innerData as Record<string, unknown>;
    const looksLikeOptimizeBody =
      Object.prototype.hasOwnProperty.call(d, "qsw_result") ||
      Object.prototype.hasOwnProperty.call(d, "sharpe_ratio") ||
      Object.prototype.hasOwnProperty.call(d, "holdings") ||
      Object.prototype.hasOwnProperty.call(d, "n_active");
    if (looksLikeOptimizeBody) {
      r = d;
    }
  }

  const qsw = r.qsw_result as Record<string, unknown> | undefined;
  let merged: Record<string, unknown> = { ...r, ...(qsw || {}) };

  const jobRes = merged.result;
  if (
    (merged.sharpe_ratio == null || merged.expected_return == null) &&
    jobRes != null &&
    typeof jobRes === "object" &&
    !Array.isArray(jobRes)
  ) {
    const jr = jobRes as Record<string, unknown>;
    const m = jr.metrics as Record<string, unknown> | undefined;
    merged = { ...merged, ...jr, ...(m || {}) };
  }

  return merged;
}

function resolveBounds(
  data: Record<string, unknown>,
  ctx?: ReportContext
): { minW: number; maxW: number } {
  const apiMeta = data.metadata as Record<string, unknown> | undefined;
  const minW =
    typeof apiMeta?.weight_min === "number"
      ? apiMeta.weight_min
      : (ctx?.weightMin ?? 0.005);
  const maxW =
    typeof apiMeta?.weight_max === "number"
      ? apiMeta.weight_max
      : (ctx?.weightMax ?? 0.2);
  return { minW, maxW };
}

export function buildReportPayload(
  selectedType: ReportType,
  data: Record<string, unknown>,
  tickers: string[],
  ctx?: ReportContext,
  provenance?: ReportProvenance
): Record<string, unknown> {
  const source: ReportDataSource = provenance?.source ?? "fresh";
  const { minW, maxW } = resolveBounds(data, ctx);
  const apiMeta = data.metadata as Record<string, unknown> | undefined;
  const objective = resolveObjective(data, ctx);

  const meta: ReportMetaV2 = {
    schema_version: "2",
    data_source: source,
    snapshot_at: provenance?.snapshot_at ?? null,
    objective,
    tickers: Array.isArray(apiMeta?.tickers)
      ? (apiMeta.tickers as string[])
      : tickers,
    n_assets: apiMeta?.n_assets,
    weight_min: minW,
    weight_max: maxW,
  };

  const report: Record<string, unknown> = {
    generated_at: new Date().toISOString(),
    report_type: selectedType,
    tickers,
    meta,
  };

  const benchmarksRaw = data.benchmarks as Record<string, unknown> | undefined;
  const hasBenchmarks =
    benchmarksRaw && Object.keys(benchmarksRaw).length > 0
      ? sanitizeBenchmarksForJson(benchmarksRaw)
      : undefined;

  const assetsArr = data.assets as unknown[] | undefined;
  const hasAssets = Array.isArray(assetsArr) && assetsArr.length > 0;

  if (selectedType === "performance" || selectedType === "full") {
    const performance: Record<string, unknown> = {
      sharpe_ratio: data.sharpe_ratio,
      expected_return: data.expected_return,
      volatility: data.volatility,
      n_active: data.n_active,
    };
    if (hasBenchmarks) performance.benchmarks = hasBenchmarks;
    if (hasAssets) performance.assets = assetsArr;
    report.performance = performance;
  }

  if (selectedType === "risk" || selectedType === "full") {
    const rm = data.risk_metrics as Record<string, unknown> | undefined;
    const risk: Record<string, unknown> = {
      var_95: rm?.var_95,
      cvar: rm?.cvar,
    };
    if (data.correlation_matrix != null) {
      risk.correlation_matrix = data.correlation_matrix;
    }
    if (data.stage_info != null) {
      risk.stage_info = data.stage_info;
    }
    report.risk = risk;
  }

  if (selectedType === "compliance" || selectedType === "full") {
    const { checks, violation_count } = computeWeightViolations(
      data.holdings,
      minW,
      maxW
    );
    const compliance: Record<string, unknown> = {
      objective_used: objective ?? ctx?.objective ?? "hybrid",
      bounds: { min: minW, max: maxW },
      checks,
      violation_count,
      timestamp: new Date().toISOString(),
    };
    if (data.stage_info != null) {
      compliance.stage_info = data.stage_info;
    }
    report.compliance = compliance;
  }

  if (selectedType === "full") {
    report.holdings = data.holdings;
    report.sector_allocation = data.sector_allocation;
  }

  return report;
}

/** Strip nested/tabular fields before CSV key,value flatten so values stay human-readable. */
export function stripReportForCsvFlat(
  report: Record<string, unknown>
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...report };
  delete out.holdings;
  delete out.sector_allocation;

  if (out.performance && typeof out.performance === "object") {
    const p = { ...(out.performance as Record<string, unknown>) };
    delete p.benchmarks;
    delete p.assets;
    out.performance = p;
  }
  if (out.risk && typeof out.risk === "object") {
    const r = { ...(out.risk as Record<string, unknown>) };
    delete r.correlation_matrix;
    delete r.stage_info;
    out.risk = r;
  }
  if (out.compliance && typeof out.compliance === "object") {
    const c = { ...(out.compliance as Record<string, unknown>) };
    delete c.checks;
    delete c.stage_info;
    out.compliance = c;
  }
  return out;
}

/** RFC 4180: escape and quote a single CSV field */
export function escapeCsvField(value: string): string {
  const escaped = value.replace(/"/g, '""');
  return `"${escaped}"`;
}

function flattenScalars(
  obj: unknown,
  prefix: string,
  rows: { key: string; value: string }[]
): void {
  if (obj === null || obj === undefined) {
    rows.push({ key: prefix, value: "" });
    return;
  }
  if (Array.isArray(obj)) {
    rows.push({
      key: prefix,
      value: JSON.stringify(obj),
    });
    return;
  }
  if (typeof obj === "object") {
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      const next = prefix ? `${prefix}.${k}` : k;
      if (v instanceof Date) {
        rows.push({ key: next, value: v.toISOString() });
        continue;
      }
      if (
        v !== null &&
        typeof v === "object" &&
        !Array.isArray(v)
      ) {
        flattenScalars(v, next, rows);
      } else if (Array.isArray(v)) {
        rows.push({ key: next, value: JSON.stringify(v) });
      } else {
        rows.push({ key: next, value: String(v) });
      }
    }
    return;
  }
  rows.push({ key: prefix, value: String(obj) });
}

/** Flat key-value CSV of scalar-ish report fields; skips holdings/sector_allocation (handled in reportToCsv). */
export function toCsvFlat(report: Record<string, unknown>): string {
  const rows: { key: string; value: string }[] = [];
  const rest = { ...report };
  delete rest.holdings;
  delete rest.sector_allocation;
  flattenScalars(rest, "", rows);
  const lines = ["key,value", ...rows.map((r) => `${escapeCsvField(r.key)},${escapeCsvField(r.value)}`)];
  return lines.join("\n");
}

type HoldingRow = { name?: unknown; sector?: unknown; weight?: unknown };

function isHoldingRow(x: unknown): x is HoldingRow {
  return x !== null && typeof x === "object";
}

function appendBenchmarksTable(
  benchmarks: Record<string, unknown>,
  parts: string[]
): void {
  const keys = Object.keys(benchmarks);
  if (keys.length === 0) return;
  parts.push("");
  parts.push("benchmark,sharpe,expected_return,volatility");
  for (const name of keys) {
    const v = benchmarks[name];
    if (!v || typeof v !== "object") continue;
    const rec = v as Record<string, unknown>;
    parts.push(
      [name, String(rec.sharpe ?? ""), String(rec.expected_return ?? ""), String(rec.volatility ?? "")].map(escapeCsvField).join(",")
    );
  }
}

function appendAssetsTable(assets: unknown[], parts: string[]): void {
  if (!Array.isArray(assets) || assets.length === 0) return;
  parts.push("");
  parts.push("name,sector,return,volatility,sharpe");
  for (const a of assets) {
    if (!a || typeof a !== "object") continue;
    const rec = a as Record<string, unknown>;
    parts.push(
      [
        String(rec.name ?? ""),
        String(rec.sector ?? ""),
        String(rec.return ?? ""),
        String(rec.volatility ?? ""),
        String(rec.sharpe ?? ""),
      ].map(escapeCsvField).join(",")
    );
  }
}

function appendCorrelationUpperTriangle(
  matrix: unknown,
  tickers: string[],
  parts: string[]
): void {
  if (!Array.isArray(matrix) || matrix.length === 0) return;
  const n = matrix.length;
  parts.push("");
  parts.push("ticker_a,ticker_b,correlation");
  for (let i = 0; i < n; i++) {
    const row = matrix[i];
    if (!Array.isArray(row)) continue;
    for (let j = i + 1; j < n; j++) {
      const v = row[j];
      const a = tickers[i] ?? `col_${i}`;
      const b = tickers[j] ?? `col_${j}`;
      const val = typeof v === "number" ? String(v) : String(v ?? "");
      parts.push([a, b, val].map(escapeCsvField).join(","));
    }
  }
}

function appendComplianceChecksRows(
  checks: unknown,
  parts: string[]
): void {
  if (!Array.isArray(checks) || checks.length === 0) return;
  parts.push("");
  parts.push("name,weight,issue");
  for (const c of checks) {
    if (!c || typeof c !== "object") continue;
    const rec = c as Record<string, unknown>;
    parts.push(
      [
        String(rec.name ?? ""),
        String(rec.weight ?? ""),
        String(rec.issue ?? ""),
      ].map(escapeCsvField).join(",")
    );
  }
}

function appendStageInfoKv(stageInfo: unknown, parts: string[]): void {
  if (!stageInfo || typeof stageInfo !== "object" || Array.isArray(stageInfo)) {
    return;
  }
  parts.push("");
  parts.push("key,value");
  for (const [k, v] of Object.entries(stageInfo as Record<string, unknown>)) {
    const val =
      v !== null && typeof v === "object"
        ? JSON.stringify(v)
        : String(v ?? "");
    parts.push([k, val].map(escapeCsvField).join(","));
  }
}

/** Full report CSV: flat meta + optional holdings and sector tables */
export function reportToCsv(report: Record<string, unknown>): string {
  const parts: string[] = [toCsvFlat(stripReportForCsvFlat(report))];

  const perf = report.performance as Record<string, unknown> | undefined;
  if (perf?.benchmarks && typeof perf.benchmarks === "object") {
    appendBenchmarksTable(perf.benchmarks as Record<string, unknown>, parts);
  }
  if (perf?.assets && Array.isArray(perf.assets)) {
    appendAssetsTable(perf.assets as unknown[], parts);
  }

  const risk = report.risk as Record<string, unknown> | undefined;
  if (risk?.correlation_matrix != null) {
    const tickers = Array.isArray(report.tickers)
      ? (report.tickers as string[])
      : [];
    appendCorrelationUpperTriangle(risk.correlation_matrix, tickers, parts);
  }

  const comp = report.compliance as Record<string, unknown> | undefined;
  if (comp?.checks) {
    appendComplianceChecksRows(comp.checks, parts);
  }

  const siRisk = risk?.stage_info;
  const siComp = comp?.stage_info;
  if (siRisk != null && typeof siRisk === "object") {
    appendStageInfoKv(siRisk, parts);
  } else if (siComp != null && typeof siComp === "object") {
    appendStageInfoKv(siComp, parts);
  }

  const holdings = report.holdings;
  if (Array.isArray(holdings) && holdings.length > 0 && isHoldingRow(holdings[0])) {
    const sorted = [...holdings].sort((a, b) => {
      const wa = Number((a as HoldingRow).weight) || 0;
      const wb = Number((b as HoldingRow).weight) || 0;
      return wb - wa;
    });
    parts.push("");
    parts.push("name,weight,sector");
    for (const h of sorted) {
      if (!isHoldingRow(h)) continue;
      const name = String(h.name ?? "");
      const w = h.weight;
      const weightStr = typeof w === "number" ? String(w) : String(w ?? "");
      const sector = String(h.sector ?? "");
      parts.push(
        [name, weightStr, sector].map((c) => escapeCsvField(c)).join(",")
      );
    }
  }

  const sectors = report.sector_allocation;
  if (Array.isArray(sectors) && sectors.length > 0) {
    const first = sectors[0];
    if (first && typeof first === "object" && "sector" in first) {
      parts.push("");
      parts.push("sector,weight");
      for (const s of sectors) {
        if (!s || typeof s !== "object") continue;
        const rec = s as Record<string, unknown>;
        const sec = String(rec.sector ?? "");
        const w = rec.weight;
        const weightStr = typeof w === "number" ? String(w) : String(w ?? "");
        parts.push([sec, weightStr].map((c) => escapeCsvField(c)).join(","));
      }
    }
  }

  return parts.join("\n");
}

/** @deprecated Use reportToCsv for exports; kept for tests expecting old flatten behavior */
export function toCsv(data: Record<string, unknown>): string {
  return reportToCsv(data);
}

export function downloadFile(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Analyst Run Bundle V3 ────────────────────────────────────────────────────

export type RunKind = "browser" | "lab_run" | "session";

/** Extracted optimize request inputs — all optional since they may not be persisted. */
export interface AnalystInputs {
  tickers?: string[];
  asset_names?: string[];
  returns?: number[];
  covariance?: number[][];
  sectors?: string[];
  objective?: string;
  weight_min?: number;
  weight_max?: number;
  K?: number | null;
  K_screen?: number | null;
  K_select?: number | null;
  n_layers?: number;
  n_restarts?: number;
  lambda_risk?: number;
  gamma?: number;
  seed?: number;
}

export interface AnalystRunBundleV3 {
  schema_version: "3";
  run_id: string;
  run_kind: RunKind;
  captured_at: string;
  snapshot_at: string | null;
  tickers: string[];
  /** Merged API optimize response — single source of truth for charts and CSV. */
  optimize: Record<string, unknown>;
  /** Optional: structured request inputs when the raw payload is available. */
  inputs: AnalystInputs | null;
}

const INPUT_STRIP_KEYS = new Set(["__api_key", "api_key", "password", "token"]);

/** Extract analyst-relevant inputs from a raw optimize request payload. */
export function extractInputsFromPayload(raw: unknown): AnalystInputs | null {
  if (raw == null || typeof raw !== "object" || Array.isArray(raw)) return null;
  const r = raw as Record<string, unknown>;

  const out: AnalystInputs = {};
  let hasAny = false;

  function pick<T>(key: string, guard: (v: unknown) => v is T, target: keyof AnalystInputs) {
    if (INPUT_STRIP_KEYS.has(key)) return;
    const v = r[key];
    if (v !== undefined && guard(v)) {
      (out as Record<string, unknown>)[target] = v;
      hasAny = true;
    }
  }

  const isNum = (v: unknown): v is number => typeof v === "number";
  const isNumArr = (v: unknown): v is number[] =>
    Array.isArray(v) && v.every((x) => typeof x === "number");
  const isNum2d = (v: unknown): v is number[][] =>
    Array.isArray(v) && v.every((row) => Array.isArray(row) && row.every((x) => typeof x === "number"));
  const isStrArr = (v: unknown): v is string[] =>
    Array.isArray(v) && v.every((x) => typeof x === "string");
  const isStr = (v: unknown): v is string => typeof v === "string";
  const isNumOrNull = (v: unknown): v is number | null =>
    v === null || typeof v === "number";

  pick("tickers", isStrArr, "tickers");
  pick("asset_names", isStrArr, "asset_names");
  pick("returns", isNumArr, "returns");
  pick("covariance", isNum2d, "covariance");
  pick("sectors", isStrArr, "sectors");
  pick("objective", isStr, "objective");
  pick("weight_min", isNum, "weight_min");
  pick("weight_max", isNum, "weight_max");
  pick("maxWeight", isNum, "weight_max"); // legacy alias
  pick("K", isNumOrNull, "K");
  pick("K_screen", isNumOrNull, "K_screen");
  pick("K_select", isNumOrNull, "K_select");
  pick("n_layers", isNum, "n_layers");
  pick("n_restarts", isNum, "n_restarts");
  pick("lambda_risk", isNum, "lambda_risk");
  pick("gamma", isNum, "gamma");
  pick("seed", isNum, "seed");

  return hasAny ? out : null;
}

export interface BuildBundleOptions {
  runId: string;
  runKind: RunKind;
  tickers: string[];
  provenance?: ReportProvenance;
  rawPayload?: unknown;
}

/** Build the single source-of-truth artifact for one optimization run. */
export function buildAnalystRunBundle(
  merged: Record<string, unknown>,
  opts: BuildBundleOptions
): AnalystRunBundleV3 {
  return {
    schema_version: "3",
    run_id: opts.runId,
    run_kind: opts.runKind,
    captured_at: new Date().toISOString(),
    snapshot_at: opts.provenance?.snapshot_at ?? null,
    tickers: opts.tickers,
    optimize: merged,
    inputs: extractInputsFromPayload(opts.rawPayload),
  };
}

/** Download the analyst bundle JSON with a stable filename. */
export function downloadAnalystBundle(
  bundle: AnalystRunBundleV3,
  filenamePrefix = "analyst_run"
): void {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  downloadFile(
    JSON.stringify(bundle, null, 2),
    `${filenamePrefix}_${bundle.run_id.slice(0, 8)}_${ts}.json`,
    "application/json"
  );
}

/** Download CSV derived from the same `bundle.optimize` object, proving single source of truth. */
export function downloadAnalystCsvFromBundle(
  bundle: AnalystRunBundleV3,
  ctx?: ReportContext,
  filenamePrefix = "analyst_run"
): void {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const report = buildReportPayload(
    "full",
    bundle.optimize,
    bundle.tickers,
    ctx,
    { source: bundle.snapshot_at ? "snapshot" : "fresh", snapshot_at: bundle.snapshot_at }
  );
  downloadFile(
    reportToCsv(report as Record<string, unknown>),
    `${filenamePrefix}_${bundle.run_id.slice(0, 8)}_${ts}.csv`,
    "text/csv"
  );
}
