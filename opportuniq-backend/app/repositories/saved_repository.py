"""Persistence and joined queries for saved opportunities."""

import uuid
from collections.abc import Mapping
from typing import Any

from app.database import get_db
from app.repositories.opportunity_repository import _deserialize_list


STATUS_ALIASES = {
    "not applied": "Not Applied", "not_applied": "Not Applied",
    "applied": "Applied", "interview": "Interview Scheduled",
    "interview scheduled": "Interview Scheduled", "interview_scheduled": "Interview Scheduled",
    "offer": "Offer Received", "offer received": "Offer Received",
    "offer_received": "Offer Received", "rejected": "Rejected",
}
SELECT_JOINED = """
SELECT s.id AS saved_id, s.profile_id, s.opportunity_id, s.status, s.notes,
       s.saved_at, s.updated_at, o.title,
       COALESCE(o.company, o.organization, '') AS company,
       COALESCE(o.platform, o.source, '') AS platform,
       COALESCE(o.url, '') AS url, o.location, o.deadline,
       o.match_score, o.combined_score, o.skills_required, o.also_on
FROM saved_opportunities s JOIN opportunities o ON o.opportunity_id = s.opportunity_id
"""


def normalize_application_status(value: str) -> str:
    clean = str(value or "").strip().lower().replace("-", " ")
    if clean not in STATUS_ALIASES:
        raise ValueError("Unsupported application status.")
    return STATUS_ALIASES[clean]


def row_to_saved_opportunity(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["saved_id"] = str(item["saved_id"])
    item["profile_id"] = str(item["profile_id"])
    item["opportunity_id"] = str(item["opportunity_id"])
    item["skills_required"] = _deserialize_list(item.get("skills_required"))
    item["also_on"] = _deserialize_list(item.get("also_on"))
    for field in ("match_score", "combined_score"):
        try: item[field] = float(item.get(field) or 0)
        except (TypeError, ValueError): item[field] = 0.0
    return item


async def get_saved_by_id(saved_id: str) -> dict[str, Any] | None:
    async with get_db() as db:
        cursor = await db.execute(SELECT_JOINED + " WHERE s.id = ?", (saved_id,))
        row = await cursor.fetchone(); await cursor.close()
    return row_to_saved_opportunity(row)


async def get_saved_by_profile_and_opportunity(profile_id: str, opportunity_id: str) -> dict[str, Any] | None:
    async with get_db() as db:
        cursor = await db.execute(SELECT_JOINED + " WHERE s.profile_id = ? AND s.opportunity_id = ?", (profile_id, opportunity_id))
        row = await cursor.fetchone(); await cursor.close()
    return row_to_saved_opportunity(row)


async def save_opportunity(*, profile_id: str, opportunity_id: str) -> dict[str, Any]:
    existing = await get_saved_by_profile_and_opportunity(profile_id, opportunity_id)
    if existing: return existing
    async with get_db() as db:
        cursor = await db.execute("SELECT 1 FROM opportunities WHERE opportunity_id = ?", (opportunity_id,))
        opportunity = await cursor.fetchone(); await cursor.close()
        if opportunity is None: raise ValueError("Opportunity not found.")
        saved_id = str(uuid.uuid4())
        await db.execute("INSERT INTO saved_opportunities (id, profile_id, opportunity_id, status) VALUES (?, ?, ?, 'Not Applied')", (saved_id, profile_id, opportunity_id))
        await db.commit()
    result = await get_saved_by_id(saved_id)
    if result is None: raise RuntimeError("Saved opportunity could not be loaded.")
    return result


async def list_saved_opportunities(profile_id: str, *, status: str | None = None, platform: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    clauses = ["s.profile_id = ?"]; values: list[Any] = [profile_id]
    if status is not None: clauses.append("s.status = ?"); values.append(normalize_application_status(status))
    if platform: clauses.append("LOWER(COALESCE(o.platform, o.source, '')) = LOWER(?)"); values.append(platform.strip())
    values.append(max(1, min(int(limit), 200)))
    async with get_db() as db:
        cursor = await db.execute(SELECT_JOINED + f" WHERE {' AND '.join(clauses)} ORDER BY s.saved_at DESC, s.id DESC LIMIT ?", values)
        rows = await cursor.fetchall(); await cursor.close()
    return [item for row in rows if (item := row_to_saved_opportunity(row))]


async def update_saved_opportunity(saved_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    existing = await get_saved_by_id(saved_id)
    if existing is None: return None
    clean: dict[str, Any] = {}
    if "status" in updates: clean["status"] = normalize_application_status(updates["status"])
    if "notes" in updates: clean["notes"] = str(updates["notes"]).strip() or None if updates["notes"] is not None else None
    if not clean: return existing
    clause = ", ".join(f"{key} = ?" for key in clean)
    async with get_db() as db:
        await db.execute(f"UPDATE saved_opportunities SET {clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [*clean.values(), saved_id]); await db.commit()
    return await get_saved_by_id(saved_id)


async def delete_saved_opportunity(saved_id: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM saved_opportunities WHERE id = ?", (saved_id,)); await db.commit()
        deleted = cursor.rowcount; await cursor.close()
    return bool(deleted)
