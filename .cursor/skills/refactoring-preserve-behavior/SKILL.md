---
name: refactoring-preserve-behavior
description: Structures refactors to preserve behavior first, tighten boundaries without unnecessary contract changes, update imports/types/tests, and record intentional architectural debt. Use when refactoring, restructuring modules, extracting services, moving logic across layers, or when the user asks for a safe refactor workflow.
---

# Refactoring (preserve behavior, clarify boundaries)

## When to apply

Use for moves, extractions, renames, layering cleanup, or any change that reshapes code without intending to change product behavior. For **new behavior**, prefer [feature-implementation-slice](../feature-implementation-slice/SKILL.md).

## Principles (order matters)

1. **Preserve behavior first** — Same inputs and environment → same observable outcomes (API responses, side effects, errors, persisted data). Prefer characterization tests or golden checks before large moves.
2. **Cleaner boundaries, stable contracts** — Move implementation behind clearer modules; keep public surfaces (HTTP schemas, CLI args, exported symbols, env vars) unchanged unless the task explicitly requires a breaking change. If a contract must change, treat it as a separate, explicit step with migration notes.
3. **Imports, types, tests** — After moves, fix all import paths and type references; run or update tests so the suite reflects the new structure. Add tests only where they lock in behavior that was implicit before (e.g. pure function extracted from a god module).
4. **Intentional debt** — Call out shortcuts left on purpose (temporary facades, duplicated logic pending merge, TODO with owner/ticket) so reviewers do not mistake them for accidents.

## Workflow

### 1. Baseline behavior

- Identify observable contract: who calls this code, what is returned, what errors, what I/O.
- If coverage is thin, add a minimal test or script that captures current behavior for the touched paths **before** restructuring (or run existing integration tests and note pass/fail).

### 2. Plan boundaries

- Decide what becomes **public** vs **internal** per module (exports, package `__all__`, API routes unchanged).
- Prefer one coherent move (one slice) over scattering renames across the repo in one commit unless the repo already favors wide mechanical refactors with tooling.

### 3. Execute the move

- Apply the smallest diff that achieves the boundary improvement.
- Avoid scope creep: no feature additions or “while we’re here” behavior changes in the same change set.

### 4. Mechanical follow-through

- Update imports, barrel files, and type definitions.
- Fix linter/type checker; update test paths and mocks that referenced old locations.

### 5. Verify

- Run the narrowest meaningful test command (unit + affected integration).
- For risky paths, manually exercise one critical flow (e.g. one API call or UI action).

### 6. Document debt

- Short list of **intentional** debt: what was not fixed, why, and what would retire it.

## Checklist

```
- [ ] Behavior unchanged (or contract change explicitly scoped and documented)
- [ ] Public contracts unchanged unless required
- [ ] Imports / types / tests updated
- [ ] Tests green
- [ ] Intentional debt noted (or none)
```

## Output template

Use when reporting completion to the user:

```markdown
## Refactor summary
**Goal:** [boundary / readability / duplication removal — one line]

## Behavior
- **Preserved:** [what was verified — tests or manual check]
- **Contract changes:** [none | list with rationale]

## Structure
- **Moved:** [old → new, high level]
- **Public surface:** [unchanged | what changed]

## Mechanical updates
- Imports/types: [done | notable files]
- Tests: [updated paths / new tests]

## Intentional debt
- [None | bullets with reason + optional follow-up ID]
```

## Anti-patterns

- Mixing behavior changes with structural moves in one undifferentiated diff.
- “Cleaning” unrelated files in the same change.
- Renaming exports without searching callers and tests.
- Leaving ambiguity between “not done yet” and “left intentionally.”
