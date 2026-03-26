/**
 * Normalizes Flask `error_response` / legacy shapes — mirrors
 * `frontend/src/services/api.js` interceptor order:
 * `error.message` | `error` (string) | top-level `message` | axios message | fallback.
 */
export function extractApiErrorMessage(
  err: unknown,
  responseData: unknown
): string {
  if (responseData && typeof responseData === "object") {
    const r = responseData as {
      error?: unknown;
      message?: unknown;
    };
    const nested = r.error;
    if (
      nested &&
      typeof nested === "object" &&
      nested !== null &&
      "message" in nested
    ) {
      const m = (nested as { message?: unknown }).message;
      if (typeof m === "string") return m;
    }
    if (typeof nested === "string") return nested;
    if (typeof r.message === "string") return r.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return "An unexpected error occurred";
}
