"""Business operations for manual and Gmail-derived deadlines."""

from datetime import datetime
from typing import Any

from app.models import DeadlineCreate
from app.repositories import deadline_repository


async def create_manual_deadline(payload: DeadlineCreate) -> dict[str, Any]:
    """Create a deadline while preserving manual-source semantics."""
    return await deadline_repository.create_deadline(
        **payload.model_dump(),
        source="manual",
    )


async def create_gmail_deadline(
    *,
    profile_id: str,
    title: str,
    deadline_datetime: datetime | str | None,
    organization: str | None = None,
    event_type: str = "other",
    action_required: str | None = None,
    notes: str | None = None,
    gmail_message_id: str | None = None,
    confidence: float | None = None,
    needs_review: bool = False,
    opportunity_id: str | None = None,
) -> dict[str, Any]:
    """Create or retrieve an idempotent Gmail-derived deadline."""
    return await deadline_repository.create_deadline(
        profile_id=profile_id,
        opportunity_id=opportunity_id,
        title=title,
        organization=organization,
        deadline_datetime=deadline_datetime,
        event_type=event_type,
        action_required=action_required,
        notes=notes,
        source="gmail",
        gmail_message_id=gmail_message_id,
        confidence=confidence,
        needs_review=needs_review,
    )


async def update_existing_deadline(
    deadline_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply an allowlisted deadline update."""
    return await deadline_repository.update_deadline(deadline_id, updates)


async def delete_existing_deadline(deadline_id: str) -> bool:
    """Delete one deadline by public identifier."""
    return await deadline_repository.delete_deadline(deadline_id)
