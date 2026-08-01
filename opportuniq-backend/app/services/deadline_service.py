"""Business operations for manual and Gmail-derived deadlines."""

from datetime import datetime
from typing import Any

from app.models import DeadlineCreate
from app.repositories import deadline_repository, settings_repository
from app.services import scheduler_service


async def _schedule_active_deadline(deadline: dict[str, Any]) -> dict[str, Any]:
    if (
        deadline.get("deadline_datetime")
        and not deadline.get("needs_review")
        and not deadline.get("is_completed")
        and not deadline.get("is_cancelled")
    ):
        return scheduler_service.schedule_reminders(
            deadline["deadline_id"],
            deadline["deadline_datetime"],
            deadline["profile_id"],
            preferences=await settings_repository.get_notification_settings(deadline["profile_id"]),
        )
    return {
        "deadline_id": deadline["deadline_id"],
        "scheduled_jobs": [],
        "skipped_offsets": list(scheduler_service.ALL_REMINDER_OFFSETS),
    }


async def create_manual_deadline(payload: DeadlineCreate) -> dict[str, Any]:
    """Create a deadline while preserving manual-source semantics."""
    deadline = await deadline_repository.create_deadline(
        **payload.model_dump(),
        source="manual",
    )
    return {"deadline": deadline, "schedule": await _schedule_active_deadline(deadline)}


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
    deadline = await deadline_repository.create_deadline(
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
    return {"deadline": deadline, "schedule": await _schedule_active_deadline(deadline)}


async def update_existing_deadline(
    deadline_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    """Apply an allowlisted deadline update."""
    deadline = await deadline_repository.update_deadline(deadline_id, updates)
    if deadline is None:
        return None
    if deadline.get("is_completed") or deadline.get("is_cancelled"):
        scheduler_service.cancel_reminders(deadline_id)
    elif deadline.get("deadline_datetime") and not deadline.get("needs_review"):
        preferences = await settings_repository.get_notification_settings(deadline["profile_id"])
        scheduler_service.cancel_reminders(deadline_id)
        scheduler_service.schedule_reminders(
            deadline_id,
            deadline["deadline_datetime"],
            deadline["profile_id"],
            preferences=preferences,
        )
    else:
        scheduler_service.cancel_reminders(deadline_id)
    return deadline


async def delete_existing_deadline(deadline_id: str) -> bool:
    """Delete one deadline by public identifier."""
    deleted = await deadline_repository.delete_deadline(deadline_id)
    if deleted:
        scheduler_service.cancel_reminders(deadline_id)
    return deleted
