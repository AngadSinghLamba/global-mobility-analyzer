# ADR-001: Modular Visa Subgraphs over Monolithic Pipeline

**Status**: Accepted | **Date**: 2026-03-07 | **Deciders**: Angad

## Context

The system must evaluate applicant eligibility across multiple visa categories (UK Skilled Worker, DE Opportunity Card, CA Express Entry). Each category has distinct scoring algorithms, document requirements, and threshold logic.

We considered three architectural approaches for structuring the LangGraph workflow.

## Decision

**Adopted Option B: Visa-Specific Compiled Subgraphs with Shared Corrective RAG.**

Each visa category is an isolated, compiled LangGraph subgraph. A Supervisor node routes user input to the correct subgraph based on `target_country`. All subgraphs share a common Corrective RAG pattern (Document Clerk → Grader → Legal Analyst) and a shared Report Generator downstream.

## Alternatives Considered

### Option A: Linear Pipeline with Conditional Retry
- Single monolithic graph handles all visa types
- Visa-specific logic embedded as conditional branches
- **Rejected**: Adding Sprint 2+ visas requires modifying the core graph. Untestable in isolation. Violates Open/Closed Principle.

### Option C: Full Autonomous Agent Swarm
- Legal Analyst agents autonomously decide when/how to query the Document Clerk
- Maximum flexibility and architectural impressiveness
- **Rejected**: Unpredictable token consumption (fatal for free-tier). Corrective loops may spiral. Harder to trace and debug. YAGNI.

## Trade-off Analysis

| Factor | A (Linear) | **B (Subgraphs)** | C (Swarm) |
|---|---|---|---|
| Complexity | Low | **Medium** | High |
| Extensibility | Poor | **Excellent** | Excellent |
| Testability | Good | **Excellent** | Poor |
| Token predictability | Good | **Good** | Unpredictable |
| Sprint 2+ cost | High | **Low** | Medium |

## Consequences

- **Positive**: Adding a new visa category = adding one new subgraph file. Zero changes to existing workflows. Each subgraph can be independently tested and evaluated.
- **Negative**: More boilerplate per subgraph. Requires understanding of LangGraph's compiled subgraph API.
- **Risk**: Low — LangGraph natively supports compiled subgraphs. Well-documented pattern.
