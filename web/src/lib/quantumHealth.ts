/**
 * Helpers for Quantum page telemetry (health envelope from GET /api/health).
 */

export type ApiHealthTone = "ok" | "warn" | "bad" | "unknown";

export function apiHealthPresentation(data: Record<string, unknown> | null): {
  label: string;
  tone: ApiHealthTone;
} {
  if (!data || typeof data.status !== "string") {
    return { label: "Unknown", tone: "unknown" };
  }
  const s = data.status;
  if (s === "healthy") {
    return { label: "Online", tone: "ok" };
  }
  if (s === "degraded") {
    return { label: "Degraded", tone: "warn" };
  }
  return { label: "Offline", tone: "bad" };
}
