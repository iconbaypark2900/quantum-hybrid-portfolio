---
name: paper-to-implementation
description: Extracts core algorithmic mechanisms from research, defers non-essential complexity, maps modules/APIs/data flow, defines a minimal PoC path, and states evidence needed before productionization. Use when translating papers or research into code, scoping a literature-based feature, comparing claims to an implementation plan, or when the user mentions theory-to-practice, proof of concept, or research translation.
---

# Paper → implementation

## When to apply

Use when the starting point is a **paper, preprint, textbook section, or conceptual description** rather than an existing codebase spec. Complements `feature-implementation-slice` for the actual build: first produce this plan, then implement the smallest slice.

## Workflow (five steps)

### 1. Extract the core algorithmic mechanism

Answer in plain language (no jargon stacking):

- **Problem class**: What input → output family does the method address?
- **Inductive bias / assumption**: What must be true about the world or data for this to work?
- **Core loop**: The single repeated step (optimization, inference, sampling, message passing, etc.).
- **What is novel vs standard**: Which parts are new vs off-the-shelf (e.g. known optimizer + new objective).

If the source is ambiguous, list **interpretations** and pick one primary reading with stated uncertainty.

### 2. Ignore non-essential paper complexity at first

Before designing the full system, **strip** what does not belong in the first PoC:

- **Defer**: secondary theorems, full ablations, optional regularizers, scale/speed tricks, full hyperparameter grids, every baseline from the paper.
- **Keep**: the mechanism that makes the method different from a naive baseline, one clear objective/loop, and the minimum data/interface needed to exercise it.
- **Explicit deferrals table** (name what returns in phase 2+):

| Deferred item | Why not PoC | When to revisit |
|---------------|-------------|-----------------|
| … | … | … |

### 3. Modules, APIs, and data flow

Separate four views:

| View | Deliverable |
|------|-------------|
| **Modules** | Named components (ingestion, model, loss, solver, metrics, I/O). Each has one job. |
| **APIs** | External boundaries: CLI args, REST/JSON fields, function signatures callers depend on; version-sensitive contracts. |
| **Data flow** | Types/shapes at boundaries; what is batched vs stateful; where randomness enters. |
| **Algorithms** | Pseudocode or numbered steps for the non-obvious parts; cite equation numbers if from a paper. |

Explicitly call out **orchestration** (who calls whom) vs **pure transforms** (functions of inputs).

### 4. Minimal proof-of-concept path

Define one **vertical sliver** that proves the mechanism, not the full system:

- **In scope**: Inputs, one backend path, outputs (artifacts or API response).
- **Out of scope**: Everything else, named explicitly.
- **Stub policy**: What may be mocked (e.g. fixed covariance) and what must be real (e.g. the actual loss or circuit).
- **Stop condition**: What “runs end-to-end once” means for this PoC.

Optional: align phasing with dependencies and risk:

| Phase | Scope | Depends on | Risk |
|-------|--------|------------|------|
| PoC | Minimal assumptions, smallest real core | — | … |
| Next | Stronger assumptions or more data | … | … |
| Later | Full paper fidelity or scale | … | … |

Flag **blockers**: missing data, unavailable APIs, compute limits, licensing, need for human labels.

### 5. Evidence: prototype vs productionization

**Prototype (PoC) evidence** — measurable, tied to the PoC scope:

| Category | What to define |
|----------|----------------|
| **Correctness / sanity** | Invariants, known small cases, reproducibility (seeds). |
| **Comparison** | Baseline (simple heuristic, prior method, or ablation). |
| **Efficiency** | Time/memory acceptable for PoC scale (order-of-magnitude). |
| **Failure modes** | When the method should degrade; what to log when it does. |

Avoid success criteria that require the full paper setup if the PoC is intentionally smaller.

**Productionization bar** — what would justify moving beyond PoC (name thresholds or gates, not vague “more testing”):

| Gate | Evidence | Owner / artifact |
|------|----------|-------------------|
| **Correctness at target scale** | e.g. error bounds, held-out metrics, parity with reference impl on fixed seeds | … |
| **Robustness** | stress inputs, drift, worst-case slices | … |
| **Ops** | latency SLO, cost per run, failure recovery, observability | … |
| **Safety / compliance** | if applicable: audit trail, data handling | … |

## Output template

Report using this structure (adapt headings if the source is not a formal paper):

```markdown
## Core mechanism
- Problem class: …
- Assumptions: …
- Core loop: …
- Novel vs standard: …

## Deferred complexity (not in PoC)
| Item | Why deferred | Revisit when |
|------|--------------|--------------|

## Architecture sketch
### Modules
- …

### APIs (boundaries)
- …

### Data flow
- …

### Algorithms (non-obvious steps)
1. …

## Minimal PoC
- In scope: …
- Out of scope: …
- Stubs: …
- Done when: …

## Evidence
### PoC
- Correctness/sanity: …
- Baselines/ablations: …
- Efficiency (PoC scale): …
- Failure modes: …

### Productionization bar
| Gate | Evidence | Artifact |
|------|----------|----------|
```

## Handoff

When moving to code in this repo, switch to [feature-implementation-slice](../feature-implementation-slice/SKILL.md): map the PoC to concrete files, tests, and one shippable slice.

## Additional resources

- For structured debugging after implementation, see [systematic-debugging](../systematic-debugging/SKILL.md).
- For ML/RAG-specific evaluation rigor, see [retrieval-ml-change-evaluation](../retrieval-ml-change-evaluation/SKILL.md).
