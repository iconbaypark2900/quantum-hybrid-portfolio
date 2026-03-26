---
name: experiment-proposal
description: Structures ML, retrieval, optimization, and simulation experiments with hypothesis, baseline, change description, data/evaluation plan, success criteria, and required artifacts (config, metrics, plots, logs). Use when proposing a new experiment, scoping an A/B or offline eval, writing an experiment plan, or before implementing model or algorithm changes.
---

# Experiment proposal

## When to apply

Use when **designing** an experiment—not only after results exist. Complements [retrieval-ml-change-evaluation](../retrieval-ml-change-evaluation/SKILL.md), which focuses on **comparing outcomes** once numbers exist.

## Required sections (in order)

Answer each section in plain language; skip none unless the user explicitly narrows scope.

### 1. Hypothesis

- One or two sentences: **what you believe will improve** and **why** (mechanism or intuition).
- If there is no causal claim, state that the run is **exploratory** and what question it answers.

### 2. Baseline

- What counts as **baseline**: current production, previous checkpoint, strongest simple baseline, or random/control.
- **Frozen details** that must match when comparing: code revision, config snapshot, seed policy, hardware or simulator settings.

### 3. Algorithm or model change

- **What changes** (single variable or small bundle); name the algorithm, model, loss, feature, or pipeline stage.
- **Everything held constant** that could otherwise explain a difference.

### 4. Dataset, slice, and evaluation procedure

- **Data**: source, time range, domain, filters, and **train/val/test or eval slice** definition.
- **Procedure**: how metrics are computed (code path, aggregation, number of runs), and **leakage or overlap** risks to call out.
- **Sample size** or compute budget if relevant.

### 5. Success and failure thresholds

- **Success**: quantitative or qualitative criteria that justify adopting the change (primary threshold; optional secondary).
- **Failure**: conditions that stop the experiment early or reject the change (regression limits, instability, cost ceiling).
- If thresholds are tentative, say so and what would **recalibrate** them.

### 6. Artifacts to save

Plan outputs so runs are **reproducible and comparable**:

| Artifact | What to capture |
|----------|-----------------|
| **Config** | Full experiment config: hyperparameters, model ids, seeds, paths, environment or dependency pins as used. |
| **Metrics** | Raw and aggregated metrics in machine-readable form (JSON/CSV); version or hash of eval code. |
| **Plots / tables** | Figures or tables for the primary comparison; caption what each axis or column represents. |
| **Logs** | Structured or text logs for training, inference, or job orchestration; correlation or run id if applicable. |

Prefer **deterministic configs** and **explicit seeds** where the stack allows.

## Output template

Use this in docs, tickets, or PR bodies when proposing work:

```markdown
## Hypothesis
...

## Baseline
...

## Change (algorithm / model)
...

## Data, slice, evaluation
...

## Success / failure thresholds
- Success: ...
- Failure / stop: ...

## Artifacts
- Config: ...
- Metrics: ...
- Plots/tables: ...
- Logs: ...
```

## Checklist

- [ ] Hypothesis stated (or marked exploratory)
- [ ] Baseline identified and comparable
- [ ] Change isolated from confounders
- [ ] Data/slice/procedure explicit
- [ ] Success and failure thresholds defined
- [ ] Artifact locations and formats chosen
