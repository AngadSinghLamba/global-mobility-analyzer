"""
Global Mobility Analyzer — Legal Analyst Agent

Powered by Google Gemini 3 via Google AI Studio free tier.
Evaluates retrieved immigration law chunks and produces a structured
eligibility assessment (LegalAnalysisJSON).

Architecture: Decision #2 — Outputs structured JSON; Report Generator
              handles Markdown rendering downstream.
"""

from __future__ import annotations

import logging

from src.shared.state import GraphState, LegalAnalysisJSON

logger = logging.getLogger(__name__)


async def analyse_eligibility(state: GraphState) -> dict:
    """
    Evaluate applicant eligibility against retrieved legal chunks.

    If grader_output.relevance == 'ambiguous', the prompt instructs Gemini
    to resolve conflicting sources by:
    1. Most recent published_date
    2. Highest authority_level (primary_legislation > regulation > guidance)

    TODO (Sprint 1):
        - Integrate google-genai SDK (Gemini 3)
        - Build visa-specific prompt templates (UK/DE/CA)
        - Implement structured output parsing with Pydantic
        - Add cost-saving cache (hash profile + chunks → cache response)
    """
    country = state.get("target_country")
    chunks = state.get("retrieved_chunks", [])
    grader = state.get("grader_output")

    logger.info(
        "Legal Analyst evaluating %d chunks for %s (grader: %s)",
        len(chunks),
        country,
        grader.relevance if grader else "N/A",
    )

    # Stub: Return a placeholder analysis
    return {
        "legal_analysis": LegalAnalysisJSON(
            eligibility="conditionally_eligible",
            confidence=0.0,
            reasoning="Placeholder — Gemini 3 integration pending.",
            cited_sources=[],
            missing_documents=["Integration pending"],
            risk_factors=["LLM not yet connected"],
        ),
    }
