"""Persistence helpers for student profiles."""

import json
from collections.abc import Mapping
from typing import Any

import aiosqlite


PROFILE_COLUMNS = (
    "id",
    "name",
    "email",
    "year_of_study",
    "graduation_year",
    "degree",
    "college",
    "target_roles",
    "skills",
    "location",
    "opportunity_type",
    "created_at",
    "updated_at",
)


def _serialize_list(value: list[str] | None) -> str:
    """Serialize a list field for SQLite storage."""
    if value is None:
        return "[]"
    return json.dumps([str(item) for item in value])


def _deserialize_list(value: str | None) -> list[str]:
    """Deserialize a JSON list field without failing on legacy bad data."""
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded]


def row_to_profile(row: aiosqlite.Row | Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Convert a SQLite profile row into the public API shape."""
    if row is None:
        return None

    row_data = dict(row)
    profile = {column: row_data.get(column) for column in PROFILE_COLUMNS if column in row_data}
    profile["profile_id"] = str(profile.pop("id"))
    profile["skills"] = _deserialize_list(profile.get("skills"))
    profile["target_roles"] = _deserialize_list(profile.get("target_roles"))
    return profile
