---
name: pre-change-impact-analysis
description: Maps upstream callers and downstream consumers, checks schema/API/config/UI contracts, surfaces hidden dependencies, estimates blast radius (local, feature, system), and recommends the safest change insertion point. Use before modifying existing code, shared types, routes, or persistence; when the user asks for impact analysis, risk assessment, or "what could break."
---

# Pre-change impact analysis

## When to apply

Run **before** editing production paths, shared utilities, API handlers, DB migrations, or anything with multiple call sites. Skip for greenfield files with no consumers yet.

**Pairs well with:** [repo-orientation](../repo-orientation/SKILL.md) (where things live), [refactoring-preserve-behavior](../refactoring-preserve-behavior/SKILL.md) (execution after analysis).

## Workflow (order matters)

### 1. Anchor the change

- State **one sentence**: what is being changed and why (behavior vs structure).
- Name the **entry surface**: symbol, module, route, table, or component file.

### 2. Upstream callers and downstream consumers

- **Upstream (who calls / depends on this):** static search (references to symbol, imports of module, HTTP clients hitting route); note tests and scripts.
- **Downstream (what this calls / uses):** imports, injected services, DB tables, queues, external APIs, child components.
- Flag **dynamic** edges: reflection, stringly keyed registries, plugin loaders, `importlib`, config-driven class names, feature flags branching behavior.

### 3. Contract surfaces

Check implications on each layer that applies to this repo:

| Surface | What to verify |
|--------|----------------|
| **Schema / persistence** | Migrations, ORM models, serializers, backward compatibility of stored data |
| **API** | Request/response models, status codes, pagination, versioning, OpenAPI if present |
| **Config / env** | Defaults, required vars, feature flags, deployment-specific values |
| **UI** | Props, routes, API client types, loading/error states tied to backend shape |

If a layer is untouched, say **"no contract change"** explicitly.

### 4. Hidden dependencies and breakpoints

Look for:

- Shared types re-exported from barrels; duplicate definitions that can drift
- Caching layers (HTTP, CDN, in-process) assuming old shapes or TTL semantics
- Background jobs, cron, webhooks, or consumers outside the main request path
- Serialization boundaries (JSON keys, CSV columns, protobuf) that must stay stable
- Authz: permissions checked in middleware vs route vs resource
- **Breakpoint:** a place where a small edit causes many failures (e.g. renaming a widely imported constant)

Document **uncertainty** when search tools cannot prove completeness (e.g. external callers).

### 5. Blast radius (three levels)

Assign the change a **primary** level and note **escalation** if a mistake propagates.

| Level | Meaning | Typical signals |
|-------|---------|-----------------|
| **Local** | Single module or narrow path; few or no external callers | Private helpers, tests only, feature-flagged branch |
| **Feature-level** | A user-visible flow or bounded subsystem | Multiple files in one feature folder, one API resource family |
| **System-level** | Cross-cutting contracts, infra, or data shared by many features | Global middleware, core DTOs, auth, DB schema used everywhere, queue topics |

### 6. Safest insertion point

Recommend **one** primary approach:

- **Extend alongside** — new function/route/field with adapter at the old surface (lowest risk when contracts must stay stable)
- **Change at the leaf** — edit the deepest private implementation if the public contract is unchanged
- **Introduce a seam** — interface or facade so callers migrate incrementally
- **Big-bang only when** — migration is already planned; list prerequisites (data backfill, dual-write, coordinated deploy)

## Checklist

```
- [ ] Entry surface and intent stated in one sentence
- [ ] Upstream callers listed (incl. tests, jobs, scripts)
- [ ] Downstream dependencies listed
- [ ] Dynamic/indirect call paths considered
- [ ] Schema / API / config / UI implications checked or marked N/A
- [ ] Hidden deps and likely breakpoints noted
- [ ] Blast radius: local | feature | system (+ escalation scenario)
- [ ] Safest insertion point chosen with short rationale
```

## Output template

Report to the user in this structure (adapt sections if N/A):

```markdown
## Pre-change impact

**Change:** [one line]

### Call graph (summary)
- **Upstream:** [callers / trigger types]
- **Downstream:** [dependencies]

### Contracts
- **Schema/persistence:** [...]
- **API:** [...]
- **Config/env:** [...]
- **UI:** [...]

### Risks
- **Hidden / dynamic:** [...]
- **Breakpoints:** [...]
- **Unknowns:** [...]

### Blast radius
- **Primary:** local | feature | system
- **Could escalate to:** [if ...]

### Recommendation
**Safest insertion point:** [extend alongside | leaf change | seam | coordinated change]
**Rationale:** [1–3 sentences]
```

## Anti-patterns

- Declaring "no impact" without searching for references and import sites
- Analyzing only the happy path and ignoring error handling and edge types
- Mixing this analysis with implementation in the same step — finish analysis first, then implement the smallest slice
