import { describe, expect, it } from "vitest";

import { normalizeObjectives, normalizePresets } from "./configApiNormalize";

describe("normalizeObjectives", () => {
  it("maps objectives array to id-keyed record", () => {
    const out = normalizeObjectives({
      objectives: [
        {
          id: "hybrid",
          label: "Hybrid",
          description: "d",
          fast: false,
          family: "hybrid",
          papers: [{ citation: "Test ref" }],
          notebooks: [{ path: "notebooks/x.ipynb", title: "NB" }],
          code_refs: [{ path: "methods/x.py", label: "x" }],
        },
      ],
    });
    expect(out.hybrid?.label).toBe("Hybrid");
    expect(out.hybrid?.fast).toBe(false);
    expect(out.hybrid?.family).toBe("hybrid");
    expect(out.hybrid?.papers[0]?.citation).toBe("Test ref");
    expect(out.hybrid?.notebooks[0]?.path).toBe("notebooks/x.ipynb");
    expect(out.hybrid?.codeRefs[0]?.path).toBe("methods/x.py");
  });

  it("migrates legacy paper into papers", () => {
    const out = normalizeObjectives({
      objectives: [
        { id: "eq", label: "Eq", description: "", fast: true, paper: "Legacy ref" },
      ],
    });
    expect(out.eq?.papers[0]?.citation).toBe("Legacy ref");
  });

  it("returns {} for wrong shape", () => {
    expect(normalizeObjectives({})).toEqual({});
  });
});

describe("normalizePresets", () => {
  it("maps presets array to id-keyed record", () => {
    const out = normalizePresets({
      presets: [
        {
          id: "default",
          label: "Default",
          objective: "hybrid",
          weight_min: 0.005,
          weight_max: 0.3,
        },
      ],
    });
    expect(out.default?.objective).toBe("hybrid");
  });

  it("preserves optional description", () => {
    const out = normalizePresets({
      presets: [
        {
          id: "sim_crash_day",
          label: "Stress · Crash day",
          description: "Pairs with Simulations stress cards.",
          objective: "min_variance",
          weight_min: 0.02,
          weight_max: 0.1,
        },
      ],
    });
    expect(out.sim_crash_day?.description).toContain("Simulations");
  });
});
