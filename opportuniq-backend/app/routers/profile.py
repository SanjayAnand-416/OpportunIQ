"""Profile API routes for the OpportunIQ backend."""

import logging
import sqlite3
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.models import (
    ManualProfileCreate,
    ProfileCreateResponse,
    ProfileResponse,
    ProfileUpdate,
    ProfileUpdateResponse,
    StudentProfile,
)
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


def _resume_service_functions():
    """Resolve teammate-owned ResumeAI functions without breaking app startup."""
    try:
        from app.services.resume_service import forward_to_resumeai, map_resumeai_to_profile
    except ImportError as exc:
        logger.info("ResumeAI service is unavailable: %s", exc)
        return None, None
    return forward_to_resumeai, map_resumeai_to_profile


def _resume_error_response(exc: Exception) -> JSONResponse | None:
    """Translate active adapter exceptions without exposing provider details."""
    responses = {
        "ResumeAIConfigurationError": (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Resume extraction service is not available.",
        ),
        "ResumeAIConnectionError": (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Resume extraction service is not available.",
        ),
        "ResumeAITimeoutError": (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Resume extraction service timed out.",
        ),
        "ResumeAIExtractionError": (
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Resume extraction failed.",
        ),
        "ResumeAIResponseError": (
            status.HTTP_502_BAD_GATEWAY,
            "Resume extraction returned an invalid response.",
        ),
    }
    response = responses.get(type(exc).__name__)
    if response is None:
        return None
    status_code, detail = response
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "fallback": "manual"},
    )


def _normalize_update_payload(updates: dict[str, Any]) -> dict[str, Any]:
    """Normalize patch payload values before persistence."""
    normalized: dict[str, Any] = {}
    for field_name, value in updates.items():
        if field_name in {"skills", "target_roles"}:
            clean_values = _dedupe_strings(value)
            if not clean_values:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field_name} cannot be empty.",
                )
            normalized[field_name] = clean_values
        elif field_name in {"name", "location", "opportunity_type"}:
            clean_value = _clean_text(value)
            if clean_value is None or not clean_value:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field_name} cannot be empty.",
                )
            normalized[field_name] = clean_value
        elif isinstance(value, str):
            normalized[field_name] = value.strip()
        else:
            normalized[field_name] = value
    return normalized


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


@router.patch("/{profile_id}", response_model=ProfileUpdateResponse)
async def patch_profile(profile_id: str, payload: ProfileUpdate) -> ProfileUpdateResponse:
    """Partially update a student profile."""
    clean_profile_id = profile_id.strip()
    if not clean_profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    updates = _normalize_update_payload(payload.model_dump(exclude_unset=True))
    updated_profile = await profile_repository.update_profile(clean_profile_id, updates)
    if updated_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    profile_response = ProfileResponse(**updated_profile)
    return ProfileUpdateResponse(
        success=True,
        profile=profile_response,
        missing_fields=_find_missing_fields(updated_profile),
    )


@router.post(
    "/upload",
    response_model=ProfileCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume_profile(
    file: UploadFile = File(...),
) -> ProfileCreateResponse | JSONResponse:
    """Create a profile by forwarding an uploaded resume to ResumeAI."""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a PDF, DOC, or DOCX file.",
        )

    if _file_extension(filename) not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a PDF, DOC, or DOCX file.",
        )

    content_type = file.content_type or ""
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Upload a PDF, DOC, or DOCX file.",
        )

    try:
        file_bytes = await file.read()
    finally:
        await file.close()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 5 MB limit.",
        )

    forward_to_resumeai, map_resumeai_to_profile = _resume_service_functions()
    if forward_to_resumeai is None or map_resumeai_to_profile is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Resume extraction service is not available.",
                "fallback": "manual",
            },
        )

    try:
        response = await forward_to_resumeai(file_bytes, filename, content_type)
    except Exception as exc:
        controlled_response = _resume_error_response(exc)
        if controlled_response is not None:
            logger.warning("Resume extraction integration failed: %s", type(exc).__name__)
            return controlled_response
        logger.exception("Unexpected resume extraction failure")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Resume extraction could not be completed.",
                "fallback": "manual",
            },
        )

    if not response.success or response.data is None:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Resume extraction failed.",
                "fallback": "manual",
            },
        )

    resume_data = (
        response.data.model_dump()
        if hasattr(response.data, "model_dump")
        else response.data
    )
    profile_id = str(uuid.uuid4())
    try:
        mapped = map_resumeai_to_profile(resume_data, profile_id=profile_id)
    except Exception as exc:
        controlled_response = _resume_error_response(exc)
        if controlled_response is not None:
            logger.warning("Resume extraction mapping failed: %s", type(exc).__name__)
            return controlled_response
        logger.exception("Unexpected resume extraction mapping failure")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Resume extraction could not be completed.",
                "fallback": "manual",
            },
        )
    profile_payload = mapped.get("profile", {})
    profile = _build_student_profile(
        str(profile_payload.get("profile_id") or profile_id),
        profile_payload,
    )

    try:
        created_profile = await profile_repository.create_profile(profile)
    except Exception as exc:
        logger.exception("Unexpected database error while creating resume profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile could not be created.",
        ) from exc

    profile_response = ProfileResponse(**created_profile)
    return ProfileCreateResponse(
        profile_id=profile_response.profile_id,
        profile=profile_response,
        missing_fields=mapped.get("missing_fields") or _find_missing_fields(created_profile),
    )
