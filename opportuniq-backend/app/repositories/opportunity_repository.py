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
