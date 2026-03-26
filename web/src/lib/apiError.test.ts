import { describe, expect, it } from "vitest";
import { extractApiErrorMessage } from "./apiError";

describe("extractApiErrorMessage", () => {
  it("prefers nested error.message", () => {
    expect(
      extractApiErrorMessage(new Error("x"), {
        error: { code: "E", message: "nested" },
      })
    ).toBe("nested");
  });

  it("uses error string when present", () => {
    expect(
      extractApiErrorMessage(new Error("x"), { error: "plain string" })
    ).toBe("plain string");
  });

  it("uses top-level message", () => {
    expect(
      extractApiErrorMessage(new Error("x"), { message: "top" })
    ).toBe("top");
  });

  it("falls back to Error message then default", () => {
    expect(extractApiErrorMessage(new Error("axios failed"), {})).toBe(
      "axios failed"
    );
    expect(extractApiErrorMessage({}, undefined)).toBe(
      "An unexpected error occurred"
    );
  });
});
