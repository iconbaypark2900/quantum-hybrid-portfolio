---
name: messy-architecture-triage
description: Separates required cleanup from optional cleanup when a task reveals tangled code; flags boundary violations (UI business logic, route orchestration, duplicated transforms, scattered config); recommends the smallest structural refactor that improves maintainability without blocking delivery. Use when the user or task surfaces messy architecture, "tech debt," unclear layers, or asks what to fix now vs later.
---

# Messy architecture triage

## When to apply

Use when a change touches code that mixes concerns, duplicates logic, or spreads configuration—and the user needs a **delivery-safe** path, not a full rewrite.

**Pairs well with:** [pre-change-impact-analysis](../pre-change-impact-analysis/SKILL.md) (blast radius), [refactoring-preserve-behavior](../refactoring-preserve-behavior/SKILL.md) (safe steps), [boundary-data-contracts](../boundary-data-contracts/SKILL.md) (DTO/schema drift).

## Core outputs (always produce these)

1. **Required cleanup** — must fix to ship safely (correctness, security, data integrity, broken contracts, observable bugs).
2. **Optional cleanup** — improves clarity or future velocity but is not blocking; schedule or defer explicitly.
3. **Boundary violations found** — use the checklist below; cite file/symbol evidence when possible.
4. **Smallest structural refactor** — one coherent move that reduces coupling or duplication **without** expanding scope into a framework migration or repo-wide pattern sweep.

## 1. Required vs optional cleanup

| Required (blocking or near-blocking) | Optional (defer unless cheap) |
|-------------------------------------|------------------------------|
| Wrong results, race conditions, or data loss risk | Naming-only or cosmetic consistency |
| Security/authz gaps or secret handling | Deeper abstractions "for elegance" |
| Broken API/UI contract or serialization mismatch | Full layer extraction when a 20-line helper fixes the immediate bug |
| Untestable change because behavior is undefined | Broad style alignment across unrelated modules |
| Duplication that will **definitely** diverge on the next edit (same bug twice) | Duplication that is stable and localized behind one caller |

State **why** each required item blocks delivery. For optional items, give **cost** (files touched, risk) vs **benefit**.

## 2. Boundary violation checklist

Flag violations with **evidence** (e.g. "component computes portfolio weights" + path). Not every task hits every layer—mark **N/A** where appropriate.

### UI owns business logic

Signals:

- Components or hooks contain rules that belong in domain/services (pricing, optimization constraints, eligibility, feature gating beyond presentation).
- API response shaping or business validation only in the client with no shared contract or server validation.
- Multiple UI entry points reimplement the same rule with small differences.

### Routes own orchestration

Signals:

- Handlers sequence many steps (fetch, transform, call provider, persist, notify) with inline control flow instead of a service/use-case function.
- Retry, transaction boundaries, or idempotency live only in the route layer.
- Hard to unit test behavior because it is trapped in framework entrypoints.

### Duplicated transformations

Signals:

- Same mapping/filter/normalization in two+ places (client + server, two services, test + prod helpers that diverge).
- Copy-pasted DTO construction or field renaming chains.
- "Fix once, miss the other" risk on the next schema change.

### Config spread across files

Signals:

- Magic numbers/strings for limits, URLs, feature flags, or algorithm parameters in unrelated modules.
- Partial env reads with inconsistent defaults between layers.
- Behavior changes requiring edits in many files with no single source of truth.

## 3. Smallest structural refactor (constraints)

Recommend **one** primary refactor slice that:

- **Preserves behavior** unless the task explicitly changes behavior (pair with refactoring-preserve-behavior when needed).
- **Touches the smallest set of modules** that removes the worst coupling or duplication for *this* task.
- **Creates a seam** future work can follow: e.g. extract one `useCaseX()` / `service.method`, one shared mapper, one config object loaded in one place.
- **Avoids** simultaneous large moves: no "while we're here" package renames, global DI rewires, or framework upgrades in the same PR unless required.

Template for the recommendation:

```
Smallest refactor:
- Move: [what]
- From: [where]
- To: [where]
- Why now: [ties to required cleanup or high-risk boundary]
- Explicitly out of scope: [what not to do in this pass]
- Validation: [how to prove same behavior]
```

## 4. Escalation: when "small" is not enough

Say so plainly if:

- Correctness requires a **new** authoritative layer (e.g. validation only on client today).
- Duplication spans **teams or repos** and needs a contract/versioning plan.
- Config sprawl reflects **environment** issues (no env separation, secrets in code).

Then split into **phase 1 (ship)** and **phase 2 (harden)** with clear boundaries.

## Checklist

```
- [ ] Required vs optional cleanup listed with rationale
- [ ] Boundary violations: UI logic / route orchestration / dup transforms / config — each addressed or N/A
- [ ] Smallest structural refactor stated with out-of-scope guardrails
- [ ] Validation path named (tests, manual checks, contract checks)
```
