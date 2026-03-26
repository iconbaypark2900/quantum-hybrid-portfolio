import { describe, expect, it } from "vitest";

import {
  buildVqeIbmOptimizePayload,
  MAX_IBM_VQE_ASSETS,
} from "./quantumPortfolioJobs";
import type { LedgerSession } from "@/context/LedgerSessionContext";

const baseSession: LedgerSession = {
  tickers: ["AAPL", "MSFT"],
  objective: "hybrid",
  constraints: { weightMin: 0.01, weightMax: 0.5 },
  lastOptimize: null,
};

describe("buildVqeIbmOptimizePayload", () => {
  it("forces vqe objective and keeps tickers and weights", () => {
    const p = buildVqeIbmOptimizePayload(baseSession);
    expect(p.objective).toBe("vqe");
    expect(p.tickers).toEqual(["AAPL", "MSFT"]);
    expect(p.weight_min).toBe(0.01);
    expect(p.maxWeight).toBe(0.5);
  });

  it("applies optional n_layers and n_restarts", () => {
    const p = buildVqeIbmOptimizePayload(baseSession, {
      n_layers: 4,
      n_restarts: 6,
    });
    expect(p.n_layers).toBe(4);
    expect(p.n_restarts).toBe(6);
  });
});

describe("MAX_IBM_VQE_ASSETS", () => {
  it("matches backend cap", () => {
    expect(MAX_IBM_VQE_ASSETS).toBe(20);
  });
});
