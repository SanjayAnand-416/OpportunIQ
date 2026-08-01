"""Active Discovery Router adapter for the existing Person C ranker."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

BUNDLED_MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "models" / "all-MiniLM-L6-v2"
)


def deduplicate(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Delegate deduplication and return active-router opportunity mappings."""
    legacy = _person_c_ranker()
    listings = [_to_legacy_listing(opportunity) for opportunity in opportunities]
    deduplicated = legacy.deduplicate(listings)
    return [_from_legacy_listing(listing) for listing in deduplicated]


def score(opportunity: dict[str, Any], student_skills: list[str]) -> dict[str, Any]:
    """Return all Person C score components, with a deterministic fallback."""
    legacy = _person_c_ranker()
    profile = legacy.StudentProfile(skills=student_skills)
    listing = _to_legacy_listing(opportunity)
    try:
        _configure_packaged_model(legacy)
        scored = legacy.score(profile, listing)
        return _score_components(
            skill_score=scored.skill_score,
            urgency_score=scored.urgency_score,
            final_score=scored.final_score,
            fallback_used=False,
        )
    except Exception as exc:
        logger.warning(
            "Packaged MiniLM scoring unavailable; using deterministic fallback: %s",
            type(exc).__name__,
        )
        skill_score = _deterministic_skill_score(
            student_skills,
            listing.opportunity.skills_required,
        )
        urgency_score = legacy._urgency(
            listing.opportunity.deadline,
            legacy.date.today(),
        )
        final_score = (
            legacy.SKILL_SCORE_WEIGHT * skill_score
            + legacy.URGENCY_WEIGHT * urgency_score
        )
        return _score_components(
            skill_score=skill_score,
            urgency_score=urgency_score,
            final_score=final_score,
            fallback_used=True,
        )


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


def _configure_packaged_model(legacy: Any) -> None:
    """Load MiniLM exclusively from the model snapshot shipped with the app."""
    if legacy._embedding_model is not None:
        return
    if not BUNDLED_MODEL_PATH.is_dir():
        raise FileNotFoundError("Packaged MiniLM model is missing")
    legacy._embedding_model = legacy.SentenceTransformer(
        str(BUNDLED_MODEL_PATH),
        local_files_only=True,
    )


def _deterministic_skill_score(
    student_skills: list[str],
    required_skills: list[str],
) -> float:
    """Score exact case-insensitive overlap when semantic inference is unavailable."""
    student = {skill.strip().lower() for skill in student_skills if skill.strip()}
    required = {skill.strip().lower() for skill in required_skills if skill.strip()}
    if not student or not required:
        return 0.0
    return len(student & required) / len(required)


def _score_components(
    *,
    skill_score: float,
    urgency_score: float,
    final_score: float,
    fallback_used: bool,
) -> dict[str, Any]:
    """Expose active aliases without altering Person C's score values."""
    return {
        "semantic_score": skill_score,
        "skill_score": skill_score,
        "urgency_score": urgency_score,
        "deadline_score": urgency_score,
        "final_score": final_score,
        "fallback_used": fallback_used,
    }
