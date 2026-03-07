# ADR-003: Stealth Browser Verification for Government Portal Checks

**Status**: Accepted | **Date**: 2026-03-07 | **Deciders**: Angad

## Context

Immigration law contains **volatile data points** that change without notice:
- UK Skilled Worker salary thresholds (changed March 2026)
- Canada Express Entry CRS cutoffs (change every 2 weeks per draw)
- Germany Anabin database status (degree recognition lookups)

A RAG knowledge base indexed last week may contain stale data. The system needs a mechanism to detect when cached legal data no longer matches the live government portal.

## Decision

**Adopted a Stealth Verification Node using Playwright with anti-bot-detection plugins.**

A dedicated Verification Node runs *after* the Legal Analyst produces its assessment. It checks a curated list of government portal data points against cached values. If discrepancies are found, `stale_data_detected = True` is set, which can trigger re-indexing.

## Why Stealth?

Government portals employ bot detection:

| Portal | Bot Detection | Consequence |
|---|---|---|
| gov.uk | Cloudflare, rate limiting | 403 after ~50 requests/hour |
| canada.ca | AWS WAF, CAPTCHA on suspicious patterns | Blocked IP |
| make-it-in-germany.com | Basic Cloudflare | 429 rate limit |
| anabin.kmk.org | Session-based, JavaScript rendering | Empty page without JS |

Standard HTTP requests (`requests`, `httpx`) fail silently — they return HTML with CAPTCHA challenges, not the actual data. Playwright with stealth plugins renders JavaScript, handles cookies, and mimics human browsing patterns.

## Why Not APIs?

- **gov.uk**: No public API for salary threshold tables.
- **canada.ca**: Express Entry draw results are published as HTML tables, not API endpoints. IRCC provides no structured API.
- **anabin.kmk.org**: No API. JavaScript-rendered SPA requires a full browser.

If these governments provided APIs, we would use them. They don't. Stealth browser scraping is the only viable approach for live verification.

## Cost Mitigation

Browser launches are expensive. On free tier, we mitigate with:
- **24-hour local cache**: Results are cached in SQLite. Same check within 24 hours returns cached value — no browser launch.
- **Lazy verification**: Only runs *after* the Legal Analyst has already produced its assessment. The report is still usable even if verification is skipped.
- **Rate limiting**: Maximum 1 browser launch per target per 24 hours.

## Consequences

- **Positive**: Detects stale data that would otherwise cause incorrect eligibility assessments. Provides a measurable "freshness" metric for the knowledge base.
- **Negative**: Adds ~5–10 seconds per assessment if cache is cold. Playwright dependency increases container size.
- **Risk**: Government portals change their HTML structure. Mitigated by CSS selector failures being caught and logged, not crashing the workflow.
