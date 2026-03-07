"""
Global Mobility Analyzer — Shared State Schema

Pydantic models defining the LangGraph state for the multi-agent
visa eligibility assessment system.

Architecture: Multi-Agent Supervisor with Agentic RAG (Option B — Visa-Specific Subgraphs)
Decision Log: See /docs/design.md for full rationale.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EducationLevel(str, Enum):
    """Standardised education tiers used across all visa scoring engines."""
    SECONDARY = "secondary"
    DIPLOMA = "diploma"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    DOCTORATE = "doctorate"


class TargetCountry(str, Enum):
    """Sprint 1 supported visa destinations."""
    UK = "UK"
    DE = "DE"
    CA = "CA"


class RelevanceClassification(str, Enum):
    """
    Three-way Grader output (Decision #6).

    - relevant:   Chunks directly answer the query.
    - irrelevant: Chunks miss the topic → triggers re-query (max 2 retries).
    - ambiguous:  Chunks are relevant but CONFLICTING → Legal Analyst
                  resolves by recency (latest date) and authority
                  (primary legislation > guidance notes > commentary).
    """
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    AMBIGUOUS = "ambiguous"


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class ApplicantProfile(BaseModel):
    """Applicant data submitted by the user. PII is scrubbed before LLM calls."""

    full_name: str = Field(..., description="Applicant's full legal name")
    nationality: str = Field(..., description="ISO 3166-1 alpha-2 country code (e.g. 'IN')")
    education_level: EducationLevel
    field_of_study: str = Field(..., description="Degree discipline, e.g. 'Computer Science'")
    years_of_experience: int = Field(..., ge=0, le=50)
    job_title: str = Field(..., description="Current or target role, e.g. 'Software Engineer'")
    offered_salary_gbp: Optional[float] = Field(None, description="Annual salary in GBP (UK workflow)")
    offered_salary_eur: Optional[float] = Field(None, description="Annual salary in EUR (DE workflow)")
    ielts_overall: Optional[float] = Field(None, ge=0.0, le=9.0, description="IELTS overall band score")
    ielts_scores: Optional[Dict[str, float]] = Field(
        None,
        description="IELTS component scores: {'listening': 7.0, 'reading': 6.5, ...}",
    )
    german_language_level: Optional[str] = Field(
        None,
        description="CEFR level (A1–C2) or None",
    )
    age: int = Field(..., ge=18, le=65)
    has_job_offer: bool = False
    has_canadian_pnp_nomination: bool = False
    spouse_education_level: Optional[EducationLevel] = None
    spouse_language_scores: Optional[Dict[str, float]] = None


# ---------------------------------------------------------------------------
# Retrieval & Grading Models
# ---------------------------------------------------------------------------

class DocumentChunk(BaseModel):
    """A single chunk retrieved from Azure AI Search."""

    chunk_id: str = Field(..., description="Unique chunk identifier in the index")
    source_url: str = Field(..., description="Original document URL (gov.uk, canada.ca, etc.)")
    source_title: str
    page_number: Optional[int] = None
    content: str = Field(..., description="Raw text content of the chunk")
    published_date: Optional[datetime] = Field(
        None,
        description="Publication/effective date — critical for ambiguity resolution",
    )
    authority_level: Literal["primary_legislation", "regulation", "guidance", "commentary"] = Field(
        "guidance",
        description="Source authority ranking for conflict resolution",
    )
    relevance_score: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Azure AI Search relevance score",
    )


class Citation(BaseModel):
    """Audit-trail citation linking a recommendation to its source."""

    source_url: str
    source_title: str
    page_number: Optional[int] = None
    chunk_id: str
    quote_excerpt: str = Field(..., description="Exact quote from the source supporting the claim")
    accessed_at: datetime = Field(default_factory=datetime.utcnow)


class GraderOutput(BaseModel):
    """
    Three-way relevance classification (Decision #6).

    When classification is 'ambiguous', conflicting_chunks captures the IDs
    of chunks that contradict each other. The Legal Analyst is then instructed
    to resolve by (1) most recent published_date and (2) highest authority_level.
    """

    relevance: RelevanceClassification
    score: float = Field(..., ge=0.0, le=1.0, description="Overall relevance confidence")
    conflicting_chunks: List[str] = Field(
        default_factory=list,
        description="Chunk IDs that contradict each other (populated when relevance='ambiguous')",
    )
    reasoning: str = Field(..., description="Grader's explanation for this classification")


# ---------------------------------------------------------------------------
# Analysis & Verification Models
# ---------------------------------------------------------------------------

class LegalAnalysisJSON(BaseModel):
    """
    Structured output from the Legal Analyst (Gemini 3).
    Consumed by the downstream Report Generator for Markdown rendering.
    """

    eligibility: Literal["eligible", "likely_eligible", "conditionally_eligible", "ineligible"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Step-by-step assessment rationale")
    points_breakdown: Optional[Dict[str, int]] = Field(
        None,
        description="Points scored per criterion (e.g. {'salary': 20, 'qualification': 10})",
    )
    total_points: Optional[int] = None
    threshold_points: Optional[int] = Field(None, description="Minimum required points")
    cited_sources: List[Citation] = Field(default_factory=list)
    missing_documents: List[str] = Field(
        default_factory=list,
        description="Documents the applicant still needs to provide",
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Potential issues (e.g. 'Salary below threshold by £2,300')",
    )
    ambiguity_resolution: Optional[str] = Field(
        None,
        description="Explanation if conflicting sources were resolved (Decision #6)",
    )


class VerificationResult(BaseModel):
    """
    Live portal verification output (Decision #7).

    The Stealth Verification Node checks volatile government data
    (CRS cut-offs, salary tables, Anabin status) against cached values.
    """

    data_point: str = Field(..., description="What was checked (e.g. 'UK General Salary Threshold')")
    live_value: str = Field(..., description="Current value from the government portal")
    cached_value: Optional[str] = Field(None, description="Previously cached value")
    source_url: str
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    stale_data_detected: bool = Field(
        False,
        description="True if live_value != cached_value → triggers re-indexing",
    )
    country: TargetCountry


# ---------------------------------------------------------------------------
# LangGraph State (TypedDict for graph compatibility)
# ---------------------------------------------------------------------------

class GraphState(TypedDict, total=False):
    """
    Central state object passed through all LangGraph nodes.

    Uses TypedDict (not Pydantic) for LangGraph compatibility.
    Individual fields hold Pydantic model instances for validation.
    """

    # --- Input ---
    applicant_profile: ApplicantProfile
    target_country: TargetCountry

    # --- Retrieval ---
    retrieved_chunks: List[DocumentChunk]
    search_query: str               # Current search query (may be refined in CRAG loop)
    original_query: str             # Original query for audit trail

    # --- Grading (Decision #6) ---
    grader_output: GraderOutput
    retry_count: int                # Max 2 retries before fallback

    # --- Analysis ---
    legal_analysis: LegalAnalysisJSON

    # --- Verification (Decision #7) ---
    verification_results: List[VerificationResult]

    # --- Output ---
    final_report: str               # Markdown report from Report Generator
    citations: List[Citation]       # Full audit trail

    # --- Metadata ---
    workflow_id: str                # Unique run identifier
    started_at: str                 # ISO timestamp
    completed_at: Optional[str]
