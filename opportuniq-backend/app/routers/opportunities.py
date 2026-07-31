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
