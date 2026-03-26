---
name: systematic-debugging
description: Structures debugging into reproduction, root-cause analysis, precise blame location, minimal fix, validation or regression tests, and confidence with stated uncertainty. Use when fixing bugs, investigating failures, errors, stack traces, test failures, flaky behavior, or when the user asks for structured debugging.
---

# Systematic debugging

## When to apply

Use for any non-trivial failure: exceptions, wrong results, performance regressions, flaky tests, or “works on my machine” gaps. For trivial typos or obvious one-line fixes, skip heavy ceremony but still name the file and a quick check.

## Workflow

### 1. Reproduce or infer the failure path

- Prefer **reproduction**: same inputs, command, or UI steps; capture logs and environment notes (OS, versions, flags).
- If reproduction is blocked, **infer** the path: start from the symptom (stack trace, failing assertion, API status), walk the call graph backward and forward until the path is coherent.
- State explicitly what is **verified** vs **inferred**.

### 2. Root cause vs symptom

- The **symptom** is what the user sees (error message, bad value, timeout).
- The **root cause** is the earliest incorrect assumption, state, or branch that makes the symptom inevitable.
- Reject “fixes” that only mask the symptom unless the user explicitly wants a guardrail or workaround; if so, label it as such.

### 3. Point to the exact location

- Name **file path** and **function or method** (or route handler / component) where the wrong behavior originates.
- If multiple sites contribute, distinguish **primary** (fix here first) vs **secondary** (callers, shared utilities).

### 4. Propose the minimal fix

- Prefer the **smallest change** that corrects the root cause and matches local patterns (errors, types, logging).
- Avoid scope creep: no refactors unless required for correctness or safety.

### 5. Validation

Pick one or more:

- **Re-run** the reproduction steps or command.
- Add or extend a **regression test** at the best layer (unit for pure logic, integration for I/O or API contracts).
- If tests are impractical, describe a **manual verification** checklist and what would disprove the fix.

### 6. Confidence and uncertainty

Report using a **confidence label** and short rationale:

| Level | Meaning |
|-------|---------|
| **High** | Reproduced; root cause clear; fix verified |
| **Medium** | Strong inference or partial repro; fix plausible |
| **Low** | Thin evidence; multiple hypotheses remain |

List **remaining uncertainty** (edge cases not tested, race conditions, environment-specific behavior).

## Output template

Use this structure when reporting back:

```markdown
## Failure path
- Symptom: ...
- Path: [entry] → ... → [where it breaks]
- Verified: ... / Inferred: ...

## Root cause
- Why the symptom happens (one tight paragraph)
- Primary location: `path/file.ext` — `qualified_name()`

## Minimal fix
- [Bullet list of concrete changes]

## Validation
- [ ] Re-run: `...`
- [ ] Test added/updated: `...`

## Confidence
- **Level**: High | Medium | Low
- **Uncertainty**: ...
```

## Anti-patterns

- Stopping at the first error line without tracing **why** that line ran.
- Renaming or refactoring unrelated code while debugging.
- Claiming certainty without reproduction or without naming **what would falsify** the hypothesis.
