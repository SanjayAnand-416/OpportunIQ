"""Deadline Registry API routes for the OpportunIQ backend."""

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.models import (
    CalendarEventResponse,
    DeadlineCreate,
    DeadlineCreateResponse,
    DeadlineDeleteResponse,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdate,
    DeadlineUpdateResponse,
)
from app.repositories import deadline_repository, profile_repository
from app.services import deadline_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/deadlines",
    tags=["Deadlines"],
)

EVENT_TYPE_ALIASES = {
    "oa": "assessment",
    "online_assessment": "assessment",
    "online assessment": "assessment",
    "offer": "offer_acceptance",
    "offer_acceptance": "offer_acceptance",
    "offer acceptance": "offer_acceptance",
}


async def _require_profile(profile_id: str) -> str:
    clean_profile_id = profile_id.strip()
    if not clean_profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    profile = await profile_repository.get_profile_by_id(clean_profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return clean_profile_id


def _deadline_response(raw_deadline: dict[str, Any]) -> DeadlineResponse:
    return DeadlineResponse(**raw_deadline)


def _normalize_event_type(value: str | None) -> str | None:
    if value is None:
        return None
    clean_value = value.strip().lower().replace("-", "_")
    return EVENT_TYPE_ALIASES.get(clean_value, clean_value)


def _calendar_color(deadline: dict[str, Any]) -> str:
    if deadline.get("is_completed"):
        return "#64748B"
    if deadline.get("needs_review"):
        return "#8B5CF6"
    if deadline.get("status") == "overdue":
        return "#E24B4A"
    days_remaining = deadline.get("days_remaining")
    if days_remaining is not None and days_remaining <= 3:
        return "#E24B4A"
    if days_remaining is not None and days_remaining <= 7:
        return "#EF9F27"
    return "#1D9E75"


def _deadline_list_response(
    *,
    raw_deadlines: list[dict[str, Any]],
    profile_id: str,
) -> DeadlineListResponse:
    deadlines = [_deadline_response(deadline) for deadline in raw_deadlines]
    return DeadlineListResponse(
        deadlines=deadlines,
        count=len(deadlines),
        profile_id=profile_id,
    )


@router.post(
    "",
    response_model=DeadlineCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deadline(payload: DeadlineCreate) -> DeadlineCreateResponse:
    """Create a manual deadline for a profile."""
    profile_id = await _require_profile(payload.profile_id)
    try:
        normalized_payload = payload.model_copy(
            update={
                "profile_id": profile_id,
                "event_type": _normalize_event_type(payload.event_type) or "other",
            }
        )
        result = await deadline_service.create_manual_deadline(normalized_payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected database error while creating deadline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deadline could not be created.",
        ) from exc

    return DeadlineCreateResponse(
        success=True,
        deadline=_deadline_response(result["deadline"]),
        reminders_scheduled=result["schedule"]["scheduled_jobs"],
    )


@router.get("", response_model=DeadlineListResponse)
async def list_deadlines(
    profile_id: str = Query(...),
    include_completed: bool = Query(True),
    include_cancelled: bool = Query(False),
    needs_review: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=100),
) -> DeadlineListResponse:
    """List deadline registry entries for a profile."""
    clean_profile_id = await _require_profile(profile_id)
    deadlines = await deadline_repository.list_deadlines(
        profile_id=clean_profile_id,
        include_completed=include_completed,
        include_cancelled=include_cancelled,
        needs_review=needs_review,
        limit=limit,
    )
    return _deadline_list_response(raw_deadlines=deadlines, profile_id=clean_profile_id)


@router.get("/calendar", response_model=list[CalendarEventResponse])
async def list_calendar_events(
    profile_id: str = Query(...),
    include_completed: bool = Query(True),
    limit: int = Query(100, ge=1, le=100),
) -> list[CalendarEventResponse]:
    """Return calendar event projections for dated deadlines."""
    clean_profile_id = await _require_profile(profile_id)
    deadlines = await deadline_repository.list_deadlines(
        profile_id=clean_profile_id,
        include_completed=include_completed,
        include_cancelled=False,
        limit=limit,
    )
    events: list[CalendarEventResponse] = []
    for deadline in deadlines:
        deadline_datetime = deadline_repository._to_utc_datetime(
            deadline.get("deadline_datetime")
        )
        if deadline_datetime is None:
            continue
        deadline_response = _deadline_response(deadline)
        events.append(
            CalendarEventResponse(
                id=deadline_response.deadline_id,
                title=deadline_response.title,
                start=deadline_datetime,
                end=deadline_datetime + timedelta(hours=1),
                color=_calendar_color(deadline),
                deadline=deadline_response,
            )
        )
    return events


@router.get("/upcoming", response_model=DeadlineListResponse)
async def list_upcoming_deadlines(
    profile_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=100),
) -> DeadlineListResponse:
    """List upcoming active deadlines."""
    clean_profile_id = await _require_profile(profile_id)
    deadlines = await deadline_repository.list_upcoming_deadlines(
        profile_id=clean_profile_id,
        days=days,
        limit=limit,
    )
    return _deadline_list_response(raw_deadlines=deadlines, profile_id=clean_profile_id)


@router.get("/today", response_model=DeadlineListResponse)
async def list_today_deadlines(
    profile_id: str = Query(...),
    limit: int = Query(100, ge=1, le=100),
) -> DeadlineListResponse:
    """List active deadlines due today."""
    clean_profile_id = await _require_profile(profile_id)
    deadlines = await deadline_repository.list_today_deadlines(
        profile_id=clean_profile_id,
        limit=limit,
    )
    return _deadline_list_response(raw_deadlines=deadlines, profile_id=clean_profile_id)


@router.get("/overdue", response_model=DeadlineListResponse)
async def list_overdue_deadlines(
    profile_id: str = Query(...),
    include_completed: bool = Query(False),
    limit: int = Query(100, ge=1, le=100),
) -> DeadlineListResponse:
    """List overdue deadlines."""
    clean_profile_id = await _require_profile(profile_id)
    deadlines = await deadline_repository.list_overdue_deadlines(
        profile_id=clean_profile_id,
        include_completed=include_completed,
        limit=limit,
    )
    return _deadline_list_response(raw_deadlines=deadlines, profile_id=clean_profile_id)


@router.get("/needs-review", response_model=DeadlineListResponse)
async def list_needs_review_deadlines(
    profile_id: str = Query(...),
    limit: int = Query(100, ge=1, le=100),
) -> DeadlineListResponse:
    """List deadlines that require manual review."""
    clean_profile_id = await _require_profile(profile_id)
    deadlines = await deadline_repository.list_needs_review_deadlines(
        profile_id=clean_profile_id,
        limit=limit,
    )
    return _deadline_list_response(raw_deadlines=deadlines, profile_id=clean_profile_id)


@router.get("/{deadline_id}", response_model=DeadlineResponse)
async def get_deadline(deadline_id: str) -> DeadlineResponse:
    """Retrieve one deadline by ID."""
    deadline = await deadline_repository.get_deadline_by_id(deadline_id)
    if deadline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    return _deadline_response(deadline)


@router.put("/{deadline_id}", response_model=DeadlineUpdateResponse)
async def update_deadline(
    deadline_id: str,
    payload: DeadlineUpdate,
) -> DeadlineUpdateResponse:
    """Update one deadline."""
    updates = payload.model_dump(exclude_unset=True)
    if "event_type" in updates:
        updates["event_type"] = _normalize_event_type(updates["event_type"])
    try:
        updated_deadline = await deadline_service.update_existing_deadline(
            deadline_id, updates
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if updated_deadline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    return DeadlineUpdateResponse(success=True, deadline=_deadline_response(updated_deadline))


@router.delete("/{deadline_id}", response_model=DeadlineDeleteResponse)
async def delete_deadline(deadline_id: str) -> DeadlineDeleteResponse:
    """Delete one deadline."""
    deleted = await deadline_service.delete_existing_deadline(deadline_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    return DeadlineDeleteResponse(success=True, deadline_id=deadline_id)
