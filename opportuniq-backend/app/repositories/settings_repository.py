"""Persistence for per-profile reminder preferences."""

from typing import Any
from app.database import get_db

FIELDS = ("r_7d", "r_3d", "r_1d", "r_same_day")


def _map(row) -> dict[str, Any]:
    data = dict(row)
    return {"profile_id": str(data["profile_id"]), **{field: bool(int(data.get(field, 1))) for field in FIELDS}}


async def get_notification_settings(profile_id: str) -> dict[str, Any]:
    async with get_db() as db:
        await db.execute("INSERT OR IGNORE INTO notification_settings (profile_id) VALUES (?)", (profile_id,)); await db.commit()
        cursor = await db.execute(f"SELECT profile_id, {', '.join(FIELDS)} FROM notification_settings WHERE profile_id = ?", (profile_id,))
        row = await cursor.fetchone(); await cursor.close()
    return _map(row)


async def update_notification_settings(profile_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    current = await get_notification_settings(profile_id)
    clean = {field: int(bool(value)) for field, value in updates.items() if field in FIELDS and value is not None}
    if not clean: return current
    clause = ", ".join(f"{field} = ?" for field in clean)
    async with get_db() as db:
        await db.execute(f"UPDATE notification_settings SET {clause}, updated_at = CURRENT_TIMESTAMP WHERE profile_id = ?", [*clean.values(), profile_id]); await db.commit()
    return await get_notification_settings(profile_id)
