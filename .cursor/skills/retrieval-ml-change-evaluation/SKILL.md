---
name: retrieval-ml-change-evaluation
description: Evaluates retrieval, RAG, ranking, or ML model changes by stating objectives and metrics, algorithms, data splits, baseline comparisons, failure modes, and a ship/iterate/reject recommendation. Use when reviewing retrieval or ML experiments, RAG pipeline changes, ranking updates, offline evaluations, A/B analysis, or when the user asks whether to adopt a proposed model or retrieval change.
---

# Retrieval and ML change evaluation

## When to apply

Use this workflow when comparing a **proposed** retrieval, embedding, reranker, generative, or other ML change against a **baseline**—including offline benchmarks, shadow traffic analysis, or small labeled slices. Use it before UI integration or production rollout when the change is non-trivial.

## Workflow

### 1. Task objective and evaluation metric

- **Objective**: One sentence on what the system should optimize (e.g. relevant passages found, user task success, latency-adjusted quality).
- **Primary metric**: The single number or rule used to decide success (e.g. nDCG@k, recall@k, MRR, calibrated Brier score, error rate on a holdout).
- **Secondary metrics**: Constraints or guardrails (latency p95, cost per query, toxicity rate).
- If multiple objectives conflict, state the **tradeoff order** explicitly.

### 2. Algorithm

- Name the **algorithm or pipeline stage** changed (e.g. dense retriever + cross-encoder rerank, new loss, new chunking).
- List **inputs** (queries, documents, features) and **outputs** (scores, ranks, spans) at the boundary of the change.
- Note **hyperparameters or config** that materially affect results (model id, top-k, temperature if relevant).

### 3. Data split or evaluation slice

- Specify **which data** was used: time range, domain, geography, language, or product area.
- State **split type**: train/validation/test, time-based split, or ad-hoc labeled slice; flag **leakage risks** (e.g. duplicate docs across splits, future data in training).
- Give **sample size** (queries, judgments, examples) and whether labels are **human**, synthetic, or proxy signals.

### 4. Baseline vs proposed

- Identify the **baseline** (current production, previous model, or strongest simple baseline).
- Report **comparative numbers** on the same slice for primary (and key secondary) metrics.
- Call out **statistical or practical significance** if applicable; if not computed, say so and rely on effect size and consistency across slices.

### 5. Failure modes

- List **where the proposed method fails** versus baseline: query types, long tail, OOD inputs, adversarial or ambiguous queries, low-resource languages, etc.
- Note **regressions** (metrics or qualitative) even if average metrics improve.
- Tie failures to **observable signals** (empty retrievals, wrong entity, hallucination when paired with gen, etc.).

### 6. Recommendation

Choose one and justify in 2–4 sentences:

| Decision | When |
|----------|------|
| **Ship** | Primary metric meets target on representative slice; guardrails OK; failure modes acceptable or mitigated. |
| **Iterate** | Direction promising but gaps on slice, variance, or failure modes; needs more data, tuning, or constraints before ship. |
| **Reject** | No meaningful gain, regressions on critical cases, or unacceptable cost/latency/risk versus baseline. |

## Output template

Use this structure in reviews, experiment notes, or PR descriptions:

```markdown
## Objective and metrics
- Objective: ...
- Primary: ...
- Secondary / guardrails: ...

## Algorithm
- Change: ...
- Inputs → outputs: ...
- Config (material): ...

## Data and split
- Slice: ...
- Split / leakage notes: ...
- N (queries / judgments): ...

## Results (baseline vs proposed)
| Metric | Baseline | Proposed | Notes |
|--------|----------|----------|-------|
| ... | ... | ... | ... |

## Failure modes
- ...

## Recommendation
**[ Ship | Iterate | Reject ]** — ...
```

## Consistency with project rules

Keep configs externalized; record **seeds**, dataset identifiers, and evaluation artifacts (paths or hashes) when the repo tracks experiments. Prefer **offline evaluation** before broad UI or production changes.
