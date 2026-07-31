"""Persistence helpers for the deadline registry."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from app.database import get_db


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

ALLOWED_SOURCES = {"manual", "gmail"}

UPDATE_FIELDS = {
    "opportunity_id",
    "title",
    "organization",
    "deadline_datetime",
    "event_type",
    "action_required",
    "notes",
    "confidence",
    "needs_review",
    "is_completed",
    "is_cancelled",
}

BOOLEAN_FIELDS = {"needs_review", "is_completed", "is_cancelled"}


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


def _clamp_limit(limit: int) -> int:
    return max(1, min(int(limit), 100))


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    clean_value = str(value).strip()
    return clean_value or None


def _clean_title(value: Any) -> str:
    clean_value = _clean_optional_text(value)
    if clean_value is None:
        raise ValueError("Deadline title is required.")
    return clean_value


def _clean_source(value: str) -> str:
    clean_value = str(value or "").strip().lower()
    if clean_value not in ALLOWED_SOURCES:
        raise ValueError("Deadline source must be manual or gmail.")
    return clean_value


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


async def get_deadline_by_id(deadline_id: str) -> dict[str, Any] | None:
    """Load one deadline by public deadline ID."""
    clean_deadline_id = str(deadline_id or "").strip()
    if not clean_deadline_id:
        return None

    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT {', '.join(DEADLINE_COLUMNS)}
            FROM deadline_registry
            WHERE id = ?
            """,
            (clean_deadline_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
    return row_to_deadline(row)


async def _get_existing_gmail_deadline(
    *,
    profile_id: str,
    gmail_message_id: str | None,
) -> dict[str, Any] | None:
    if gmail_message_id is None:
        return None

    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT {', '.join(DEADLINE_COLUMNS)}
            FROM deadline_registry
            WHERE profile_id = ? AND gmail_message_id = ?
            LIMIT 1
            """,
            (profile_id, gmail_message_id),
        )
        row = await cursor.fetchone()
        await cursor.close()
    return row_to_deadline(row)


async def create_deadline(
    *,
    profile_id: str,
    title: str,
    deadline_datetime: Any = None,
    source: str = "manual",
    opportunity_id: str | None = None,
    organization: str | None = None,
    event_type: str | None = "other",
    action_required: str | None = None,
    notes: str | None = None,
    gmail_message_id: str | None = None,
    confidence: float | None = None,
    needs_review: bool = False,
    is_completed: bool = False,
    is_cancelled: bool = False,
) -> dict[str, Any]:
    """Persist a deadline registry item and return the API shape."""
    clean_source = _clean_source(source)
    clean_profile_id = _clean_optional_text(profile_id)
    if clean_profile_id is None:
        raise ValueError("Profile ID is required.")

    clean_gmail_message_id = _clean_optional_text(gmail_message_id)
    existing_deadline = await _get_existing_gmail_deadline(
        profile_id=clean_profile_id,
        gmail_message_id=clean_gmail_message_id,
    )
    if existing_deadline is not None:
        return existing_deadline

    serialized_deadline = _serialize_datetime(deadline_datetime)
    if clean_source == "manual" and serialized_deadline is None:
        raise ValueError("Manual deadlines require deadline_datetime.")
    if clean_source == "gmail" and serialized_deadline is None and not needs_review:
        raise ValueError("Gmail deadlines without a date must be marked needs_review.")

    deadline_id = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO deadline_registry (
                id,
                profile_id,
                opportunity_id,
                title,
                organization,
                deadline_datetime,
                event_type,
                action_required,
                notes,
                source,
                gmail_message_id,
                confidence,
                needs_review,
                is_completed,
                is_cancelled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                deadline_id,
                clean_profile_id,
                _clean_optional_text(opportunity_id),
                _clean_title(title),
                _clean_optional_text(organization),
                serialized_deadline,
                _clean_optional_text(event_type) or "other",
                _clean_optional_text(action_required),
                _clean_optional_text(notes),
                clean_source,
                clean_gmail_message_id,
                _float_value(confidence),
                int(bool(needs_review)),
                int(bool(is_completed)),
                int(bool(is_cancelled)),
            ),
        )
        await db.commit()

    created_deadline = await get_deadline_by_id(deadline_id)
    if created_deadline is None:
        raise RuntimeError("Created deadline could not be loaded.")
    return created_deadline


def _sort_deadlines_by_datetime(deadlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        deadlines,
        key=lambda item: (
            _to_utc_datetime(item.get("deadline_datetime")) is None,
            _to_utc_datetime(item.get("deadline_datetime")) or datetime.max.replace(tzinfo=UTC),
            str(item.get("created_at") or ""),
        ),
    )


async def list_deadlines(
    *,
    profile_id: str,
    include_completed: bool = True,
    include_cancelled: bool = False,
    needs_review: bool | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List deadlines for a profile with basic registry filters."""
    clean_profile_id = _clean_optional_text(profile_id)
    if clean_profile_id is None:
        return []

    where_clauses = ["profile_id = ?"]
    values: list[Any] = [clean_profile_id]
    if needs_review is not None:
        where_clauses.append("COALESCE(needs_review, 0) = ?")
        values.append(int(bool(needs_review)))
    if not include_completed:
        where_clauses.append("COALESCE(is_completed, 0) = 0")
    if not include_cancelled:
        where_clauses.append("COALESCE(is_cancelled, 0) = 0")

    values.append(_clamp_limit(limit))
    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT {', '.join(DEADLINE_COLUMNS)}
            FROM deadline_registry
            WHERE {' AND '.join(where_clauses)}
            ORDER BY
                deadline_datetime IS NULL,
                deadline_datetime ASC,
                created_at DESC
            LIMIT ?
            """,
            values,
        )
        rows = await cursor.fetchall()
        await cursor.close()

    deadlines = [item for row in rows if (item := row_to_deadline(row)) is not None]
    return _sort_deadlines_by_datetime(deadlines)


async def list_upcoming_deadlines(
    *,
    profile_id: str,
    days: int = 30,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return active deadlines due after today within the requested window."""
    requested_days = max(1, int(days))
    deadlines = await list_deadlines(
        profile_id=profile_id,
        include_completed=False,
        include_cancelled=False,
        limit=limit,
    )
    return [
        deadline
        for deadline in deadlines
        if deadline["status"] == "upcoming"
        and deadline["days_remaining"] is not None
        and deadline["days_remaining"] <= requested_days
    ]


async def list_today_deadlines(*, profile_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return active deadlines due today."""
    deadlines = await list_deadlines(
        profile_id=profile_id,
        include_completed=False,
        include_cancelled=False,
        limit=limit,
    )
    return [deadline for deadline in deadlines if deadline["status"] == "due_today"]


async def list_overdue_deadlines(
    *,
    profile_id: str,
    include_completed: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return overdue deadlines for a profile."""
    deadlines = await list_deadlines(
        profile_id=profile_id,
        include_completed=include_completed,
        include_cancelled=False,
        limit=limit,
    )
    return [deadline for deadline in deadlines if deadline["status"] == "overdue"]


async def list_needs_review_deadlines(
    *,
    profile_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return deadlines needing manual review, newest first."""
    deadlines = await list_deadlines(
        profile_id=profile_id,
        include_completed=True,
        include_cancelled=False,
        needs_review=True,
        limit=limit,
    )
    return sorted(deadlines, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def _normalize_update_value(field_name: str, value: Any) -> Any:
    if field_name == "title":
        return _clean_title(value)
    if field_name == "deadline_datetime":
        return _serialize_datetime(value)
    if field_name == "confidence":
        return _float_value(value)
    if field_name in BOOLEAN_FIELDS:
        return int(bool(value))
    if field_name in {
        "opportunity_id",
        "organization",
        "event_type",
        "action_required",
        "notes",
    }:
        return _clean_optional_text(value)
    return value


async def update_deadline(
    deadline_id: str,
    updates: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Apply allowlisted partial updates and return the updated deadline."""
    existing_deadline = await get_deadline_by_id(deadline_id)
    if existing_deadline is None:
        return None

    clean_updates: dict[str, Any] = {}
    for field_name, value in updates.items():
        if field_name not in UPDATE_FIELDS:
            continue
        clean_updates[field_name] = _normalize_update_value(field_name, value)

    if not clean_updates:
        return existing_deadline

    set_clause = ", ".join(f"{field_name} = ?" for field_name in clean_updates)
    values = [*clean_updates.values(), deadline_id]

    async with get_db() as db:
        await db.execute(
            f"""
            UPDATE deadline_registry
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        await db.commit()

    return await get_deadline_by_id(deadline_id)


async def delete_deadline(deadline_id: str) -> bool:
    """Delete one deadline from the registry."""
    clean_deadline_id = _clean_optional_text(deadline_id)
    if clean_deadline_id is None:
        return False

    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM deadline_registry WHERE id = ?",
            (clean_deadline_id,),
        )
        await db.commit()
        deleted = cursor.rowcount
        await cursor.close()
    return bool(deleted)
