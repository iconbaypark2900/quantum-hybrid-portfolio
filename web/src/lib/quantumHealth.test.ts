import { describe, expect, it } from "vitest";

import { apiHealthPresentation } from "./quantumHealth";

describe("apiHealthPresentation", () => {
  it("maps healthy", () => {
    expect(apiHealthPresentation({ status: "healthy" })).toEqual({
      label: "Online",
      tone: "ok",
    });
  });

  it("maps degraded", () => {
    expect(apiHealthPresentation({ status: "degraded" })).toEqual({
      label: "Degraded",
      tone: "warn",
    });
  });

  it("unknown when null or missing status", () => {
    expect(apiHealthPresentation(null).tone).toBe("unknown");
    expect(apiHealthPresentation({}).tone).toBe("unknown");
  });
});
