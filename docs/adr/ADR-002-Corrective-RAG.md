# ADR-002: Corrective RAG over Simple RAG for Legal Compliance

**Status**: Accepted | **Date**: 2026-03-07 | **Deciders**: Angad

## Context

Immigration law has a unique quality problem: documents are **authoritative but contradictory**. The UK Skilled Worker salary threshold changed from £38,700 to £41,700 in early 2026, but older guidance documents still exist in government archives. A simple RAG pipeline retrieves chunks without questioning their relevance or consistency — unacceptable for legal advisory.

## Decision

**Adopted Corrective RAG (CRAG) with a 3-way Grader classification.**

Every retrieval pass is followed by a Grader node that classifies chunks as `relevant`, `irrelevant`, or `ambiguous`. Irrelevant results trigger re-query (max 2 retries). Ambiguous results — where chunks are relevant but contradictory — forward `conflicting_chunks` to the Legal Analyst with explicit instructions to resolve by recency and source authority.

## Why Not Simple RAG?

| Scenario | Simple RAG | CRAG |
|---|---|---|
| Outdated salary threshold retrieved | Silently uses wrong value | Grader detects low relevance → re-query |
| Two conflicting rules from different dates | LLM picks arbitrarily | Grader flags "ambiguous" → Legal Analyst resolves by date |
| Retrieval misses the topic entirely | LLM hallucinates an answer | Grader scores "irrelevant" → refines query |
| All chunks are high quality | Works fine | Works fine (no overhead — passes through) |

## The 3-Way Classification (Decision #6)

```
GraderOutput:
  relevance: "relevant" | "irrelevant" | "ambiguous"
  score: 0.0–1.0
  conflicting_chunks: [chunk_ids]  # populated when "ambiguous"
  reasoning: str
```

**Routing logic:**
- `irrelevant` + retry < 2 → Re-query with refined search terms
- `irrelevant` + retry ≥ 2 → Legal Analyst with low-confidence flag
- `ambiguous` → Legal Analyst resolves by: (1) most recent `published_date`, (2) highest `authority_level` (primary_legislation > regulation > guidance > commentary)
- `relevant` → Legal Analyst standard path

## Consequences

- **Positive**: Eliminates the most dangerous failure mode in legal AI — confidently citing outdated or contradictory law. The ambiguity flag creates an explicit audit trail for conflict resolution.
- **Negative**: Adds 1–2 extra LLM calls per assessment when retrieval quality is low. Mitigated by aggressive caching.
- **Risk**: Quality of the Grader itself. Mitigated by behavioral contract testing (must flag known contradictions in eval dataset).
