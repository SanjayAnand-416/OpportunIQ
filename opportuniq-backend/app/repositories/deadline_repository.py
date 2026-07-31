"""Persistence helpers for the deadline registry."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import aiosqlite


DEADLINE_COLUMNS = (
    "id",
    "profile_id",
    "opportunity_id",
    "title",
    "organization",
    "deadline_datetime",
    "event_type",
    "action_required",
    "notes",
    "source",
    "gmail_message_id",
    "confidence",
    "needs_review",
    "is_completed",
    "is_cancelled",
    "created_at",
    "updated_at",
)


def _to_utc_datetime(value: Any) -> datetime | None:
    """Parse a deadline datetime and normalize it to timezone-aware UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        clean_value = value.strip()
        if not clean_value:
            return None
        if clean_value.endswith("Z"):
            clean_value = f"{clean_value[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(clean_value)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _serialize_datetime(value: Any) -> str | None:
    """Return an ISO 8601 UTC timestamp for SQLite storage."""
    parsed = _to_utc_datetime(value)
    if parsed is None:
        return None
    return parsed.isoformat()


def _bool_value(value: Any) -> bool:
    return bool(int(value or 0))


def _float_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return None


def calculate_deadline_status(
    *,
    deadline_datetime: Any,
    needs_review: bool = False,
    is_completed: bool = False,
    is_cancelled: bool = False,
    now: datetime | None = None,
) -> str:
    """Calculate the deadline status expected by dashboard and Guardian callers."""
    if is_cancelled:
        return "cancelled"
    if is_completed:
        return "completed"

    parsed_deadline = _to_utc_datetime(deadline_datetime)
    if needs_review or parsed_deadline is None:
        return "needs_review"

    comparison_now = _to_utc_datetime(now) or datetime.now(UTC)
    days_remaining = (parsed_deadline.date() - comparison_now.date()).days
    if days_remaining < 0:
        return "overdue"
    if days_remaining == 0:
        return "due_today"
    return "upcoming"


def calculate_days_remaining(deadline_datetime: Any, now: datetime | None = None) -> int | None:
    """Return date-based days remaining, or None when no valid deadline exists."""
    parsed_deadline = _to_utc_datetime(deadline_datetime)
    if parsed_deadline is None:
        return None
    comparison_now = _to_utc_datetime(now) or datetime.now(UTC)
    return (parsed_deadline.date() - comparison_now.date()).days


def row_to_deadline(
    row: aiosqlite.Row | Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Convert a SQLite deadline row into the public API shape."""
    if row is None:
        return None

    row_data = dict(row)
    deadline = {
        column: row_data.get(column)
        for column in DEADLINE_COLUMNS
        if column in row_data
    }
    deadline["deadline_id"] = str(deadline.pop("id"))
    deadline["needs_review"] = _bool_value(deadline.get("needs_review"))
    deadline["is_completed"] = _bool_value(deadline.get("is_completed"))
    deadline["is_cancelled"] = _bool_value(deadline.get("is_cancelled"))
    deadline["confidence"] = _float_value(deadline.get("confidence"))
    deadline["status"] = calculate_deadline_status(
        deadline_datetime=deadline.get("deadline_datetime"),
        needs_review=deadline["needs_review"],
        is_completed=deadline["is_completed"],
        is_cancelled=deadline["is_cancelled"],
    )
    deadline["days_remaining"] = calculate_days_remaining(deadline.get("deadline_datetime"))
    return deadline
