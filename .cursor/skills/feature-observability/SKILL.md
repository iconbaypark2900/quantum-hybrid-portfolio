---
name: feature-observability
description: Designs logs, metrics, traces, and correlation IDs for new features and complex workflows; maps events, state transitions, and failures; and makes post-deploy validation and troubleshooting practical. Use when adding features, multi-step workflows, async jobs, integrations, or when the user asks for observability, structured logging, debugging production issues, or runbooks.
---

# Feature observability

## At a glance (new features and complex workflows)

1. **Define** logs, metrics, and traces needed for debugging—before merge, not as an afterthought.
2. **Identify** important events, state transitions, and failure modes (what to count and what to alert on).
3. **Add** structured logs with correlation identifiers (`request_id`, `job_id`, `traceparent`, etc.) on critical paths.
4. **Make** post-deployment validation and troubleshooting easy: documented log queries, dashboards or alerts, and a short failure drill.

The sections below spell out how to do each step.

## When to apply

Use **during design** (before merge) for non-trivial features: async pipelines, external APIs, queues, multi-step UX, or anything where reproducing bugs from "it failed" alone is expensive. Pair with `implementation-done-criteria` (what to verify) and `feature-implementation-slice` (vertical slices).

**Out of scope:** generic logging style only—this skill ties observability to **events**, **correlation**, and **operability**.

## Workflow

### 1. Define logs, metrics, and traces

Answer these in one short design note (comment in ticket, PR description section, or ADR snippet—whatever the team uses):

| Signal | Purpose | Minimum questions |
|--------|---------|-------------------|
| **Logs** | Explain *why* a path ran and what decision was made | What human-readable story does an on-call need? |
| **Metrics** | Aggregate health, latency, volume, error rates | What SLO or threshold would catch regression early? |
| **Traces** | Tie sub-operations to one request/job | Which spans cross service/process boundaries? |

**Defaults**

- **Logs:** structured (key/value), stable field names, no secrets; include outcome (`success`, `error`, `skipped`) where applicable.
- **Metrics:** name + labels that stay low-cardinality (avoid raw IDs as label values); prefer histograms or summaries for latency where supported.
- **Traces:** one root span per user request or job; child spans for I/O and expensive computation.

### 2. Identify events, state transitions, and failures

Build an explicit **event list** for the feature:

| Event / transition | Trigger | Log level | Metric (optional) |
|--------------------|---------|-----------|-------------------|
| e.g. `job.accepted` | Valid enqueue | `info` | counter `jobs_enqueued` |
| e.g. `state.running → completed` | Terminal success | `info` | counter `jobs_completed` |
| e.g. `validation_failed` | Bad input | `warn` | counter `validation_errors` by `reason` |
| e.g. `dependency_timeout` | External SLA miss | `error` | counter + latency histogram |

**Failures:** for each failure mode, specify: **detected how** (exception, HTTP status, timeout), **logged fields** (error code/class, retryable or not), **user-visible behavior** (message vs generic), **metric** (so alerts can fire).

### 3. Structured logs and correlation identifiers

**Correlation**

- **HTTP APIs:** propagate `traceparent` / `tracestate` (W3C) or a single `X-Request-Id` / `request_id` from edge to services; log the same `request_id` on every log line for that request.
- **Background jobs:** generate `job_id` (and optionally `run_id`) at enqueue; pass through all workers; log on start, progress milestones, completion, failure.
- **Frontend:** generate or accept `correlation_id` for user actions that trigger backend work; include in API calls when the API supports it.

**Structured log fields (suggested)**

- `correlation_id` / `request_id` / `job_id` (pick one primary per flow)
- `feature` or `component` (stable string for filtering)
- `event` (from the event list)
- `duration_ms` where relevant
- `error.type` / `error.message` (sanitized) on failures

Avoid logging full payloads or PII; log identifiers and sizes if needed.

### 4. Validation and troubleshooting after deployment

Before calling the feature "done" from an ops perspective:

- [ ] **Query path:** document how to find one user's or one job's logs (e.g. "filter `job_id=` in …").
- [ ] **Dashboards / alerts:** at least one chart or alert tied to a **new** metric or error rate for this feature—or justify why existing service-level metrics suffice.
- [ ] **Synthetic or smoke:** if applicable, a minimal check that exercises the new path post-deploy.
- [ ] **Failure drill:** one paragraph: "If metric X spikes or log event Y appears, check Z first."

Keep the drill **actionable** (links to dashboards, log queries, runbooks)—not a generic "monitor logs."

## Checklist (copy for PRs)

```
Observability checklist
- [ ] Event list + failure modes documented
- [ ] Structured fields + correlation ID on critical paths
- [ ] Metrics or trace spans for latency/error boundaries
- [ ] Post-deploy: how to find traces/logs for one request/job
- [ ] Alert or dashboard hook, or explicit waiver
```

## Examples

**Good: one structured line**

```json
{"event":"portfolio.optimize.completed","request_id":"a1b2","feature":"optimizer","duration_ms":842,"status":"success","assets":12}
```

**Good: correlation across job steps**

```json
{"event":"pipeline.stage.end","job_id":"j-99","stage":"qubo","duration_ms":120,"status":"success"}
```

**Avoid:** unstructured prose only (`"Finished optimization successfully"`) with no ids—hard to correlate across services.

## Related skills

- `implementation-done-criteria` — maps requirements to tests and validation methods.
- `systematic-debugging` — when production behavior is already wrong and needs root cause.
- `change-validation-test-plan` — layered tests including integration and failure modes.
