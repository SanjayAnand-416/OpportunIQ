"""Opportunity discovery and query routes."""

import asyncio
import inspect
import logging
import uuid
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.models import (
    OpportunityListResponse,
    OpportunityResponse,
    OpportunitySearchRequest,
    OpportunitySearchResponse,
)
from app.repositories.opportunity_repository import (
    delete_opportunities_by_session,
    get_cached_discovery,
    get_latest_opportunities_by_profile,
    get_opportunities_by_session,
    get_opportunity_by_id,
    save_opportunities,
)
from app.repositories.profile_repository import get_profile_by_id
from app.services import jobspy_service
from app.websocket_manager import emit_trace


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/opportunities",
    tags=["Opportunities"],
)

MAX_EXTRACTION_INPUT_CHARS = 3000
MAX_EXTRACTION_RESULTS = 40


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


def _normalize_raw_result(raw: Mapping[str, Any]) -> str:
    """Build compact text for opportunity extraction."""
    parts = [
        f"Title: {raw.get('title') or ''}",
        f"Company: {raw.get('company') or raw.get('organization') or ''}",
        f"Location: {raw.get('location') or ''}",
        f"URL: {raw.get('url') or raw.get('job_url') or ''}",
        f"Source: {raw.get('source') or raw.get('platform') or raw.get('site') or ''}",
        f"Description: {raw.get('description') or raw.get('snippet') or ''}",
    ]
    return "\n".join(parts)[:MAX_EXTRACTION_INPUT_CHARS]


def _normalize_extracted_opportunity(
    opportunity: Any,
    raw_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Normalize extracted opportunity data and backfill from raw source data."""
    if hasattr(opportunity, "model_dump"):
        data = opportunity.model_dump()
    elif isinstance(opportunity, Mapping):
        data = dict(opportunity)
    else:
        return None

    title = str(data.get("title") or raw_result.get("title") or "").strip()
    company = str(
        data.get("company")
        or data.get("organization")
        or raw_result.get("company")
        or raw_result.get("organization")
        or ""
    ).strip()
    url = str(data.get("url") or raw_result.get("url") or raw_result.get("job_url") or "").strip()
    if not title or not company or not url:
        return None

    platform = str(
        data.get("platform")
        or data.get("source")
        or raw_result.get("platform")
        or raw_result.get("site")
        or raw_result.get("source")
        or "unknown"
    ).strip()

    return {
        "title": title,
        "company": company,
        "platform": platform or "unknown",
        "url": url,
        "location": data.get("location") or raw_result.get("location"),
        "deadline": data.get("deadline") or raw_result.get("deadline"),
        "stipend_or_prize": data.get("stipend_or_prize"),
        "eligibility": data.get("eligibility"),
        "skills_required": _as_list(data.get("skills_required") or data.get("skills")),
        "description": data.get("description") or raw_result.get("description"),
        "also_on": _as_list(data.get("also_on")),
    }


def _resolve_service_function(module_name: str, function_name: str) -> Callable[..., Any] | None:
    try:
        module = __import__(f"app.services.{module_name}", fromlist=[function_name])
    except ImportError:
        return None
    return getattr(module, function_name, None)


async def _call_maybe_async(function: Callable[..., Any], *args: Any, timeout: float = 20.0) -> Any:
    if inspect.iscoroutinefunction(function):
        return await asyncio.wait_for(function(*args), timeout=timeout)
    return await asyncio.wait_for(asyncio.to_thread(function, *args), timeout=timeout)


def _unique_strings(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in _as_list(values):
        lookup = value.lower()
        if lookup not in seen:
            seen.add(lookup)
            result.append(value)
    return result


def _clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return 0.0


def _parse_deadline(value: Any) -> date | None:
    if value is None or isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for parser in (datetime.fromisoformat, date.fromisoformat):
        try:
            parsed = parser(text.replace("Z", "+00:00"))
        except ValueError:
            continue
        return parsed.date() if isinstance(parsed, datetime) else parsed
    return None


def _is_expired(value: Any) -> bool:
    parsed = _parse_deadline(value)
    return parsed is not None and parsed < date.today()


def _fallback_deduplicate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for result in results:
        url = str(result.get("url") or "").strip().lower()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(result)
    return deduped


def _fallback_score(opportunity: dict[str, Any], student_skills: list[str]) -> float:
    required = {skill.lower() for skill in _as_list(opportunity.get("skills_required"))}
    skills = {skill.lower() for skill in student_skills}
    if not required or not skills:
        return 0.5
    return len(required & skills) / max(len(required), 1)


async def run_discovery_pipeline(
    *,
    session_id: str,
    profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Run opportunity discovery and return ranked, unexpired results."""
    errors: list[str] = []
    await emit_trace(session_id, "profile", "running", "Loading student profile")

    target_roles = _unique_strings(profile.get("target_roles"))
    student_skills = _as_list(profile.get("skills"))
    location = str(profile.get("location") or "India").strip() or "India"
    opportunity_type = profile.get("opportunity_type")
    profile_id = str(profile.get("profile_id") or "").strip()
    if not profile_id or not target_roles:
        await emit_trace(session_id, "profile", "error", "Profile is missing target roles")
        return [], ["Profile has no usable target roles."]

    await emit_trace(
        session_id,
        "profile",
        "complete",
        "Student profile loaded",
        {"target_roles": target_roles, "skills_count": len(student_skills)},
    )

    raw_results: list[dict[str, Any]] = []
    for role in target_roles:
        try:
            raw_results.extend(
                await jobspy_service.search_jobs(role, location, opportunity_type)
            )
        except Exception as exc:
            logger.warning("JobSpy role search failed: %s", exc)
            errors.append(f"JobSpy search failed for {role}.")
    await emit_trace(
        session_id,
        "jobspy",
        "complete",
        "JobSpy search complete",
        {"count": len(raw_results)},
    )

    tavily_search = _resolve_service_function("tavily_service", "search_hackathons_and_portals")
    tavily_count = 0
    if tavily_search is None:
        errors.append("Tavily service unavailable.")
    else:
        for role in target_roles:
            try:
                tavily_results = await _call_maybe_async(tavily_search, role, student_skills)
                if isinstance(tavily_results, list):
                    raw_results.extend(tavily_results)
                    tavily_count += len(tavily_results)
            except Exception as exc:
                logger.warning("Tavily search failed: %s", exc)
                errors.append(f"Tavily search failed for {role}.")
    await emit_trace(
        session_id,
        "tavily",
        "complete",
        "Tavily search complete",
        {"count": tavily_count},
    )

    if not raw_results:
        await emit_trace(session_id, "pipeline", "error", "No discovery results were found")
        return [], errors or ["No discovery results were found."]

    extract_opportunity = _resolve_service_function("groq_service", "extract_opportunity")
    extracted: list[dict[str, Any]] = []
    for raw in raw_results[:MAX_EXTRACTION_RESULTS]:
        try:
            if extract_opportunity is None:
                normalized = _normalize_extracted_opportunity(raw, raw)
            else:
                extracted_item = await _call_maybe_async(
                    extract_opportunity,
                    _normalize_raw_result(raw),
                    timeout=15.0,
                )
                normalized = _normalize_extracted_opportunity(extracted_item, raw)
            if normalized is not None:
                extracted.append(normalized)
        except Exception as exc:
            logger.warning("Opportunity extraction failed: %s", exc)
            errors.append("One opportunity extraction failed.")
    await emit_trace(
        session_id,
        "groq",
        "complete",
        "Structured extraction complete",
        {"count": len(extracted), "fallback": extract_opportunity is None},
    )

    if not extracted:
        await emit_trace(session_id, "pipeline", "error", "No structured opportunities remained")
        return [], errors or ["No structured opportunities remained."]

    deduplicate = _resolve_service_function("ranker_service", "deduplicate")
    try:
        deduped = (
            await _call_maybe_async(deduplicate, extracted)
            if deduplicate is not None
            else _fallback_deduplicate(extracted)
        )
    except Exception as exc:
        logger.warning("Deduplication failed: %s", exc)
        errors.append("Ranker deduplication failed; used fallback.")
        deduped = _fallback_deduplicate(extracted)
    await emit_trace(
        session_id,
        "ranker",
        "complete",
        "Deduplication complete",
        {"count": len(deduped), "fallback": deduplicate is None},
    )

    score = _resolve_service_function("ranker_service", "score")
    ranked: list[dict[str, Any]] = []
    for opportunity in deduped:
        if _is_expired(opportunity.get("deadline")):
            continue
        try:
            combined = (
                await _call_maybe_async(score, opportunity, student_skills, timeout=10.0)
                if score is not None
                else _fallback_score(opportunity, student_skills)
            )
        except Exception as exc:
            logger.warning("Opportunity scoring failed: %s", exc)
            combined = _fallback_score(opportunity, student_skills)
            errors.append("One opportunity score failed; used fallback.")
        match_score = _clamp_score(opportunity.get("match_score", combined))
        urgency_score = _clamp_score(opportunity.get("urgency_score", 0.5))
        opportunity["match_score"] = match_score
        opportunity["urgency_score"] = urgency_score
        opportunity["combined_score"] = _clamp_score(combined)
        opportunity["is_expired"] = False
        ranked.append(opportunity)

    ranked.sort(key=lambda item: item.get("combined_score", 0.0), reverse=True)
    top_results = ranked[:15]
    await emit_trace(
        session_id,
        "ranker",
        "complete",
        "Ranking complete",
        {"count": len(top_results), "fallback": score is None},
    )
    return top_results, errors


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    session_id: str | None = Query(default=None),
    profile_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> OpportunityListResponse:
    """List persisted opportunities by session or latest profile session."""
    if session_id and profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either session_id or profile_id, not both.",
        )
    if not session_id and not profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide session_id or profile_id.",
        )

    if session_id:
        clean_session_id = session_id.strip()
        opportunities = await get_opportunities_by_session(clean_session_id, limit=limit)
        return OpportunityListResponse(
            opportunities=[OpportunityResponse(**item) for item in opportunities],
            count=len(opportunities),
            session_id=clean_session_id,
        )

    clean_profile_id = (profile_id or "").strip()
    opportunities = await get_latest_opportunities_by_profile(clean_profile_id, limit=limit)
    response_session_id = opportunities[0]["session_id"] if opportunities else None
    return OpportunityListResponse(
        opportunities=[OpportunityResponse(**item) for item in opportunities],
        count=len(opportunities),
        session_id=response_session_id,
        profile_id=clean_profile_id,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: str) -> OpportunityResponse:
    """Return one persisted opportunity."""
    opportunity = await get_opportunity_by_id(opportunity_id.strip())
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opportunity not found",
        )
    return OpportunityResponse(**opportunity)
