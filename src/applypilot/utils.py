"""Common utility helpers for ApplyPilot."""
from __future__ import annotations

import re


DIRECT_EMPLOYER_STRATEGIES = frozenset({
    "greenhouse_api", "workday_api", "lever_api", "ashby_api",
    "amazon_jobs", "microsoft_careers", "apple_jobs", "google_careers",
    "meta_careers", "twilio_greenhouse",
})


def resolve_company_key(job: dict) -> str | None:
    """Return a lowercase company key for cap logic, or None if exempt.

    Resolution order:
      1. The extracted ``company`` column when populated.
      2. The ATS-tenant slug embedded in ``application_url`` for any
         job that points at a known direct-employer ATS (Greenhouse,
         Lever, Ashby, Workday). This catches the LinkedIn-aggregator
         case where ``company`` is NULL but the apply URL clearly
         identifies the employer (e.g. a LinkedIn listing whose Apply
         button resolves to job-boards.greenhouse.io/{slug}/...).
      3. Direct-employer ``site`` (the fallback for direct scrapers).
    """
    co = (job.get("company") or "").strip().lower()
    if co:
        return co

    # 2) ATS-tenant extraction from application_url. Works regardless
    # of whether the discovery strategy was an aggregator or direct.
    apply_url = (job.get("application_url") or "").lower()
    if apply_url:
        # Greenhouse: boards.greenhouse.io/{slug}/jobs/N or
        #             job-boards.greenhouse.io/{slug}/jobs/N (eu/us)
        m = re.search(r"(?:job-)?boards(?:\.eu)?\.greenhouse\.io/([a-z0-9-]+)/", apply_url)
        if m:
            return m.group(1)
        # Lever: jobs.lever.co/{slug}/...
        m = re.search(r"jobs\.lever\.co/([a-z0-9-]+)/", apply_url)
        if m:
            return m.group(1)
        # Ashby: jobs.ashbyhq.com/{slug}/...
        m = re.search(r"jobs\.ashbyhq\.com/([a-z0-9-]+)/", apply_url)
        if m:
            return m.group(1)
        # Workday: {tenant}.wd*.myworkdayjobs.com/...
        m = re.search(r"https?://([a-z0-9-]+)\.wd[0-9]+\.myworkdayjobs\.com/", apply_url)
        if m:
            return m.group(1)

    # 3) Direct-employer site fallback.
    strategy = (job.get("strategy") or "").lower()
    if strategy in DIRECT_EMPLOYER_STRATEGIES:
        site = (job.get("site") or "").strip().lower()
        if site:
            return site
    return None


def display_company(job: dict) -> str:
    """Best-known employer name for prompts, or '' if unknown.

    Uses ``company`` column first. If empty, falls back to the
    ATS-tenant slug from ``resolve_company_key``.
    """
    co = (job.get("company") or "").strip()
    if co:
        return co
    resolved = resolve_company_key(job)
    return resolved or ""
