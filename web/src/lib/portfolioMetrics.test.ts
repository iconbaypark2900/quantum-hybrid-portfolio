import { describe, expect, it } from "vitest";

import {
  clipNormalizeWeights,
  portfolioMetricsFromWeights,
} from "./simulationEngine";

const mockData = {
  assets: [
    { name: "A", annReturn: 0.1, annVol: 0.2, sector: "Tech" },
    { name: "B", annReturn: 0.08, annVol: 0.15, sector: "Fin" },
  ],
  corr: [
    [1, 0.3],
    [0.3, 1],
  ],
};

describe("portfolioMetricsFromWeights", () => {
  it("matches equal-weight sanity", () => {
    const w = [0.5, 0.5];
    const m = portfolioMetricsFromWeights(w, mockData);
    expect(m.portReturn).toBeGreaterThan(0);
    expect(m.portVol).toBeGreaterThan(0);
    expect(m.sharpe).toBeCloseTo(m.portReturn / m.portVol, 5);
    expect(m.nActive).toBe(2);
  });
});

describe("clipNormalizeWeights", () => {
  it("clips and renormalizes to sum 1", () => {
    const w = clipNormalizeWeights([0.9, 0.9], 0.05, 0.95);
    expect(w[0] + w[1]).toBeCloseTo(1, 6);
    expect(w[0]).toBeGreaterThanOrEqual(0.05);
    expect(w[1]).toBeGreaterThanOrEqual(0.05);
  });
});
