# Product Requirements Document — Global Mobility Application Analyzer

**Version**: 1.0 | **Date**: 2026-03-07 | **Author**: Angad | **Status**: Active

---

## Problem Statement

Immigration application processing is broken. A skilled Indian software engineer exploring the UK Skilled Worker Visa faces:

- **200+ pages** of fragmented legal text across gov.uk, UKVI guidance, and SOL tables
- **Contradictory information** — salary thresholds changed three times since April 2024 (£26K → £38.7K → £41.7K)
- **No single source of truth** — government portals, law firm blogs, and reddit threads offer conflicting advice
- **$3,000–8,000** in legal consultation fees for a basic eligibility assessment

This is not a knowledge problem. It is a **retrieval and synthesis** problem — exactly what Agentic RAG was designed for.

## 2026 Market Context

| Signal | Data Point |
|---|---|
| Indian tech professionals emigrating annually | ~350,000 (MHA 2025 data) |
| Top 3 destinations | Canada (Express Entry), UK (Skilled Worker), Germany (Chancenkarte) |
| Average legal consultation cost | $3,000–$8,000 per visa category |
| UK salary threshold (March 2026) | £41,700/year, £17.13/hour floor |
| Germany Chancenkarte financial proof | €13,092/year (up from €12,324) |
| Canada Express Entry CRS cutoff | Draw #402: Senior Managers 429, General CEC ~508 |

The Chancenkarte launched in June 2024. As of March 2026, there is **no authoritative, free, AI-powered tool** that evaluates eligibility across multiple visa categories using grounded legal sources.

## User Personas

### Primary: The Evaluator (Recruiter / Hiring Manager)

- Reviews this project on GitHub or LinkedIn
- Evaluates: architectural depth, code quality, production readiness
- Success criteria: *"This person understands enterprise AI systems"*

### Secondary: The Applicant (Indian Tech Professional)

- 25–35 years old, 3–8 years of experience, Masters or Bachelors in CS/IT
- Exploring UK, Germany, or Canada for career advancement
- Needs: fast eligibility check, clear reasoning, cited sources
- Constraint: cannot afford $5,000 in legal fees for exploratory assessment

## Key Success Metrics

| Metric | Definition | Target |
|---|---|---|
| **Citation Accuracy** | % of Legal Analyst claims backed by a valid source chunk | ≥ 95% |
| **Token Efficiency** | Average tokens consumed per complete eligibility assessment | < 15,000 |
| **Retrieval Precision@5** | % of top-5 retrieved chunks rated as "relevant" by the Grader | ≥ 80% |
| **CRAG Loop Effectiveness** | % of "irrelevant" gradings successfully resolved by re-query | ≥ 70% |
| **Ambiguity Detection Rate** | % of conflicting-source scenarios correctly flagged as "ambiguous" | ≥ 85% |
| **End-to-End Latency** | Time from applicant profile submission to Markdown report | < 30 seconds |
| **Stale Data Detection** | % of outdated cached values caught by Stealth Verification | ≥ 90% |

## Non-Goals (Sprint 1)

- Not a production legal advisory tool
- No real-time government portal scraping at scale
- No multi-language support
- No user authentication or persistent accounts
- No mobile application

## Dependencies

| Dependency | Tier | Monthly Cost |
|---|---|---|
| Google AI Studio (Gemini 3) | Free | $0 |
| Azure AI Search | Free (50MB, 3 indexes) | $0 |
| LangSmith | Free (5K traces/month) | $0 |
| Playwright | Open source | $0 |
| **Total** | | **$0** |
