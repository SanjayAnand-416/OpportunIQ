"""SQLite persistence for dashboard, email, and system notifications."""

import uuid
from collections.abc import Mapping
from typing import Any

import aiosqlite

from app.database import get_db


NOTIFICATION_COLUMNS = (
    "id",
    "profile_id",
    "deadline_id",
    "subject",
    "message",
    "channel",
    "reminder_offset",
    "is_read",
    "delivery_status",
    "error_message",
    "sent_at",
    "created_at",
)
ALLOWED_CHANNELS = {"dashboard", "email", "system"}
ALLOWED_DELIVERY_STATUSES = {"created", "sent", "failed", "skipped"}


def _required_text(value: Any, field_name: str) -> str:
    clean_value = str(value or "").strip()
    if not clean_value:
        raise ValueError(f"{field_name} is required.")
    return clean_value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def row_to_notification(
    row: aiosqlite.Row | Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Map a SQLite row to the public notification representation."""
    if row is None:
        return None
    data = dict(row)
    notification = {
        column: data.get(column) for column in NOTIFICATION_COLUMNS if column in data
    }
    notification["is_read"] = bool(int(notification.get("is_read") or 0))
    return notification


async def get_notification_by_id(notification_id: str) -> dict[str, Any] | None:
    """Load one notification by public UUID."""
    clean_id = _optional_text(notification_id)
    if clean_id is None:
        return None
    async with get_db() as db:
        cursor = await db.execute(
            f"SELECT {', '.join(NOTIFICATION_COLUMNS)} FROM notifications WHERE id = ?",
            (clean_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
    return row_to_notification(row)


async def _get_duplicate_notification(
    *, deadline_id: str, reminder_offset: str, channel: str
) -> dict[str, Any] | None:
    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT {', '.join(NOTIFICATION_COLUMNS)}
            FROM notifications
            WHERE deadline_id = ? AND reminder_offset = ? AND channel = ?
            LIMIT 1
            """,
            (deadline_id, reminder_offset, channel),
        )
        row = await cursor.fetchone()
        await cursor.close()
    return row_to_notification(row)


async def notification_exists(
    *, deadline_id: str, reminder_offset: str, channel: str
) -> bool:
    """Return whether an equivalent reminder notification exists."""
    return (
        await _get_duplicate_notification(
            deadline_id=_required_text(deadline_id, "deadline_id"),
            reminder_offset=_required_text(reminder_offset, "reminder_offset"),
            channel=_validate_channel(channel),
        )
        is not None
    )


def _validate_channel(channel: str) -> str:
    clean_channel = _required_text(channel, "channel").lower()
    if clean_channel not in ALLOWED_CHANNELS:
        raise ValueError("Unsupported notification channel.")
    return clean_channel


def _validate_delivery_status(delivery_status: str) -> str:
    clean_status = _required_text(delivery_status, "delivery_status").lower()
    if clean_status not in ALLOWED_DELIVERY_STATUSES:
        raise ValueError("Unsupported notification delivery status.")
    return clean_status


async def create_notification(
    *,
    profile_id: str,
    subject: str,
    message: str,
    channel: str,
    deadline_id: str | None = None,
    reminder_offset: str | None = None,
    delivery_status: str = "created",
    error_message: str | None = None,
) -> dict[str, Any]:
    """Create an idempotent notification and return its public representation."""
    clean_profile_id = _required_text(profile_id, "profile_id")
    clean_channel = _validate_channel(channel)
    clean_status = _validate_delivery_status(delivery_status)
    clean_deadline_id = _optional_text(deadline_id)
    clean_offset = _optional_text(reminder_offset)

    if clean_deadline_id is not None and clean_offset is not None:
        existing = await _get_duplicate_notification(
            deadline_id=clean_deadline_id,
            reminder_offset=clean_offset,
            channel=clean_channel,
        )
        if existing is not None:
            return existing

    notification_id = str(uuid.uuid4())
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO notifications (
                    id, profile_id, deadline_id, subject, message, channel,
                    reminder_offset, is_read, delivery_status, error_message,
                    sent_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    notification_id,
                    clean_profile_id,
                    clean_deadline_id,
                    _required_text(subject, "subject"),
                    _required_text(message, "message"),
                    clean_channel,
                    clean_offset,
                    clean_status,
                    _optional_text(error_message),
                ),
            )
            await db.commit()
    except aiosqlite.IntegrityError:
        if clean_deadline_id is None or clean_offset is None:
            raise
        existing = await _get_duplicate_notification(
            deadline_id=clean_deadline_id,
            reminder_offset=clean_offset,
            channel=clean_channel,
        )
        if existing is not None:
            return existing
        raise

    created = await get_notification_by_id(notification_id)
    if created is None:
        raise RuntimeError("Created notification could not be loaded.")
    return created


async def update_delivery_status(
    notification_id: str,
    *,
    delivery_status: str,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    """Update delivery outcome fields for one notification."""
    clean_status = _validate_delivery_status(delivery_status)
    async with get_db() as db:
        cursor = await db.execute(
            """
            UPDATE notifications
            SET delivery_status = ?, error_message = ?
            WHERE id = ?
            """,
            (clean_status, _optional_text(error_message), notification_id),
        )
        await db.commit()
        updated = cursor.rowcount
        await cursor.close()
    if not updated:
        return None
    return await get_notification_by_id(notification_id)
