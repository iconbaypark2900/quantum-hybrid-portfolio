---
name: implementation-done-criteria
description: Defines observable success, happy-path/edge/failure criteria, and maps each to a validation method (manual, unit test, integration test, UI check, metric/log). Use when starting or finishing a feature, bug fix, or refactor; when the user asks for acceptance criteria, definition of done, test plan, or how to validate a change; or when work must have explicit finish-line checks.
---

# Implementation done criteria

## When to apply

Use for any non-trivial **feature**, **bug fix**, or **refactor** where "done" should be objective. Apply **before** coding when possible; **update** after scope changes. Pair with `feature-request-to-spec` (what to build) and `feature-implementation-slice` (how to ship a slice).

## Workflow

### 1. Observable success

Write **one short paragraph** that states what "working" means in **observable** terms: inputs, outputs, user-visible or API-visible behavior, data persisted, or errors surfaced. Avoid vague goals ("make it better"); prefer verifiable statements ("when X, then Y within Z").

### 2. Criteria by class

For the scoped change, list criteria in three buckets:

| Class | Meaning |
|-------|---------|
| **Happy path** | Primary flow succeeds under expected inputs and environment. |
| **Edge case** | Boundaries, empty/null, limits, concurrency/order quirks, backward compatibility. |
| **Failure case** | Invalid input, missing deps, timeouts, permission errors, partial failure; must fail safely and predictably. |

Keep lists proportional to risk: critical paths get more failure/edge coverage than cosmetic UI.

### 3. Map each criterion to validation

For **every** criterion row, assign exactly one **primary** validation method (add a secondary only if needed):

| Method | Use when |
|--------|----------|
| **Manual check** | Exploratory verification, one-off repro, environment-specific behavior. |
| **Unit test** | Pure logic, small functions, deterministic branches. |
| **Integration test** | API/DB/queue/external contract, multi-component wiring. |
| **UI check** | Browser-visible behavior, accessibility spot-checks, client routing. |
| **Metric/log output** | Observability: structured logs, counters, traces, health endpoints. |

Rules:

- Prefer **automated** tests where the behavior is stable and repeated regressions are costly.
- Prefer **manual** or **UI check** when judgment, layout, or environment varies.
- **Metric/log** complements tests: use when production verification or ops handoff matters.

### 4. Finish line

Work is **not** complete until:

- Every **happy-path** criterion has a mapped validation and at least one is executed (or explicitly waived with reason).
- **Edge** and **failure** criteria for high-risk areas are covered or explicitly deferred.
- Any **waived** criterion is documented (e.g. ticket comment) with owner and follow-up.

Update the matrix if scope changes; do not silently drop rows.

## Output template

Paste and fill. One row per criterion; split rows if multiple methods are required.

```markdown
## Observable success
[Paragraph: what "done" looks like in observable terms]

## Criteria and validation

| ID | Class (happy / edge / failure) | Criterion (specific, testable) | Validation method | Notes (command, route, or log id) |
|----|----------------------------------|----------------------------------|---------------------|-------------------------------------|
| C1 | happy | ... | unit test | `pytest path/test_foo.py::...` |
| C2 | edge | ... | integration test | `...` |
| C3 | failure | ... | manual check | steps: ... |
| C4 | ... | ... | UI check | ... |
| C5 | ... | ... | metric/log | e.g. structured field `...` |

## Finish-line status
- [ ] All in-scope rows satisfied or waived
- Waivers: [none | ID + reason + follow-up]
```

## Examples (minimal)

**Bug fix (API returns 500 on empty body)**

- Observable success: Empty JSON body returns 400 with stable error shape, not 500.
- C1 happy: Valid body still works — integration test.
- C2 edge: Empty body — integration test.
- C3 failure: Malformed JSON — integration test.

**Refactor (extract service, no behavior change)**

- Observable success: Same public API and responses for a frozen fixture set; no new errors in logs at default level.
- C1 happy: Contract unchanged — integration or unit tests on preserved interfaces.
- C2 edge: Same error codes/messages for known failures — tests or manual spot-check per waiver policy.

## Additional resources

- For spec-level inputs/outputs before criteria, see [../feature-request-to-spec/SKILL.md](../feature-request-to-spec/SKILL.md).
- For shipping a vertical slice after criteria exist, see [../feature-implementation-slice/SKILL.md](../feature-implementation-slice/SKILL.md).
