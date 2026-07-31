"""Persistence helpers for discovered opportunities."""

import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import aiosqlite

from app.database import get_db


OPPORTUNITY_COLUMNS = (
    "id",
    "opportunity_id",
    "session_id",
    "profile_id",
    "title",
    "company",
    "platform",
    "url",
    "url_hash",
    "location",
    "deadline",
    "stipend_or_prize",
    "eligibility",
    "skills_required",
    "description",
    "also_on",
    "match_score",
    "urgency_score",
    "combined_score",
    "is_expired",
    "fetched_at",
)


def _serialize_list(value: list[str] | None) -> str:
    """Serialize a list field for SQLite storage."""
    if value is None:
        return "[]"
    return json.dumps([str(item) for item in value])


def _deserialize_list(value: str | None) -> list[str]:
    """Deserialize a JSON list field without failing on malformed data."""
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded]


def _float_value(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def row_to_opportunity(
    row: aiosqlite.Row | Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Convert a SQLite opportunity row into the public API shape."""
    if row is None:
        return None

    row_data = dict(row)
    opportunity = {
        column: row_data.get(column)
        for column in OPPORTUNITY_COLUMNS
        if column in row_data
    }
    internal_id = opportunity.pop("id", None)
    opportunity["opportunity_id"] = str(opportunity.get("opportunity_id") or internal_id)
    opportunity.pop("url_hash", None)
    opportunity["skills_required"] = _deserialize_list(opportunity.get("skills_required"))
    opportunity["also_on"] = _deserialize_list(opportunity.get("also_on"))
    opportunity["match_score"] = _float_value(opportunity.get("match_score"))
    opportunity["urgency_score"] = _float_value(opportunity.get("urgency_score"))
    opportunity["combined_score"] = _float_value(opportunity.get("combined_score"))
    opportunity["is_expired"] = bool(opportunity.get("is_expired"))
    return opportunity


def _normalize_url_hash(url: str, url_hash: str | None = None) -> str:
    normalized_url = url.strip().lower()
    return url_hash or hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


def _clean_opportunity(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    title = str(raw.get("title") or "").strip()
    company = str(raw.get("company") or raw.get("organization") or "").strip()
    url = str(raw.get("url") or "").strip()
    if not title or not company or not url:
        return None
    if bool(raw.get("is_expired")):
        return None
    platform = str(raw.get("platform") or raw.get("source") or "unknown").strip() or "unknown"
    return {
        "opportunity_id": str(raw.get("opportunity_id") or uuid.uuid4()),
        "title": title,
        "company": company,
        "platform": platform,
        "url": url,
        "url_hash": _normalize_url_hash(url, raw.get("url_hash")),
        "location": raw.get("location"),
        "deadline": raw.get("deadline"),
        "stipend_or_prize": raw.get("stipend_or_prize"),
        "eligibility": raw.get("eligibility"),
        "skills_required": raw.get("skills_required") or raw.get("skills") or [],
        "description": raw.get("description"),
        "also_on": raw.get("also_on") or [],
        "match_score": _float_value(raw.get("match_score")),
        "urgency_score": _float_value(raw.get("urgency_score")),
        "combined_score": _float_value(raw.get("combined_score")),
        "is_expired": 0,
    }


async def delete_opportunities_by_session(session_id: str) -> int:
    """Delete all opportunities for one discovery session."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM opportunities WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()
        deleted = cursor.rowcount
        await cursor.close()
    return int(deleted or 0)


async def save_opportunities(
    *,
    session_id: str,
    profile_id: str,
    opportunities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Persist valid opportunities for a discovery session in ranked order."""
    seen_hashes: set[str] = set()
    clean_opportunities: list[dict[str, Any]] = []
    for raw in opportunities:
        clean = _clean_opportunity(raw)
        if clean is None or clean["url_hash"] in seen_hashes:
            continue
        seen_hashes.add(clean["url_hash"])
        clean_opportunities.append(clean)

    if not clean_opportunities:
        return []

    async with get_db() as db:
        for opportunity in clean_opportunities:
            await db.execute(
                """
                INSERT INTO opportunities (
                    opportunity_id,
                    session_id,
                    profile_id,
                    source,
                    title,
                    company,
                    platform,
                    organization,
                    location,
                    url,
                    url_hash,
                    description,
                    deadline,
                    stipend_or_prize,
                    eligibility,
                    skills_required,
                    also_on,
                    match_score,
                    urgency_score,
                    combined_score,
                    is_expired,
                    fetched_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    opportunity["opportunity_id"],
                    session_id,
                    profile_id,
                    opportunity["platform"],
                    opportunity["title"],
                    opportunity["company"],
                    opportunity["platform"],
                    opportunity["company"],
                    opportunity["location"],
                    opportunity["url"],
                    opportunity["url_hash"],
                    opportunity["description"],
                    opportunity["deadline"],
                    opportunity["stipend_or_prize"],
                    opportunity["eligibility"],
                    _serialize_list(opportunity["skills_required"]),
                    _serialize_list(opportunity["also_on"]),
                    opportunity["match_score"],
                    opportunity["urgency_score"],
                    opportunity["combined_score"],
                    opportunity["is_expired"],
                ),
            )
        await db.commit()

    return await get_opportunities_by_session(session_id, limit=len(clean_opportunities))
