import { describe, expect, it } from "vitest";

import {
  buildReportPayload,
  computeWeightViolations,
  escapeCsvField,
  mergeOptimizeResponse,
  reportToCsv,
  sanitizeBenchmarksForJson,
  stripReportForCsvFlat,
  toCsv,
} from "./reportExport";

describe("buildReportPayload", () => {
  const base = {
    sharpe_ratio: 1.2,
    expected_return: 0.08,
    volatility: 0.15,
    n_active: 5,
    risk_metrics: { var_95: -0.02, cvar: -0.03 },
    holdings: [{ name: "AAPL", weight: 0.1, sector: "tech" }],
    sector_allocation: [{ sector: "tech", weight: 0.4 }],
  };

  const provenance = {
    source: "fresh" as const,
    snapshot_at: null as string | null,
  };

  it("includes performance only for performance type", () => {
    const r = buildReportPayload("performance", base, ["AAPL"], {}, provenance);
    expect(r.performance).toBeDefined();
    expect(r.risk).toBeUndefined();
    expect(r.holdings).toBeUndefined();
    expect((r.meta as { schema_version: string }).schema_version).toBe("2");
    expect((r.meta as { data_source: string }).data_source).toBe("fresh");
  });

  it("full includes holdings and sector_allocation", () => {
    const r = buildReportPayload("full", base, ["AAPL"], {}, provenance);
    expect(r.holdings).toEqual(base.holdings);
    expect(r.sector_allocation).toEqual(base.sector_allocation);
  });

  it("records snapshot provenance", () => {
    const snap = { source: "snapshot" as const, snapshot_at: "2020-01-01T00:00:00.000Z" };
    const r = buildReportPayload("performance", base, ["AAPL"], {}, snap);
    const meta = r.meta as { data_source: string; snapshot_at: string | null };
    expect(meta.data_source).toBe("snapshot");
    expect(meta.snapshot_at).toBe(snap.snapshot_at);
  });

  it("resolves objective from data", () => {
    const r = buildReportPayload(
      "performance",
      { ...base, objective: "max_sharpe" },
      ["AAPL"],
      {},
      provenance
    );
    expect((r.meta as { objective?: string }).objective).toBe("max_sharpe");
  });

  it("embeds benchmarks and assets for performance when API sends them", () => {
    const data = {
      ...base,
      benchmarks: {
        equal_weight: {
          weights: [0.5, 0.5],
          sharpe: 0.9,
          expected_return: 0.07,
          volatility: 0.12,
        },
      },
      assets: [
        { name: "AAPL", sector: "tech", return: 0.1, volatility: 0.2, sharpe: 0.5 },
      ],
    };
    const r = buildReportPayload("performance", data, ["AAPL"], {}, provenance);
    const perf = r.performance as Record<string, unknown>;
    const bench = perf.benchmarks as Record<string, unknown>;
    expect(bench.equal_weight).toBeDefined();
    expect((bench.equal_weight as Record<string, unknown>).weights).toBeUndefined();
    expect(Array.isArray(perf.assets)).toBe(true);
  });

  it("risk report includes correlation and stage_info when present", () => {
    const data = {
      ...base,
      risk_metrics: { var_95: -1, cvar: -2 },
      correlation_matrix: [
        [1, 0.3],
        [0.3, 1],
      ],
      stage_info: { backend: "hybrid", stage2_selected_idx: [0, 1] },
    };
    const r = buildReportPayload("risk", data, ["X", "Y"], {}, provenance);
    const risk = r.risk as Record<string, unknown>;
    expect(risk.correlation_matrix).toEqual(data.correlation_matrix);
    expect(risk.stage_info).toEqual(data.stage_info);
  });

  it("compliance report lists weight violations", () => {
    const data = {
      ...base,
      holdings: [{ name: "BIG", weight: 0.5, sector: "x" }],
      metadata: { weight_min: 0.01, weight_max: 0.2 },
    };
    const r = buildReportPayload("compliance", data, ["BIG"], {}, provenance);
    const comp = r.compliance as Record<string, unknown>;
    expect(comp.violation_count).toBe(1);
    const checks = comp.checks as Array<{ name: string; issue: string }>;
    expect(checks[0].name).toBe("BIG");
    expect(checks[0].issue).toBe("above_max");
  });
});

describe("computeWeightViolations", () => {
  it("flags above max and below min", () => {
    const { checks, violation_count } = computeWeightViolations(
      [
        { name: "Hi", weight: 0.9, sector: "a" },
        { name: "Lo", weight: 0.001, sector: "b" },
      ],
      0.01,
      0.2
    );
    expect(violation_count).toBe(2);
    expect(checks.some((c) => c.issue === "above_max")).toBe(true);
    expect(checks.some((c) => c.issue === "below_min")).toBe(true);
  });
});

describe("sanitizeBenchmarksForJson", () => {
  it("drops weights keys", () => {
    const out = sanitizeBenchmarksForJson({
      m: { weights: [1, 2], sharpe: 1 },
    });
    expect((out.m as Record<string, unknown>).weights).toBeUndefined();
    expect((out.m as Record<string, unknown>).sharpe).toBe(1);
  });
});

describe("mergeOptimizeResponse", () => {
  it("merges qsw_result over top-level response", () => {
    const merged = mergeOptimizeResponse({
      holdings: [{ name: "X", weight: 0.5, sector: "s" }],
      qsw_result: { sharpe_ratio: 9, objective: "hybrid" },
    });
    expect(merged.sharpe_ratio).toBe(9);
    expect(merged.objective).toBe("hybrid");
    expect(Array.isArray(merged.holdings)).toBe(true);
  });

  it("unwraps { data, meta } envelope from API client", () => {
    const merged = mergeOptimizeResponse({
      data: {
        sharpe_ratio: 2.384,
        expected_return: 0.491859,
        volatility: 0.206315,
        n_active: 3,
        qsw_result: {
          sharpe_ratio: 2.384,
          expected_return: 0.491859,
          volatility: 0.206315,
        },
      },
      meta: { duration_ms: 12 },
    });
    expect(merged.sharpe_ratio).toBe(2.384);
    expect(merged.n_active).toBe(3);
  });

  it("folds async job result.metrics when top-level Sharpe missing", () => {
    const merged = mergeOptimizeResponse({
      tickers: ["AAPL"],
      result: {
        metrics: { sharpe_ratio: 1.2, expected_return: 0.1, volatility: 0.2 },
      },
    });
    expect(merged.sharpe_ratio).toBe(1.2);
  });
});

describe("escapeCsvField", () => {
  it("quotes and escapes internal double quotes", () => {
    expect(escapeCsvField('say "hi"')).toBe(`"say ""hi"""`);
  });
});

describe("stripReportForCsvFlat", () => {
  it("removes tabular nested keys from performance and risk", () => {
    const stripped = stripReportForCsvFlat({
      performance: {
        sharpe_ratio: 1,
        benchmarks: { a: { sharpe: 1 } },
        assets: [{ name: "z" }],
      },
      risk: { var_95: 1, correlation_matrix: [[1]], stage_info: { x: 1 } },
    });
    const p = stripped.performance as Record<string, unknown>;
    expect(p.benchmarks).toBeUndefined();
    expect(p.assets).toBeUndefined();
    expect(p.sharpe_ratio).toBe(1);
    const rk = stripped.risk as Record<string, unknown>;
    expect(rk.correlation_matrix).toBeUndefined();
    expect(rk.var_95).toBe(1);
  });
});

describe("toCsv / reportToCsv", () => {
  it("flattens nested keys in flat section", () => {
    const csv = toCsv({ a: { b: 1 }, c: "x" });
    expect(csv).toContain("a.b");
    expect(csv).toContain("c");
    expect(csv.startsWith("key,value")).toBe(true);
  });

  it("emits holdings table for full-shaped report", () => {
    const report = buildReportPayload(
      "full",
      {
        sharpe_ratio: 1,
        expected_return: 0.1,
        volatility: 0.2,
        n_active: 2,
        risk_metrics: { var_95: -0.01, cvar: -0.02 },
        holdings: [
          { name: "B", weight: 0.6, sector: "s1" },
          { name: "A", weight: 0.4, sector: "s2" },
        ],
        sector_allocation: [
          { sector: "s1", weight: 0.6 },
          { sector: "s2", weight: 0.4 },
        ],
      },
      ["A", "B"],
      {},
      { source: "fresh", snapshot_at: null }
    );
    const csv = reportToCsv(report as Record<string, unknown>);
    expect(csv).toContain("name,weight,sector");
    expect(csv).toContain('"B"');
    expect(csv).toContain("sector,weight");
    expect(csv.indexOf('"B"')).toBeLessThan(csv.indexOf("sector,weight"));
  });

  it("emits benchmark, assets, correlation, and compliance sections when present", () => {
    const report = buildReportPayload(
      "full",
      {
        sharpe_ratio: 1,
        expected_return: 0.1,
        volatility: 0.2,
        n_active: 2,
        risk_metrics: { var_95: -0.01, cvar: -0.02 },
        benchmarks: {
          equal_weight: { sharpe: 0.5, expected_return: 0.05, volatility: 0.15 },
        },
        assets: [
          { name: "A", sector: "t", return: 0.1, volatility: 0.2, sharpe: 0.5 },
        ],
        correlation_matrix: [
          [1, 0.4, 0.3],
          [0.4, 1, 0.2],
          [0.3, 0.2, 1],
        ],
        holdings: [
          { name: "B", weight: 0.6, sector: "s1" },
          { name: "OVER", weight: 0.5, sector: "s2" },
        ],
        sector_allocation: [{ sector: "s1", weight: 0.6 }],
        metadata: { weight_min: 0.01, weight_max: 0.2 },
      },
      ["T1", "T2", "T3"],
      {},
      { source: "fresh", snapshot_at: null }
    );
    const csv = reportToCsv(report as Record<string, unknown>);
    expect(csv).toContain("benchmark,sharpe,expected_return,volatility");
    expect(csv).toContain("equal_weight");
    expect(csv).toContain("name,sector,return,volatility,sharpe");
    expect(csv).toContain("ticker_a,ticker_b,correlation");
    expect(csv).toContain("T1");
    expect(csv).toContain("name,weight,issue");
    expect(csv).toContain("OVER");
    expect(csv).not.toMatch(/performance\.benchmarks/);
  });
});
