---
name: feature-request-to-spec
description: Converts informal feature requests into precise engineering tasks with inputs, outputs, users, interfaces, success criteria, core vs stretch scope, smallest proof slice, and testable acceptance criteria before coding. Use when scoping a new feature, clarifying a ticket, writing a spec before implementation, or when the user asks to turn a request into an engineering plan.
---

# Feature request → engineering spec

## When to apply

Use **before** implementation when the starting point is a goal, idea, or ticket—not yet a buildable task. For coding the slice after the spec exists, use [feature-implementation-slice](../feature-implementation-slice/SKILL.md).

## Workflow

### 1. Precise engineering task

Restate the request as **one sentence** that names the behavior change and the system boundary (e.g. API, UI surface, job). Avoid solution jargon unless the user required a specific technology.

- **In scope**: what must change.
- **Out of scope**: what is explicitly not part of this task.

### 2. Inputs, outputs, users, interfaces, success criteria

| Dimension | What to capture |
|-----------|-----------------|
| **Users / actors** | Who triggers it; roles or permissions if relevant. |
| **Inputs** | Data, events, config, env; validation and defaults. |
| **Outputs** | Responses, side effects, persisted state, notifications. |
| **Interfaces** | HTTP routes, CLI, events, UI screens/components, file formats—only what this feature touches. |
| **Success criteria** | Observable outcomes (latency, correctness, UX), not internal implementation details. |

### 3. Core vs stretch

- **Core**: required for the feature to be considered “done” for this task.
- **Stretch**: valuable but deferrable; must not block shipping the core.

If the request mixes several features, split into separate tasks or mark secondary items as stretch.

### 4. Smallest vertical slice

Define the **narrowest end-to-end path** that proves the feature works (e.g. one API + one consumer path, or one UI flow + backing call). State what is intentionally **not** built in the slice.

### 5. Acceptance criteria (before implementation)

Write **testable** criteria the implementer can verify:

- Use **Given / When / Then** or numbered checks that avoid ambiguity.
- Include negative cases and error behavior where they matter.
- Separate **core** acceptance from **stretch** acceptance if stretch remains in scope.

## Output template

Produce the spec in this structure (copy and fill):

```markdown
## Engineering task (one sentence)
[...]

## In scope / out of scope
- **In scope:** ...
- **Out of scope:** ...

## Actors and users
- ...

## Inputs
- ...

## Outputs
- ...

## Interfaces touched
- ...

## Success criteria (product/system)
- ...

## Core vs stretch
| Core | Stretch |
|------|---------|
| ... | ... |

## Smallest vertical slice
- **Slice:** ...
- **Proves:** ...
- **Explicitly deferred:** ...

## Acceptance criteria (pre-implementation)
### Core
1. ...
### Stretch (if any)
1. ...

## Open questions / assumptions
- ...
```

## Handoff

After the user confirms the spec, implementation follows [feature-implementation-slice](../feature-implementation-slice/SKILL.md) using this doc as the source of scope and acceptance criteria.
