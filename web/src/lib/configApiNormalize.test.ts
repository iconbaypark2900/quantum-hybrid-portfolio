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

  it("parses role field on papers", () => {
    const out = normalizeObjectives({
      objectives: [
        {
          id: "vqe",
          label: "VQE",
          description: "d",
          fast: false,
          family: "quantum",
          papers: [
            { role: "foundational", citation: "Peruzzo (2014)", url: "https://arxiv.org/abs/1304.3061" },
            { role: "modern", citation: "Tilly et al. (2022)", url: "https://arxiv.org/abs/2111.05176" },
          ],
          notebooks: [],
          code_refs: [],
        },
      ],
    });
    expect(out.vqe?.papers[0]?.role).toBe("foundational");
    expect(out.vqe?.papers[1]?.role).toBe("modern");
  });

  it("parses download_path on papers and maps to downloadPath", () => {
    const out = normalizeObjectives({
      objectives: [
        {
          id: "qubo_sa",
          label: "QUBO",
          description: "d",
          fast: false,
          family: "quantum",
          papers: [
            {
              role: "foundational",
              citation: "Orús (2019)",
              url: "https://arxiv.org/abs/1811.03975",
              download_path: "https://arxiv.org/pdf/1811.03975",
            },
          ],
          notebooks: [],
          code_refs: [],
        },
      ],
    });
    expect(out.qubo_sa?.papers[0]?.downloadPath).toBe("https://arxiv.org/pdf/1811.03975");
  });

  it("parses note field on papers", () => {
    const out = normalizeObjectives({
      objectives: [
        {
          id: "hybrid",
          label: "Hybrid",
          description: "d",
          fast: false,
          family: "hybrid",
          papers: [
            {
              role: "modern",
              citation: "Cerezo (2021)",
              url: "https://arxiv.org/abs/2012.09265",
              note: "Related reading only.",
            },
          ],
          notebooks: [],
          code_refs: [],
        },
      ],
    });
    expect(out.hybrid?.papers[0]?.note).toBe("Related reading only.");
  });

  it("parses download_path on notebooks and maps to downloadPath", () => {
    const out = normalizeObjectives({
      objectives: [
        {
          id: "hrp",
          label: "HRP",
          description: "d",
          fast: true,
          family: "classical",
          papers: [],
          notebooks: [
            {
              path: "notebooks/objectives/05-hrp.ipynb",
              title: "HRP",
              download_path: "/downloads/notebooks/05-hrp.ipynb",
            },
          ],
          code_refs: [],
        },
      ],
    });
    expect(out.hrp?.notebooks[0]?.downloadPath).toBe("/downloads/notebooks/05-hrp.ipynb");
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
