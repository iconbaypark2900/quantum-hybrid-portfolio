---
name: boundary-data-contracts
description: Traces producer and consumer across module boundaries; validates schema, types, nullability, defaults, and field naming; flags versioning and backward-compatibility risks; surfaces ambiguous fields and hidden assumptions; recommends explicit contracts (types, schemas, adapters). Use when data crosses packages, layers, services, APIs, queues, or persistence; when reviewing DTOs, serializers, or refactors; or when the user asks about cross-module contracts, breaking changes, or data-shape safety.
---

# Boundary data contracts

## When to apply

Use when **data leaves one module and enters another** (imports between packages, service calls, HTTP/JSON, gRPC, events, DB rows, file formats, UI props fed by API clients). Skip for purely local structs used only inside one file unless preparing to extract them.

**Pairs well with:** [pre-change-impact-analysis](../pre-change-impact-analysis/SKILL.md) (blast radius), [refactoring-preserve-behavior](../refactoring-preserve-behavior/SKILL.md) (behavior-preserving edits).

## Workflow (order matters)

### 1. Producer and consumer

- **Producer:** module/function that **constructs, maps, or serializes** the payload (source of truth for intent).
- **Consumer:** module that **reads, deserializes, or pattern-matches** the payload (source of truth for usage).
- If multiple producers or consumers exist, list each and note **which pair** is in scope for the change.
- Name the **boundary kind**: in-process call, network (sync/async), persistence replay, batch job, etc.

### 2. Shape and semantics

Check the **contract as the consumer actually uses it** (not only what the producer intends):

| Check | Questions |
|-------|-----------|
| **Schema / structure** | Fixed keys vs extensible maps? Nested objects vs flat? Arrays vs single values? |
| **Types** | String vs number vs enum? Date as ISO string, epoch ms, or object? Units (basis points vs percent)? |
| **Nullability** | Optional vs required? Missing key vs explicit `null`? Empty string vs null? |
| **Defaults** | Who applies defaults—producer, consumer, or middleware? Documented? |
| **Naming** | Same casing and spelling on both sides? Renamed in one layer only (alias drift)? |

Flag **any field** the consumer reads that the producer does not clearly set, and vice versa.

### 3. Versioning and compatibility

- **Direction of change:** who deploys first—producer, consumer, or both?
- **Additive vs breaking:** new optional fields (usually safe) vs renamed/removed/required fields (breaking unless versioned).
- **Persistence:** old rows/events still decoded? Migration or dual-read period needed?
- **If versioning exists:** version numbers, content negotiation, or schema registry—verify they match reality in code paths.
- If no formal versioning: state **compatibility rule** (e.g. “consumers must ignore unknown keys”) and whether code follows it.

### 4. Ambiguity and hidden assumptions

Call out explicitly:

- **Ambiguous fields:** names that could mean multiple things (`id`, `type`, `status`, `value`, `data`).
- **Implicit coupling:** ordering assumptions, timezone, locale, “truth” when two fields disagree.
- **Silent coercion:** truthy/falsy, `parseInt`, float rounding, enum fallback to default.
- **Partial updates:** PATCH semantics vs replace—which fields mean “leave unchanged”?
- **Error shape:** does the consumer handle the producer’s error format?

### 5. Recommend explicit contracts

Prefer **one** primary recommendation per gap:

- **Shared type or schema** in a neutral module (OpenAPI/Pydantic/TypeScript types/protobuf), generated or hand-maintained but **single source of truth**.
- **Validation at the boundary:** assert or parse on ingress in the consumer; fail fast with actionable messages.
- **Adapter layer:** map external/raw shapes to internal domain models at the edge; keep core logic free of wire formats.
- **Documentation:** table of fields with type, nullability, default, and version introduced—when types alone are insufficient.

Avoid vague advice (“be careful”); tie each recommendation to a **specific field or boundary** identified above.

## Output format

Structure findings so they are easy to scan in PR review:

```markdown
## Boundary: [producer] → [consumer] ([boundary kind])

### Endpoints
- Producer: `path:line` or symbol
- Consumer: `path:line` or symbol

### Contract table
| Field | Producer sets? | Consumer expects | Type / null / default | Notes |
|-------|----------------|------------------|------------------------|-------|

### Compatibility
- Risk: [none | additive | breaking]
- Versioning: [what exists / gap]

### Issues
- [Ambiguity / assumption / drift] — evidence — severity

### Recommendations
1. [Concrete next step tied to boundary]
```

## Checklist

```
- [ ] Producer and consumer named; boundary kind stated
- [ ] Schema, types, nullability, defaults, naming reviewed for drift
- [ ] Versioning / deploy order / persistence replay considered or marked N/A
- [ ] Ambiguous fields and hidden assumptions listed with evidence
- [ ] Explicit contract recommendation(s) tied to specific gaps
```
