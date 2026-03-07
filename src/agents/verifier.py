"""
Global Mobility Analyzer — Stealth Verification Node (Decision #7)

Live-checks volatile government data against cached values using Playwright.
Detects stale data in the RAG knowledge base and flags it for re-indexing.

Architecture Note:
    This node runs AFTER the Legal Analyst produces its assessment.
    If stale_data_detected == True, the workflow can optionally trigger
    a re-query through the corrective RAG loop with updated data.

2026 Constants:
    All threshold values are sourced from official government portals
    as of March 7, 2026. The verification targets below encode the
    CSS selectors and URLs needed to check for updates.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.shared.state import TargetCountry, VerificationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 2026 Constants — Official thresholds (as of 2026-03-07)
# ---------------------------------------------------------------------------

# UK Skilled Worker Visa — effective March 26, 2026
UK_GENERAL_SALARY_THRESHOLD_GBP = 41_700      # Up from £38,700
UK_HOURLY_FLOOR_GBP = 17.13                    # Strict per-hour minimum
UK_SALARY_COMPLIANCE_RULE = "monthly"           # New: checks per pay period, not annual
UK_SALARY_COMPLIANCE_EFFECTIVE = "2026-03-26"

# Germany Opportunity Card (Chancenkarte) — 2026 update
DE_FINANCIAL_PROOF_EUR_YEAR = 13_092           # ~€1,091/month, up from €12,324
DE_FINANCIAL_PROOF_EUR_MONTH = 1_091
DE_POINTS_THRESHOLD = 6                        # Unchanged
DE_SHORTAGE_OCCUPATION_BONUS = 1               # Extra point for IT & Healthcare roles
DE_SHORTAGE_SECTORS = ["information_technology", "healthcare"]

# Canada Express Entry — Draw #402 (March 7, 2026)
CA_LATEST_DRAW_NUMBER = 402
CA_SENIOR_MANAGERS_CRS_CUTOFF = 429            # New "Senior Managers" category
CA_GENERAL_CEC_CRS_CUTOFF = 508               # General CEC draws
CA_LATEST_DRAW_DATE = "2026-03-07"
CA_LATEST_DRAW_CATEGORY = "Senior Managers"


# ---------------------------------------------------------------------------
# Verification Targets — What to check and where
# ---------------------------------------------------------------------------

@dataclass
class VerificationTarget:
    """
    A single data point to verify against a live government portal.

    Attributes:
        country: Which visa workflow this target belongs to.
        data_point: Human-readable name of what's being checked.
        url: Government portal URL to scrape.
        css_selector: CSS selector to extract the live value.
        cached_value: The value currently in our knowledge base.
        description: What this data point means for eligibility.
    """

    country: TargetCountry
    data_point: str
    url: str
    css_selector: str
    cached_value: str
    description: str


# Pre-configured verification targets for Sprint 1 workflows
VERIFICATION_TARGETS: list[VerificationTarget] = [
    # --- UK Skilled Worker ---
    VerificationTarget(
        country=TargetCountry.UK,
        data_point="UK General Salary Threshold",
        url="https://www.gov.uk/skilled-worker-visa/your-job",
        css_selector="table.salary-thresholds td:nth-child(2)",
        cached_value=f"£{UK_GENERAL_SALARY_THRESHOLD_GBP:,}",
        description=(
            "General salary threshold for Skilled Worker visa. "
            f"Current: £{UK_GENERAL_SALARY_THRESHOLD_GBP:,}/year, "
            f"with a strict £{UK_HOURLY_FLOOR_GBP}/hour floor. "
            f"New salary compliance rule (effective {UK_SALARY_COMPLIANCE_EFFECTIVE}): "
            f"checks per {UK_SALARY_COMPLIANCE_RULE} pay period, not annually."
        ),
    ),
    VerificationTarget(
        country=TargetCountry.UK,
        data_point="UK Shortage Occupation List",
        url="https://www.gov.uk/government/publications/skilled-worker-visa-shortage-occupations",
        css_selector="div.govuk-govspeak table",
        cached_value="SOL v2026.1",
        description="Shortage Occupation List — roles on this list qualify for reduced salary thresholds.",
    ),

    # --- Germany Opportunity Card ---
    VerificationTarget(
        country=TargetCountry.DE,
        data_point="DE Financial Proof Requirement",
        url="https://www.make-it-in-germany.com/en/visa-residence/types/chance-card",
        css_selector="div.content-main p",
        cached_value=f"€{DE_FINANCIAL_PROOF_EUR_YEAR:,}/year",
        description=(
            f"Self-subsistence proof for Chancenkarte: €{DE_FINANCIAL_PROOF_EUR_YEAR:,}/year "
            f"(~€{DE_FINANCIAL_PROOF_EUR_MONTH:,}/month). "
            f"Points threshold: {DE_POINTS_THRESHOLD}. "
            f"Shortage occupation bonus (+{DE_SHORTAGE_OCCUPATION_BONUS} point) for: "
            f"{', '.join(s.replace('_', ' ').title() for s in DE_SHORTAGE_SECTORS)}."
        ),
    ),
    VerificationTarget(
        country=TargetCountry.DE,
        data_point="DE Anabin Database Status",
        url="https://anabin.kmk.org/anabin.html",
        css_selector="div#search-results",
        cached_value="Anabin DB online",
        description="Anabin foreign degree recognition database availability and latest update status.",
    ),

    # --- Canada Express Entry ---
    VerificationTarget(
        country=TargetCountry.CA,
        data_point="CA Latest Express Entry Draw CRS Cutoff",
        url="https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/submit-profile/rounds-invitations.html",
        css_selector="table.table tbody tr:first-child",
        cached_value=(
            f"Draw #{CA_LATEST_DRAW_NUMBER} ({CA_LATEST_DRAW_DATE}): "
            f"{CA_LATEST_DRAW_CATEGORY} cutoff {CA_SENIOR_MANAGERS_CRS_CUTOFF}"
        ),
        description=(
            f"Latest Express Entry draw. Draw #{CA_LATEST_DRAW_NUMBER} introduced "
            f"'{CA_LATEST_DRAW_CATEGORY}' category with CRS cutoff of "
            f"{CA_SENIOR_MANAGERS_CRS_CUTOFF}. General CEC draws: ~{CA_GENERAL_CEC_CRS_CUTOFF}."
        ),
    ),
    VerificationTarget(
        country=TargetCountry.CA,
        data_point="CA NOC TEER Categories",
        url="https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/find-national-occupation-code.html",
        css_selector="div.mwsgeneric-base-html table",
        cached_value="NOC 2021 v1.0 — TEER 0-5",
        description="National Occupation Classification TEER categories for FSW eligibility.",
    ),
]


# ---------------------------------------------------------------------------
# Cache Layer — SQLite-backed for free-tier cost savings
# ---------------------------------------------------------------------------

CACHE_DIR = Path(__file__).parent.parent.parent / ".cache" / "verification"


def _cache_key(target: VerificationTarget) -> str:
    """Generate a deterministic cache key for a verification target."""
    raw = f"{target.country}:{target.data_point}:{target.url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_cached_result(target: VerificationTarget) -> Optional[VerificationResult]:
    """
    Retrieve a cached verification result if available and fresh (< 24 hours).
    Returns None if no cache exists or cache is stale.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_cache_key(target)}.json"

    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text())
        result = VerificationResult(**data)
        age_hours = (datetime.utcnow() - result.checked_at).total_seconds() / 3600
        if age_hours > 24:
            logger.info(
                "Cache expired for %s (%.1f hours old)", target.data_point, age_hours
            )
            return None
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt cache for %s: %s", target.data_point, exc)
        return None


def save_cached_result(target: VerificationTarget, result: VerificationResult) -> None:
    """Persist a verification result to the local cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{_cache_key(target)}.json"
    cache_file.write_text(result.model_dump_json(indent=2))
    logger.info("Cached verification result for %s", target.data_point)


# ---------------------------------------------------------------------------
# Verification Functions — Playwright Integration Point
# ---------------------------------------------------------------------------

async def verify_live_data(target: VerificationTarget) -> VerificationResult:
    """
    Check a live government portal for the current value of a data point.

    Uses Playwright with stealth plugins to avoid bot detection on
    government websites. Falls back to cached data on failure.

    TODO (Sprint 1):
        - Integrate playwright-extra with stealth plugin
        - Add retry logic with exponential backoff
        - Implement per-country rate limiting

    Args:
        target: The verification target to check.

    Returns:
        VerificationResult with live_value and stale_data_detected flag.
    """
    # Check cache first — saves browser launches on free tier
    cached = get_cached_result(target)
    if cached is not None:
        logger.info("Using cached result for %s", target.data_point)
        return cached

    # --- Playwright stub ---
    # In production, this will:
    # 1. Launch a stealth browser (playwright-extra)
    # 2. Navigate to target.url
    # 3. Extract text from target.css_selector
    # 4. Compare with target.cached_value
    # 5. Return VerificationResult
    #
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch(headless=True)
    #     context = await browser.new_context()
    #     page = await context.new_page()
    #     await page.goto(target.url, wait_until="networkidle")
    #     element = await page.query_selector(target.css_selector)
    #     live_value = await element.inner_text() if element else "SELECTOR_NOT_FOUND"
    #     await browser.close()

    logger.warning(
        "Playwright not yet integrated — returning cached value for %s",
        target.data_point,
    )

    result = VerificationResult(
        data_point=target.data_point,
        live_value=target.cached_value,  # Stub: returns cached as if it were live
        cached_value=target.cached_value,
        source_url=target.url,
        stale_data_detected=False,
        country=target.country,
    )

    save_cached_result(target, result)
    return result


def compare_with_cached(
    live_value: str,
    cached_value: str,
) -> bool:
    """
    Detect whether the live value differs from the cached value.

    Uses normalised string comparison (strip, lowercase) to avoid
    false positives from whitespace or casing differences.

    Returns:
        True if stale data is detected (values differ).
    """
    normalise = lambda s: s.strip().lower().replace(",", "").replace(" ", "")
    return normalise(live_value) != normalise(cached_value)


async def verify_all_for_country(country: TargetCountry) -> list[VerificationResult]:
    """
    Run all verification targets for a given country.

    Called by the Verification Node in each visa subgraph.

    Args:
        country: Which country's targets to verify.

    Returns:
        List of VerificationResult objects.
    """
    targets = [t for t in VERIFICATION_TARGETS if t.country == country]
    results: list[VerificationResult] = []

    for target in targets:
        result = await verify_live_data(target)
        results.append(result)

        if result.stale_data_detected:
            logger.warning(
                "⚠️  STALE DATA DETECTED for %s: cached='%s', live='%s'",
                target.data_point,
                result.cached_value,
                result.live_value,
            )

    return results
