---
name: change-validation-test-plan
description: Plans validation for a code change by assigning the smallest coherent tests across unit, integration, and end-to-end layers; requires explicit coverage of happy path, invalid input, partial failure, timeout/retry, and null or data-drift handling. Use when reviewing a change, writing a test plan, scoping PR tests, or when the user asks what to test at each layer or how to minimize tests while proving correctness.
---

# Change validation test plan

## When to apply

Use when validating a **specific change** (feature, bug fix, refactor) and deciding **what to run or add** before merge. Pair with [../implementation-done-criteria/SKILL.md](../implementation-done-criteria/SKILL.md) for acceptance criteria and finish-line checks; this skill focuses on **layer assignment**, **mandatory coverage dimensions**, and **minimal sufficient tests**.

## Layer definitions

Assign each behavior to the **lowest layer** that can falsify the risk. Move **up** only when lower layers cannot represent the contract (real I/O, multi-service flow, browser, or production-like timing).

| Layer | Proves | Typical scope |
|-------|--------|----------------|
| **Unit** | Pure logic, branches, invariants, error mapping from inputs | Single module/function; dependencies mocked or faked |
| **Integration** | Wiring, persistence, APIs, queues, external clients (test doubles or sandboxes), schema contracts | Multiple real components short of full user journey |
| **End-to-end (E2E)** | Full user or system journey in environment close to prod | Browser/app + API + data path; slowest; use sparingly |

Rules:

- **Prefer unit** for deterministic branches (validation, parsing, state machines, retries logic with a fake clock).
- **Prefer integration** for I/O boundaries the change touches (DB, HTTP client, message bus).
- **Reserve E2E** for one or few **critical paths** where only the full stack proves correctness or regressions are catastrophic.

## Mandatory coverage dimensions

For the **in-scope surface** of the change, the plan must explicitly address each row (mark **N/A** with reason only if the change cannot possibly exhibit that dimension).

| Dimension | What to assert |
|-----------|----------------|
| **Happy path** | Primary success under valid inputs and expected environment. |
| **Invalid input** | Rejection or safe handling: validation errors, 4xx, bounded behavior; no silent corruption. |
| **Partial failure** | Downstream or sibling failures: one dependency fails while others succeed; transactional or compensating behavior if applicable. |
| **Timeout / retry** | Time limits respected; retries idempotent or safe; backoff or cap; no duplicate side effects when inappropriate. |
| **Data drift or null** | Missing fields, unexpected types, schema version skew, empty collections; defaults and explicit errors, not undefined behavior. |

Map each dimension to **at least one** test at the appropriate layer; avoid duplicating the same assertion at three layers unless each layer tests a **different failure mode**.

## Smallest test set (minimal proof)

Goal: **fewest tests that still disprove likely bugs** for this change, not exhaustive coverage of the repo.

1. **List risks** introduced or touched by the diff (behavioral, contract, performance-sensitive paths).
2. **Cover each high-risk path once** at the lowest sufficient layer.
3. **Do not** add E2E for logic provable at unit; **do not** skip integration if the change alters a real boundary.
4. **Stop** when every mandatory dimension is satisfied for in-scope code, unless review identifies an additional credible failure mode.

Heuristics:

- Same scenario **unit + integration** is justified when unit tests **policy** and integration tests **actual I/O** (e.g. retry wrapper + real HTTP stub).
- **One** E2E smoke for the main journey is often enough if integration tests cover branches.
- Regressions: add **one** targeted test that would have failed before the fix.

## Output template

Paste and fill. Keep rows few; split only when different layers or dimensions need separate proof.

```markdown
## Change under test
[1–2 sentences: what changed and the public surface]

## Risk summary
- [Bullet: risk → why it matters]

## Layer plan

| Test ID | Layer (unit / integration / E2E) | Dimension (happy / invalid / partial / timeout-null / drift-null) | What it proves | Why this layer (not higher/lower) |
|---------|-----------------------------------|-------------------------------------|------------------|-------------------------------------|
| T1 | | | | |
| T2 | | | | |

## Coverage check
- [ ] Happy path
- [ ] Invalid input
- [ ] Partial failure
- [ ] Timeout / retry (or N/A: ...)
- [ ] Data drift / null (or N/A: ...)

## Minimal set justification
[2–4 sentences: why fewer tests would miss a credible bug, why more would be redundant]

## Commands / locations (if known)
[e.g. `pytest path::test`, `npm test`, E2E job name]
```

## Examples (minimal)

**API change: new query param**

- Unit: invalid param values → 400; null/missing → default or 400 per spec.
- Integration: happy path + one partial failure (e.g. DB error → 503/structured error).
- E2E: optional single smoke if param is user-facing and untested elsewhere.

**Client retry on 503**

- Unit: retry count, backoff, idempotency key behavior with fake time.
- Integration: server returns 503 then 200; client ends in expected state.
- E2E: usually N/A unless only full browser reproduces bug.

## Additional resources

- For observable success and criterion-to-validation mapping, see [../implementation-done-criteria/SKILL.md](../implementation-done-criteria/SKILL.md).
- For impact and blast radius before planning tests, see [../pre-change-impact-analysis/SKILL.md](../pre-change-impact-analysis/SKILL.md).
