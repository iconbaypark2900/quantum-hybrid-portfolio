---
name: completion-readiness-checklist
description: Verifies correctness, tests, config/env, observability, docs/run instructions, rollback/failure containment, and residual risks before declaring work complete. Use before closing a task or PR, when the user asks if work is ready to ship, or for a definition-of-done / finish-line review.
---

# Completion readiness checklist

## When to apply

Run **before** telling the user work is complete, merging risky changes, or closing a ticket. Complements [implementation-done-criteria](../implementation-done-criteria/SKILL.md) (which defines *what* to validate); this skill is the **execution gate** for *whether* validation and operational readiness are satisfied.

If any step fails, fix or explicitly document waiver + follow-up before calling the work done.

---

## 1. Correctness

- **Logic**: Changed code paths match intended behavior; edge cases (null, empty, limits) handled where they matter.
- **Contracts**: Request/response shapes, types, and error codes remain consistent with callers and docs unless the change intentionally versions them.
- **Data**: Migrations or transforms are safe; no silent data loss; idempotency where retries exist.

State **pass / fail / N/A** and point to evidence (test name, manual repro, or file:line).

---

## 2. Test coverage for changed behavior

- New or modified behavior has **automated** coverage where stable (unit/integration); manual/UI only where appropriate.
- At least one test fails if the fix/feature is reverted (guards regressions).
- Existing tests updated when behavior intentionally changes; flaky tests not ignored without a tracked follow-up.

Cross-check with [change-validation-test-plan](../change-validation-test-plan/SKILL.md) for layer-appropriate tests.

---

## 3. Config and environment changes

- **New or renamed** env vars, flags, defaults, or secrets are reflected in `.env.example` (or project equivalent) and documented.
- **Breaking** config changes have migration notes or backward-compatible period.
- Production vs dev assumptions are explicit (URLs, keys, feature flags).

---

## 4. Logging and observability

- Errors and important state transitions are **visible** at appropriate level (not only `debug` for operator-critical failures).
- Logs/traces/metrics include enough context to debug (request/job id, user-safe identifiers, not secrets).
- New failure modes or external calls have a discoverable signal (log line, metric, or health check) where ops care.

See [feature-observability](../feature-observability/SKILL.md) for structured logging patterns.

---

## 5. Docs, README, and run instructions

- **How to run** and **how to test** still work for this repo (commands, ports, prerequisites).
- User-facing or API changes appear in README, OpenAPI, or changelog as the project expects.
- Removed features are removed from docs, not left stale.

---

## 6. Rollback and failure containment

- **Rollback**: How to revert (git revert, flag off, config flip); DB migrations reversible or paired with safe forward-only plan.
- **Blast radius**: Feature flags, timeouts, circuit breakers, or graceful degradation where partial failure could harm users or data.
- **Side effects**: Long jobs, payments, or external writes—confirm idempotency or compensation where needed.

---

## 7. Residual risks

After steps 1–6, summarize in **2–5 bullets**:

- What was **not** verified (environment, hardware, load, security review).
- Known **limitations** or **tech debt** introduced.
- **Monitoring** or **follow-up** items (tickets, dashboards).

Do not claim "zero risk"; state **residual risk** honestly.

---

## Output template

Paste and fill before declaring completion:

```markdown
## Completion readiness

| Step | Status (pass / fail / N/A) | Notes |
|------|----------------------------|-------|
| 1. Correctness | | |
| 2. Test coverage | | |
| 3. Config / env | | |
| 4. Observability | | |
| 5. Docs / run instructions | | |
| 6. Rollback / containment | | |

## Residual risks
- ...
```

---

## Related skills

- [implementation-done-criteria](../implementation-done-criteria/SKILL.md) — define acceptance criteria and validation mapping up front.
- [change-validation-test-plan](../change-validation-test-plan/SKILL.md) — scope tests by layer and risk.
- [feature-observability](../feature-observability/SKILL.md) — logs, metrics, traces for new workflows.
