---
name: feature-implementation-slice
description: Guides end-to-end feature work by tracing flows, aligning with architecture, scoping files, implementing a minimal vertical slice, updating tests, and recording assumptions. Use when implementing a new feature, extending behavior, or when the user asks for a structured implementation workflow.
---

# Feature implementation (minimal slice)

## When to apply

Use this workflow for any non-trivial change: new endpoints, UI behavior, services, or cross-cutting behavior. Skip heavy ceremony for one-line fixes.

## Workflow

### 1. Inspect and trace

- Identify entry points (routes, CLI, jobs, UI events) relevant to the request.
- Follow calls/data until the change naturally belongs: orchestration vs domain vs I/O vs presentation.
- Note existing patterns (naming, error handling, config) to match.

### 2. Architecture fit (short summary)

In a few sentences, state:

- **Where** the behavior lives in the current layering (and why).
- **What** contracts change (API shapes, types, events).
- **What** stays unchanged on purpose.

### 3. Files to touch

List **exact paths** (not directories only) for:

- Implementation
- Tests
- Config or fixtures (if any)

If uncertain after inspection, list candidates and confirm by reading one more hop in the call graph.

### 4. Smallest complete slice

- Prefer one vertical slice that works end-to-end over a broad refactor.
- Avoid drive-by edits outside the slice; match local style and abstractions.
- If the request is large, implement the first shippable slice and explicitly defer the rest to follow-up.

### 5. Tests

- Add or update tests at the **most meaningful** layer for the change (unit for pure logic, integration for I/O or API contracts).
- Run the relevant test command for the repo (or the narrowest subset) and fix failures before finishing.

### 6. Assumptions and follow-ups

Document briefly (in PR description, ticket comment, or code review notes):

| Assumptions | Follow-up work |
|-------------|----------------|
| What you had to assume (data, env, limits) | Deferred items, tech debt, or explicit non-goals |

## Output template

Use this structure when reporting back to the user:

```markdown
## Flow (current)
[2–5 bullets: entry → key steps → exit]

## Architecture fit
[Short paragraph]

## Files to modify
- `path/...` — [role: e.g. route, service, test]

## Slice implemented
[What works now; what is explicitly out of scope]

## Tests
- [ ] Added/updated: `...`
- Command: `...`

## Assumptions
- ...

## Follow-up
- ...
```

## Anti-patterns

- Implementing before tracing the existing flow.
- Vague file lists (“update the API”) without paths.
- Large refactors bundled with the feature.
- Missing tests for new behavior or changed contracts.
- Silent assumptions with no written follow-up.
