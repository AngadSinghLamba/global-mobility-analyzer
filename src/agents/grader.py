"""
Global Mobility Analyzer — Grader Agent (Decision #6)

Three-way relevance classification:
- relevant:   Chunks directly answer the query → pass to Legal Analyst.
- irrelevant: Chunks miss the topic → re-query (max 2 retries).
- ambiguous:  Chunks are relevant but CONFLICTING → pass to Legal Analyst
              with conflicting_chunks list for recency/authority resolution.
"""

from __future__ import annotations

import logging

from src.shared.state import (
    GraderOutput,
    GraphState,
    RelevanceClassification,
)

logger = logging.getLogger(__name__)

# Threshold for the 3-way classification
RELEVANCE_THRESHOLD = 0.7
MAX_RETRIES = 2


def grade_retrieval(state: GraphState) -> dict:
    """
    Grade retrieved chunks for relevance, triggering the CRAG loop.

    Conditional edge logic:
        - "irrelevant" + retry_count < 2  → Re-Query node
        - "irrelevant" + retry_count >= 2 → Legal Analyst (low-confidence)
        - "ambiguous"                     → Legal Analyst (with conflicting_chunks)
        - "relevant"                      → Legal Analyst (standard path)

    TODO (Sprint 1):
        - Implement LLM-based grading (Gemini 3 or lightweight model)
        - Add conflict detection logic (compare dates, detect contradictions)
    """
    chunks = state.get("retrieved_chunks", [])
    retry_count = state.get("retry_count", 0)

    logger.info("Grading %d chunks (retry %d/%d)", len(chunks), retry_count, MAX_RETRIES)

    # Stub: Return a default grading
    return {
        "grader_output": GraderOutput(
            relevance=RelevanceClassification.RELEVANT,
            score=0.0,
            conflicting_chunks=[],
            reasoning="Placeholder — grading logic pending.",
        ),
    }


def should_retry(state: GraphState) -> str:
    """
    Conditional edge function: decide next node after grading.

    Returns:
        "re_query" | "legal_analyst" based on grader output and retry count.
    """
    grader = state.get("grader_output")
    retry_count = state.get("retry_count", 0)

    if grader is None:
        return "legal_analyst"

    if grader.relevance == RelevanceClassification.IRRELEVANT:
        if retry_count < MAX_RETRIES:
            logger.info("Re-querying (attempt %d/%d)", retry_count + 1, MAX_RETRIES)
            return "re_query"
        else:
            logger.warning("Max retries reached — proceeding with low confidence")
            return "legal_analyst"

    # Both "relevant" and "ambiguous" proceed to Legal Analyst
    if grader.relevance == RelevanceClassification.AMBIGUOUS:
        logger.info(
            "Ambiguous grading — %d conflicting chunks forwarded",
            len(grader.conflicting_chunks),
        )

    return "legal_analyst"
