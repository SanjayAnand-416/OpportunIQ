"""Active Discovery Router adapter for the existing Person C ranker."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any


def deduplicate(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Delegate deduplication and return active-router opportunity mappings."""
    legacy = _person_c_ranker()
    listings = [_to_legacy_listing(opportunity) for opportunity in opportunities]
    deduplicated = legacy.deduplicate(listings)
    return [_from_legacy_listing(listing) for listing in deduplicated]


def score(opportunity: dict[str, Any], student_skills: list[str]) -> float:
    """Delegate semantic and urgency scoring and return its final score."""
    legacy = _person_c_ranker()
    profile = legacy.StudentProfile(skills=student_skills)
    listing = _to_legacy_listing(opportunity)
    return legacy.score(profile, listing).final_score


def _to_legacy_listing(opportunity: Mapping[str, Any]) -> Any:
    """Translate one active-router mapping to Person C's listing schema."""
    legacy = _person_c_ranker()
    url = str(opportunity.get("url") or "")
    source = str(opportunity.get("platform") or opportunity.get("source") or "") or None
    legacy_opportunity = legacy.Opportunity(
        title=str(opportunity.get("title") or ""),
        organization=opportunity.get("company") or opportunity.get("organization"),
        opportunity_type=opportunity.get("opportunity_type") or "other",
        summary=opportunity.get("description") or opportunity.get("summary"),
        location=opportunity.get("location"),
        eligibility=_as_string_list(opportunity.get("eligibility")),
        skills_required=_as_string_list(
            opportunity.get("skills_required") or opportunity.get("skills")
        ),
        stipend=opportunity.get("stipend_or_prize") or opportunity.get("stipend"),
        application_url=url or None,
        deadline=opportunity.get("deadline"),
    )
    return legacy.DeduplicatedListing(
        opportunity=legacy_opportunity,
        url=url,
        source=source,
        also_on=_as_string_list(opportunity.get("also_on")),
    )


def _from_legacy_listing(listing: Any) -> dict[str, Any]:
    """Translate Person C's deduplicated listing to the router's raw schema."""
    opportunity = listing.opportunity
    return {
        "title": opportunity.title,
        "company": opportunity.organization,
        "platform": listing.source or "unknown",
        "url": listing.url,
        "location": opportunity.location,
        "deadline": opportunity.deadline,
        "stipend_or_prize": opportunity.stipend,
        "eligibility": opportunity.eligibility,
        "skills_required": opportunity.skills_required,
        "description": opportunity.summary,
        "also_on": listing.also_on,
    }


def _as_string_list(value: Any) -> list[str]:
    """Adapt scalar/list router fields to the legacy model's list boundary."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _person_c_ranker() -> Any:
    """Resolve the legacy implementation only at the adapter boundary."""
    return importlib.import_module("services.ranker_service")
