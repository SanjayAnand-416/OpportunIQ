"""Profile API routes for the OpportunIQ backend."""

import logging
import sqlite3
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.models import ManualProfileCreate, ProfileCreateResponse, ProfileResponse, StudentProfile
from app.repositories import profile_repository


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/profile",
    tags=["Profile"],
)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 5 * 1024 * 1024

REQUIRED_PROFILE_FIELDS = (
    "name",
    "email",
    "year_of_study",
    "degree",
    "college",
    "skills",
    "target_roles",
    "location",
    "opportunity_type",
)


def _dedupe_strings(values: list[str] | None) -> list[str]:
    """Trim and deduplicate strings case-insensitively while preserving order."""
    if not values:
        return []

    seen: set[str] = set()
    clean_values: list[str] = []
    for value in values:
        clean_value = str(value).strip()
        lookup = clean_value.lower()
        if not clean_value or lookup in seen:
            continue
        seen.add(lookup)
        clean_values.append(clean_value)
    return clean_values


def _clean_text(value: Any) -> Any:
    """Trim text values and leave non-text values unchanged."""
    if isinstance(value, str):
        return value.strip()
    return value


def _build_student_profile(profile_id: str, payload: Mapping[str, Any]) -> StudentProfile:
    """Build a StudentProfile from normalized API or ResumeAI-mapped data."""
    return StudentProfile(
        profile_id=profile_id,
        name=_clean_text(payload.get("name")),
        email=_clean_text(payload.get("email")),
        year_of_study=_clean_text(payload.get("year_of_study")),
        graduation_year=payload.get("graduation_year"),
        degree=_clean_text(payload.get("degree")),
        college=_clean_text(payload.get("college")),
        skills=_dedupe_strings(payload.get("skills")),
        target_roles=_dedupe_strings(payload.get("target_roles")),
        location=_clean_text(payload.get("location")),
        opportunity_type=_clean_text(payload.get("opportunity_type")),
    )


def _find_missing_fields(profile: Mapping[str, Any]) -> list[str]:
    """Return required profile fields that are absent or empty."""
    missing_fields: list[str] = []
    for field_name in REQUIRED_PROFILE_FIELDS:
        value = profile.get(field_name)
        if isinstance(value, list):
            if not value:
                missing_fields.append(field_name)
        elif value is None or (isinstance(value, str) and not value.strip()):
            missing_fields.append(field_name)
    return missing_fields


def _file_extension(filename: str) -> str:
    """Return the normalized extension for an uploaded file name."""
    return Path(filename).suffix.lower()


@router.post(
    "/manual",
    response_model=ProfileCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_profile(payload: ManualProfileCreate) -> ProfileCreateResponse:
    """Create a student profile from manual entry."""
    profile_id = str(uuid.uuid4())
    profile = _build_student_profile(profile_id, payload.model_dump())

    try:
        created_profile = await profile_repository.create_profile(profile)
    except sqlite3.IntegrityError as exc:
        logger.warning("Profile ID conflict while creating profile: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile could not be created due to an identifier conflict.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected database error while creating profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile could not be created.",
        ) from exc

    profile_response = ProfileResponse(**created_profile)
    return ProfileCreateResponse(
        profile_id=profile_response.profile_id,
        profile=profile_response,
        missing_fields=[],
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str) -> ProfileResponse:
    """Retrieve a student profile by ID."""
    if not profile_id.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    profile = await profile_repository.get_profile_by_id(profile_id.strip())
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return ProfileResponse(**profile)
