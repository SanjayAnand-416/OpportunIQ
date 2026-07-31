"""SQLite persistence layer.

Thin async wrapper around ``aiosqlite``. Each repository opens a short-lived
connection per call (SQLite has no meaningful pooling story for a single
local file) and guards schema creation so it only runs once per process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite
from pydantic import BaseModel

from services.groq_service import ReminderMessage, Urgency

logger = logging.getLogger(__name__)

DATABASE_PATH_ENV = "DATABASE_PATH"
DEFAULT_DATABASE_PATH = "opportuniq.db"

_NOTIFICATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS notifications (
    id              TEXT PRIMARY KEY,
    student_id      TEXT NOT NULL,
    opportunity_id  TEXT,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL,
    urgency         TEXT NOT NULL DEFAULT 'medium',
    is_read         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    read_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_notifications_student ON notifications (student_id);
CREATE INDEX IF NOT EXISTS idx_notifications_student_unread
    ON notifications (student_id, is_read);
"""


def get_database_path() -> str:
    """Return the configured SQLite file path (``DATABASE_PATH`` env var)."""
    return os.getenv(DATABASE_PATH_ENV, "").strip() or DEFAULT_DATABASE_PATH


class NotificationRecord(BaseModel):
    """A persisted notification row."""

    id: str
    student_id: str
    opportunity_id: str | None = None
    subject: str
    body: str
    urgency: Urgency = Urgency.MEDIUM
    is_read: bool = False
    created_at: datetime
    read_at: datetime | None = None


class SQLiteNotificationRepository:
    """SQLite-backed CRUD access for notifications.

    Also satisfies ``services.scheduler_service.NotificationRepository``
    (via :meth:`save_notification`), so it can be handed straight to
    ``scheduler_service.configure()``.
    """

    def __init__(self, database_path: str | None = None) -> None:
        self._database_path = database_path or get_database_path()
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    @asynccontextmanager
    async def _connect(self):
        """Open a connection with the schema guaranteed to exist.

        ``aiosqlite.Connection.__aenter__`` re-awaits the connection object,
        which blows up if it is already open — so this wraps a *freshly
        created, unopened* connection in the context manager rather than
        awaiting it first.
        """
        await self._ensure_schema()
        async with aiosqlite.connect(self._database_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    async def _ensure_schema(self) -> None:
        """Create the notifications table/indexes once per process."""
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:  # re-check: another task may have won the race
                return
            async with aiosqlite.connect(self._database_path) as conn:
                await conn.executescript(_NOTIFICATIONS_SCHEMA)
                await conn.commit()
            self._schema_ready = True
            logger.info("Ensured notifications schema at %s", self._database_path)

    async def create(
        self,
        *,
        student_id: str,
        subject: str,
        body: str,
        opportunity_id: str | None = None,
        urgency: Urgency = Urgency.MEDIUM,
    ) -> NotificationRecord:
        """Insert a new notification and return the stored record."""
        record = NotificationRecord(
            id=str(uuid.uuid4()),
            student_id=student_id,
            opportunity_id=opportunity_id,
            subject=subject,
            body=body,
            urgency=urgency,
            is_read=False,
            created_at=datetime.now(),
            read_at=None,
        )
        async with self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO notifications
                    (id, student_id, opportunity_id, subject, body, urgency, is_read, created_at, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.student_id,
                    record.opportunity_id,
                    record.subject,
                    record.body,
                    record.urgency.value,
                    int(record.is_read),
                    record.created_at.isoformat(),
                    record.read_at,
                ),
            )
            await conn.commit()
        logger.info("Created notification %s for student %s", record.id, student_id)
        return record

    async def save_notification(
        self, student_id: str, opportunity_id: str, reminder: ReminderMessage
    ) -> str:
        """Persist a generated reminder as a notification (scheduler_service hook)."""
        record = await self.create(
            student_id=student_id,
            opportunity_id=opportunity_id,
            subject=reminder.subject,
            body=reminder.body,
            urgency=reminder.urgency,
        )
        return record.id

    async def list_for_student(
        self,
        student_id: str,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationRecord]:
        """List a student's notifications, newest first."""
        query = "SELECT * FROM notifications WHERE student_id = ?"
        params: list = [student_id]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with self._connect() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [_row_to_record(row) for row in rows]

    async def get(self, notification_id: str) -> NotificationRecord | None:
        """Fetch one notification by id, or ``None`` if it doesn't exist."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM notifications WHERE id = ?", (notification_id,)
            )
            row = await cursor.fetchone()
        return _row_to_record(row) if row else None

    async def mark_read(self, notification_id: str) -> NotificationRecord | None:
        """Mark one notification read; returns the updated record, or ``None`` if missing."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                "UPDATE notifications SET is_read = 1, read_at = ? WHERE id = ? AND is_read = 0",
                (datetime.now().isoformat(), notification_id),
            )
            await conn.commit()
            if cursor.rowcount == 0:
                # Either it doesn't exist, or it was already read — tell them apart.
                existing = await conn.execute(
                    "SELECT * FROM notifications WHERE id = ?", (notification_id,)
                )
                row = await existing.fetchone()
                return _row_to_record(row) if row else None

            updated = await conn.execute(
                "SELECT * FROM notifications WHERE id = ?", (notification_id,)
            )
            row = await updated.fetchone()
        return _row_to_record(row) if row else None

    async def mark_all_read(self, student_id: str) -> int:
        """Mark every unread notification for ``student_id`` as read.

        Returns:
            The number of notifications updated.
        """
        async with self._connect() as conn:
            cursor = await conn.execute(
                "UPDATE notifications SET is_read = 1, read_at = ? "
                "WHERE student_id = ? AND is_read = 0",
                (datetime.now().isoformat(), student_id),
            )
            await conn.commit()
            updated = cursor.rowcount
        logger.info("Marked %d notification(s) read for student %s", updated, student_id)
        return updated

    async def delete(self, notification_id: str) -> bool:
        """Delete one notification. Returns ``True`` if a row was removed."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                "DELETE FROM notifications WHERE id = ?", (notification_id,)
            )
            await conn.commit()
            deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted notification %s", notification_id)
        return deleted


def _row_to_record(row: aiosqlite.Row) -> NotificationRecord:
    """Map one SQLite row onto a :class:`NotificationRecord`."""
    return NotificationRecord(
        id=row["id"],
        student_id=row["student_id"],
        opportunity_id=row["opportunity_id"],
        subject=row["subject"],
        body=row["body"],
        urgency=Urgency(row["urgency"]),
        is_read=bool(row["is_read"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        read_at=datetime.fromisoformat(row["read_at"]) if row["read_at"] else None,
    )
