/**
 * `/api/config/objectives` and `/api/config/presets` return `{ objectives: [...] }` / `{ presets: [...] }`
 * after the axios envelope unwrap in `api.ts`. These helpers build keyed maps for the Strategy UI.
 */

export type ObjectiveFamily = "classical" | "hybrid" | "quantum";

export interface PaperRef {
  title?: string;
  citation?: string;
  url?: string;
}

export interface NotebookRef {
  path: string;
  title?: string;
}

export interface CodeRef {
  path: string;
  label?: string;
}

export interface ObjectiveInfo {
  label: string;
  description: string;
  /** Legacy single-line reference; superseded by `papers` when present */
  paper?: string;
  fast: boolean;
  family: ObjectiveFamily;
  papers: PaperRef[];
  notebooks: NotebookRef[];
  codeRefs: CodeRef[];
}

export interface PresetInfo {
  label: string;
  /** Short explanation; pairs with Simulations stress narratives when set. */
  description?: string;
  objective: string;
  weight_min: number;
  weight_max: number;
  K?: number | null;
  K_screen?: number | null;
  K_select?: number | null;
}

function parseFamily(raw: unknown): ObjectiveFamily {
  if (raw === "hybrid" || raw === "quantum" || raw === "classical") {
    return raw;
  }
  return "classical";
}

function parsePapers(raw: unknown, legacyPaper: string | undefined): PaperRef[] {
  const out: PaperRef[] = [];
  if (Array.isArray(raw)) {
    for (const row of raw) {
      if (!row || typeof row !== "object") continue;
      const p = row as Record<string, unknown>;
      const title = typeof p.title === "string" ? p.title : undefined;
      const citation = typeof p.citation === "string" ? p.citation : undefined;
      const url = typeof p.url === "string" ? p.url : undefined;
      if (title || citation || url) {
        out.push({ title, citation, url });
      }
    }
  }
  if (out.length === 0 && legacyPaper) {
    out.push({ citation: legacyPaper });
  }
  return out;
}

function parseNotebooks(raw: unknown): NotebookRef[] {
  if (!Array.isArray(raw)) return [];
  const out: NotebookRef[] = [];
  for (const row of raw) {
    if (!row || typeof row !== "object") continue;
    const n = row as Record<string, unknown>;
    const path = typeof n.path === "string" ? n.path : null;
    if (!path) continue;
    out.push({
      path,
      title: typeof n.title === "string" ? n.title : undefined,
    });
  }
  return out;
}

function parseCodeRefs(raw: unknown): CodeRef[] {
  if (!Array.isArray(raw)) return [];
  const out: CodeRef[] = [];
  for (const row of raw) {
    if (!row || typeof row !== "object") continue;
    const c = row as Record<string, unknown>;
    const path = typeof c.path === "string" ? c.path : null;
    if (!path) continue;
    out.push({
      path,
      label: typeof c.label === "string" ? c.label : undefined,
    });
  }
  return out;
}

export function normalizeObjectives(
  payload: unknown
): Record<string, ObjectiveInfo> {
  if (!payload || typeof payload !== "object") return {};
  const raw = payload as { objectives?: unknown };
  if (!Array.isArray(raw.objectives)) return {};
  const out: Record<string, ObjectiveInfo> = {};
  for (const row of raw.objectives) {
    if (!row || typeof row !== "object") continue;
    const o = row as Record<string, unknown>;
    const id = typeof o.id === "string" ? o.id : null;
    if (!id) continue;
    const legacyPaper =
      typeof o.paper === "string" ? o.paper : undefined;
    const papers = parsePapers(o.papers, legacyPaper);
    const codeRefs = parseCodeRefs(o.code_refs);
    out[id] = {
      label: typeof o.label === "string" ? o.label : id,
      description: typeof o.description === "string" ? o.description : "",
      paper: legacyPaper,
      fast: Boolean(o.fast),
      family: parseFamily(o.family),
      papers,
      notebooks: parseNotebooks(o.notebooks),
      codeRefs,
    };
  }
  return out;
}

export function normalizePresets(
  payload: unknown
): Record<string, PresetInfo> {
  if (!payload || typeof payload !== "object") return {};
  const raw = payload as { presets?: unknown };
  if (!Array.isArray(raw.presets)) return {};
  const out: Record<string, PresetInfo> = {};
  for (const row of raw.presets) {
    if (!row || typeof row !== "object") continue;
    const p = row as Record<string, unknown>;
    const id = typeof p.id === "string" ? p.id : null;
    if (!id) continue;
    const desc = p.description;
    out[id] = {
      label: typeof p.label === "string" ? p.label : id,
      description:
        typeof desc === "string" && desc.trim() !== "" ? desc : undefined,
      objective: typeof p.objective === "string" ? p.objective : "hybrid",
      weight_min: typeof p.weight_min === "number" ? p.weight_min : 0.005,
      weight_max: typeof p.weight_max === "number" ? p.weight_max : 0.2,
      K: typeof p.K === "number" ? p.K : p.K === null ? null : undefined,
      K_screen:
        typeof p.K_screen === "number"
          ? p.K_screen
          : p.K_screen === null
            ? null
            : undefined,
      K_select:
        typeof p.K_select === "number"
          ? p.K_select
          : p.K_select === null
            ? null
            : undefined,
    };
  }
  return out;
}
