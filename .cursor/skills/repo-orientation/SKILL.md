---
name: repo-orientation
description: Orients work in unfamiliar or partially familiar codebases by finding entry points, tracing flows, mapping layers and cross-cutting concerns, listing concrete file paths, flagging coupling and duplication, and naming the smallest safe change location. Use when starting a task in a new repo, after cloning, when touching an unfamiliar area, or when the user asks how the code is organized or where to change something safely.
---

# Repo orientation (unfamiliar codebase)

## When to apply

Use **before** or **alongside** implementation when the task touches modules you have not recently verified. Prefer reading real files over guessing. For the implementation slice after orientation, see [feature-implementation-slice](../feature-implementation-slice/SKILL.md).

## Workflow

### 1. Entry points relevant to the task

- Infer the **surface** from the task: HTTP routes, CLI commands, scheduled jobs, message consumers, UI routes/events, library public APIs.
- Locate them using repo docs (`README`, `docs/`), config (`package.json`, `pyproject.toml`, Docker, CI), and search (route decorators, `main`, `App`, framework conventions).
- Name **specific** entry symbols (e.g. handler name, component, script) and tie each to the user’s task.

### 2. Request / data / control flow

- Pick one primary path for the task (e.g. one API call or one user action).
- Trace **forward**: entry → orchestration → domain/services → persistence/external I/O → response.
- Note **data**: request/response shapes, DTOs, DB models, file formats, and where validation/mapping happens.
- Note **control**: sync vs async, background jobs, callbacks, and error propagation.

### 3. Architecture layers and cross-cutting concerns

- State how this repo splits concerns (examples: routes vs services vs repositories; pages vs hooks vs API client; pipelines vs methods).
- List **cross-cutting** items that affect the change: auth, logging, metrics, feature flags, config/env, transactions, caching, feature-specific middleware.
- Do not invent layers; **derive** them from directory layout and imports.

### 4. Exact files most likely involved

- List **paths** (not only directories), grouped by role: entry, orchestration, domain logic, I/O, tests, config.
- If multiple candidates exist, list top 3–7 per category and say what would confirm each (e.g. grep, one test file, one call site).

### 5. Duplication, coupling, ownership risks

- **Duplication**: same logic in two places, copy-pasted helpers, divergent implementations of one concept.
- **Hidden coupling**: shared globals, implicit ordering, side effects in constructors, circular imports, “god” modules imported everywhere.
- **Unclear ownership**: ambiguous module boundaries, TODO/FIXME hotspots, files mixing unrelated responsibilities.
- Mark each finding with **evidence** (file + short note), not only intuition.

### 6. Minimum safe place to change

- Recommend the **smallest** surface that satisfies the task without breaking contracts: prefer pure functions or isolated services over wide refactors.
- Say what **must** stay stable (public API, DB schema, event payloads) and what can flex.
- If safety is unclear, state what single read or test would resolve it.

## Output template

Use this structure when reporting to the user (adjust depth to task size):

```markdown
## Task (one line)
[Restate the goal]

## Entry points
- [surface] `path` — [symbol or route] — why relevant

## Flow (primary path)
1. …
2. …

## Layers & cross-cutting
- Layers: …
- Cross-cutting: …

## Files involved (concrete paths)
- `...` — …
- `...` — …

## Risks / smells
- Duplication: …
- Coupling: …
- Ownership: …

## Minimum safe change
- **Place:** `path` / layer — [one sentence]
- **Stable contracts:** …
- **Open question (if any):** …
```

## Principles

- Prefer **evidence from the repo** over generic stack advice.
- Keep the first pass **bounded**; deepen only where the task requires it.
- If the codebase has a documented architecture, **align** the summary with it or note conflicts.
