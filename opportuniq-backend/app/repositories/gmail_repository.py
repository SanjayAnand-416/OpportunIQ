"""Persistence helpers for Gmail connection metadata."""

from datetime import UTC, datetime
from typing import Any

from app.database import get_db


GMAIL_CONNECTION_COLUMNS = (
    "profile_id",
    "email",
    "connected",
    "last_scanned",
    "deadlines_found",
    "needs_review",
    "created_at",
    "updated_at",
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_connection(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data["connected"] = bool(data.get("connected"))
    data["deadlines_found"] = int(data.get("deadlines_found") or 0)
    data["needs_review"] = int(data.get("needs_review") or 0)
    return {key: data.get(key) for key in GMAIL_CONNECTION_COLUMNS}


async def get_gmail_connection(profile_id: str) -> dict[str, Any] | None:
    """Return Gmail metadata for a public profile ID."""
    async with get_db() as db:
        cursor = await db.execute(
            f"""
            SELECT {', '.join(GMAIL_CONNECTION_COLUMNS)}
            FROM gmail_connections
            WHERE profile_id = ?
            """,
            (profile_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
    return _row_to_connection(row)


async def upsert_gmail_connection(
    profile_id: str,
    *,
    email: str | None = None,
    connected: bool = True,
) -> dict[str, Any]:
    """Create or update Gmail connection metadata without storing tokens."""
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO gmail_connections (
                profile_id,
                email,
                connected,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_id) DO UPDATE SET
                email = COALESCE(excluded.email, gmail_connections.email),
                connected = excluded.connected,
                updated_at = CURRENT_TIMESTAMP
            """,
            (profile_id, email, int(connected)),
        )
        await db.commit()
    connection = await get_gmail_connection(profile_id)
    if connection is None:
        raise RuntimeError("Gmail connection metadata could not be loaded")
    return connection


async def update_gmail_scan_metadata(
    profile_id: str,
    *,
    last_scanned: datetime | str,
    deadlines_found: int,
    needs_review: int = 0,
) -> dict[str, Any]:
    """Update scan metadata for a Gmail connection."""
    scanned_at = last_scanned.isoformat() if isinstance(last_scanned, datetime) else last_scanned
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO gmail_connections (
                profile_id,
                connected,
                last_scanned,
                deadlines_found,
                needs_review,
                created_at,
                updated_at
            )
            VALUES (?, FALSE, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_id) DO UPDATE SET
                last_scanned = excluded.last_scanned,
                deadlines_found = excluded.deadlines_found,
                needs_review = excluded.needs_review,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                profile_id,
                scanned_at,
                max(0, int(deadlines_found)),
                max(0, int(needs_review)),
            ),
        )
        await db.commit()
    connection = await get_gmail_connection(profile_id)
    if connection is None:
        raise RuntimeError("Gmail scan metadata could not be loaded")
    return connection


async def mark_gmail_disconnected(profile_id: str) -> dict[str, Any] | None:
    """Mark a Gmail account disconnected while preserving historical scan data."""
    existing = await get_gmail_connection(profile_id)
    if existing is None:
        return await upsert_gmail_connection(profile_id, connected=False)

    async with get_db() as db:
        await db.execute(
            """
            UPDATE gmail_connections
            SET connected = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE profile_id = ?
            """,
            (profile_id,),
        )
        await db.commit()
    return await get_gmail_connection(profile_id)
