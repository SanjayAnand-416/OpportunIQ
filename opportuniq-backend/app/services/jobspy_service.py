"""Async-safe wrapper around python-jobspy searches."""

import asyncio
import logging
import math
from collections.abc import Mapping
from typing import Any

from jobspy import scrape_jobs


logger = logging.getLogger(__name__)

JOBSPY_SITES = ["linkedin", "naukri", "indeed", "glassdoor", "google"]
MAX_RESULTS_WANTED = 50
DEFAULT_TIMEOUT_SECONDS = 25


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        if value != value:
            return None
    except TypeError:
        return value
    return value


def normalize_jobspy_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one JobSpy result into a compact raw opportunity dict."""
    clean_record = {key: _clean_value(value) for key, value in dict(record).items()}
    url = clean_record.get("url") or clean_record.get("job_url")
    platform = clean_record.get("site") or clean_record.get("platform")
    return {
        "source": "jobspy",
        "platform": platform,
        "site": platform,
        "title": clean_record.get("title"),
        "company": clean_record.get("company"),
        "location": clean_record.get("location"),
        "url": url,
        "description": clean_record.get("description"),
        "date_posted": clean_record.get("date_posted"),
        "job_type": clean_record.get("job_type"),
        "min_amount": clean_record.get("min_amount"),
        "max_amount": clean_record.get("max_amount"),
    }


async def search_jobs(
    role: str,
    location: str | None,
    opportunity_type: str | None,
    results_wanted: int = 15,
    hours_old: int = 168,
) -> list[dict[str, Any]]:
    """Search job platforms through JobSpy without blocking the event loop."""
    search_role = role.strip()
    if not search_role:
        return []

    search_location = (location or "India").strip() or "India"
    safe_results_wanted = max(1, min(int(results_wanted), MAX_RESULTS_WANTED))

    try:
        jobs = await asyncio.wait_for(
            asyncio.to_thread(
                scrape_jobs,
                site_name=JOBSPY_SITES,
                search_term=search_role,
                location=search_location,
                results_wanted=safe_results_wanted,
                hours_old=hours_old,
            ),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("JobSpy search failed for role %s: %s", search_role, exc)
        return []

    if jobs is None or getattr(jobs, "empty", False):
        return []

    try:
        records = jobs.to_dict("records")
    except AttributeError:
        logger.warning("JobSpy returned an unexpected result type")
        return []

    return [normalize_jobspy_record(record) for record in records]
