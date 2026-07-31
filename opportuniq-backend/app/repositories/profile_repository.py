"""Persistence helpers for student profiles."""

import json
from collections.abc import Mapping
from typing import Any

import aiosqlite

from app.database import get_db
from app.models import StudentProfile


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


def _profile_value(profile: StudentProfile, field_name: str, fallback: str | None = None) -> Any:
    """Read a profile field while supporting legacy schema aliases."""
    value = getattr(profile, field_name, None)
    if value is None and fallback is not None:
        return getattr(profile, fallback, None)
    return value


async def create_profile(profile: StudentProfile) -> dict[str, Any]:
    """Persist a new student profile and return the public profile shape."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO student_profiles (
                name,
                email,
                year_of_study,
                graduation_year,
                degree,
                college,
                target_roles,
                skills,
                location,
                opportunity_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _profile_value(profile, "name", "full_name"),
                profile.email,
                profile.year_of_study,
                profile.graduation_year,
                _profile_value(profile, "degree"),
                _profile_value(profile, "college"),
                _serialize_list(profile.target_roles),
                _serialize_list(profile.skills),
                _profile_value(profile, "location", "preferred_location"),
                profile.opportunity_type,
            ),
        )
        await db.commit()
        profile_id = str(cursor.lastrowid)
        await cursor.close()

    created_profile = await get_profile_by_id(profile_id)
    if created_profile is None:
        raise RuntimeError("Created profile could not be loaded")
    return created_profile


async def get_profile_by_id(profile_id: str) -> dict[str, Any] | None:
    """Load a student profile by API profile ID."""
    async with get_db() as db:
        cursor = await db.execute(
            f"SELECT {', '.join(PROFILE_COLUMNS)} FROM student_profiles WHERE id = ?",
            (profile_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
    return row_to_profile(row)
