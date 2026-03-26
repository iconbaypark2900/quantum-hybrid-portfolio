import { describe, expect, it } from "vitest";

import { apiMarketPayloadToLabShape } from "./marketDataAdapter";

describe("apiMarketPayloadToLabShape", () => {
  it("maps API market-data shape to lab assets + corr", () => {
    const out = apiMarketPayloadToLabShape({
      assets: ["A", "B"],
      names: ["A", "B"],
      sectors: ["Tech", "Tech"],
      returns: [0.08, 0.1],
      covariance: [
        [0.04, 0.01],
        [0.01, 0.05],
      ],
    });
    expect(out.assets).toHaveLength(2);
    expect(out.assets[0]?.returns.length).toBe(252);
    expect(out.corr[0]?.[0]).toBeCloseTo(1, 5);
    expect(out.regime).toBe("live");
  });
});
