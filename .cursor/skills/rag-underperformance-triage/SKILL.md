---
name: rag-underperformance-triage
description: Diagnoses underperforming RAG systems by pipeline stage (ingestion through generation), classifies failures as recall, precision, grounding, or instruction-following, and proposes layer-appropriate fixes. Use when retrieval quality is poor, answers are wrong or ungrounded, chunking seems off, or the user asks how to debug or improve a RAG pipeline.
---

# RAG underperformance triage

## When to apply

Use when **observed quality is below expectations** and the cause is unclear: wrong facts, missing context, noisy passages, ignored instructions, or citations that do not support the answer. Pair with offline eval (labeled qrels, LLM-as-judge on slices) when possible; this skill structures **hypothesis → layer → fix**.

## 1. Separate issues by stage

Work **upstream to downstream**. A symptom often implicates multiple stages; list **primary suspect first**, then contributing factors.

| Stage | What it controls | Typical failure signals |
|--------|------------------|-------------------------|
| **Ingestion** | Source quality, normalization, dedup, access to raw content | Stale or wrong documents; missing PDFs/HTML; encoding or parse errors; duplicates skewing frequency |
| **Chunking** | Unit of retrieval, context boundaries | Answer split across chunks; tiny fragments lacking context; huge chunks diluting relevance |
| **Metadata** | Filters, facets, doc-level tags | Wrong corpus slice; date/topic filters excluding gold docs; language or ACL mismatches |
| **Embedding** | Semantic representation for dense retrieval | Correct doc exists but embedding space does not align query↔doc phrasing; domain or language mismatch |
| **Retrieval** | Candidate generation (BM25, dense, hybrid) | Relevant docs never appear in top-*k* (recall); too much junk in candidates (noise) |
| **Reranking** | Ordering within candidate set | Right doc in pool but not in top positions; relevant after rerank drops |
| **Generation** | Prompting, model, decoding | Unsupported claims; ignores constraints; good retrieval but bad synthesis |

**Rule:** If the **gold passage is not in the candidate set** at all, prioritize **ingestion → chunking → metadata → embedding → retrieval** before blaming reranking or generation.

## 2. Classify the failure type

Use **one primary label**; note a secondary if needed.

| Type | Definition | Quick test |
|------|------------|------------|
| **Recall** | Relevant evidence is absent from the **retrieved candidate set** (or not ingested/chunked). | Would the right unit of text be findable if retrieval were oracle-limited to a labeled gold doc? If gold is missing upstream, it is not yet a rerank issue. |
| **Precision** | Retrieved set contains **too much irrelevant** material; signal diluted. | Are top-*k* mostly off-topic or redundant even when something relevant exists? |
| **Grounding** | Final answer is **not supported** by retrieved (or cited) content; hallucination or overreach. | Strike retrieved passages: can a faithful answer still be given? If model invents facts, grounding is broken. |
| **Instruction-following** | Retrieval may be fine; output **violates format, scope, style, or constraints** (length, cite-what-you-use, no speculation). | Does a constrained prompt or schema fix it without changing retrieval? |

**Interaction:** Poor **recall** can force the generator to guess → looks like grounding failure; verify retrieval first.

## 3. Propose the most likely fix at the correct layer

Map **failure type → first-line lever** (then iterate).

### Recall failures

| Suspected cause | Layer | Likely fixes |
|-----------------|-------|----------------|
| Doc never in corpus | Ingestion | Fix crawlers, ACLs, formats; backfill sources |
| Relevant span not a retrievable unit | Chunking | Tune size/overlap; structure-aware (sections, tables); parent-child chunks |
| Wrong filter or routing | Metadata | Fix tags, language, date, tenant filters; routing/classification |
| Query–doc vocabulary/domain gap | Embedding | Domain adaptation, better model, query expansion, hybrid with lexical |
| Candidate pool too small or wrong index | Retrieval | Increase *k*, hybrid BM25+dense, better ANN params, decompose multi-hop |

### Precision failures

| Suspected cause | Layer | Likely fixes |
|-----------------|-------|----------------|
| Chunks too noisy or repetitive | Chunking | Smaller chunks, dedup, remove boilerplate |
| Lexical ambiguity | Retrieval + metadata | Filters, entity-aware retrieval, disambiguation |
| Ordering wrong but pool OK | Reranking | Cross-encoder, LLM rerank, feature-based rerank; dedup reranked list |
| Over-fetch | Retrieval | Tighten *k* before rerank; MMR diversity; confidence thresholds |

### Grounding failures

| Suspected cause | Layer | Likely fixes |
|-----------------|-------|----------------|
| Generator ignores passages | Generation | Stronger cite-only instructions, quote-then-answer, lower temperature, smaller context window with only top passages |
| Wrong passages highly ranked | Reranking + retrieval | Fix precision/recall first; constrain to cited spans |
| Chunks lack necessary nuance | Chunking | Passage granularity, metadata sidecars (title, section) |

### Instruction-following failures

| Suspected cause | Layer | Likely fixes |
|-----------------|-------|----------------|
| Format/structure wrong | Generation | System prompt, JSON/schema, few-shot, constrained decoding |
| Refusal/safety vs task | Generation | Policy clarity; distinguish from retrieval |
| Retrieval pulls misleading template-heavy docs | Chunking + retrieval | Down-rank generic boilerplate; style hints in metadata |

## Output template

Use this in tickets, PRs, or investigation notes:

```markdown
## Observed failure
- Example(s): ...
- User-visible symptom: ...

## Stage hypothesis (ordered)
1. [Stage]: evidence ...
2. [Stage]: ...

## Failure type
- Primary: recall | precision | grounding | instruction-following
- Evidence: ...

## Layer-targeted fix
- **Change:** ...
- **Why this layer:** ...
- **Validate with:** metric or slice (e.g. recall@k on labeled set, nDCG, groundedness checklist)

## If wrong, next hypothesis
- ...
```

## Principles

- **Isolate stages** with minimal experiments (e.g. oracle retrieval, swap reranker only on fixed candidates).
- **Do not tune generation** to compensate for systematic recall loss without ingestion/chunking/retrieval fixes.
- **Prefer measurable slices** (query sets, qrels) over one-off vibes; state uncertainty when data is missing.
