"""Module 1 — Resume ingestion.

Forwards an uploaded resume PDF to the external ResumeAI API and maps the
structured response onto the canonical :class:`~models.StudentProfile`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, TypedDict

import httpx
from fastapi import UploadFile

from models import (
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    StudentProfile,
)

logger = logging.getLogger(__name__)

RESUMEAI_URL_ENV = "RESUMEAI_API_URL"
RESUMEAI_KEY_ENV = "RESUMEAI_API_KEY"
REQUEST_TIMEOUT_SECONDS = 30.0

# ResumeAI wraps its payload inconsistently depending on deployment; unwrap
# these envelope keys before mapping.
_ENVELOPE_KEYS = ("data", "result", "resume", "parsed_resume", "profile")


class ResumeServiceError(Exception):
    """Base error for every failure raised by this service."""


class ResumeAIConfigurationError(ResumeServiceError):
    """Raised when required ResumeAI configuration is absent."""


class ResumeAITimeoutError(ResumeServiceError):
    """Raised when ResumeAI does not respond within the timeout window."""


class ResumeAIResponseError(ResumeServiceError):
    """Raised when ResumeAI returns an error status or an unusable body."""


class ProfileExtraction(TypedDict):
    """Return shape of :func:`map_resumeai_to_profile`."""

    profile: StudentProfile
    missing_fields: list[str]


async def forward_to_resumeai(file: UploadFile) -> dict[str, Any]:
    """Upload a resume file to ResumeAI and return its decoded JSON body.

    Args:
        file: The resume uploaded by the client (expected to be a PDF).

    Returns:
        The parsed JSON object returned by ResumeAI.

    Raises:
        ResumeAIConfigurationError: ``RESUMEAI_API_URL`` is not configured.
        ResumeAITimeoutError: ResumeAI exceeded the 30 second timeout.
        ResumeAIResponseError: The upload was empty, the network call failed,
            ResumeAI returned a non-2xx status, or the body was not a JSON
            object.
    """
    url = os.getenv(RESUMEAI_URL_ENV, "").strip()
    if not url:
        raise ResumeAIConfigurationError(f"{RESUMEAI_URL_ENV} environment variable is not set.")

    content = await file.read()
    if not content:
        raise ResumeAIResponseError("Uploaded resume file is empty.")

    filename = file.filename or "resume.pdf"
    files = {"file": (filename, content, file.content_type or "application/pdf")}

    headers: dict[str, str] = {"Accept": "application/json"}
    api_key = os.getenv(RESUMEAI_KEY_ENV, "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    logger.info("Forwarding resume '%s' (%d bytes) to ResumeAI", filename, len(content))

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(url, files=files, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        logger.error("ResumeAI request timed out after %ss", REQUEST_TIMEOUT_SECONDS)
        raise ResumeAITimeoutError(
            f"ResumeAI did not respond within {REQUEST_TIMEOUT_SECONDS:.0f} seconds."
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "ResumeAI returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise ResumeAIResponseError(f"ResumeAI returned HTTP {exc.response.status_code}.") from exc
    except httpx.HTTPError as exc:
        logger.exception("ResumeAI request failed")
        raise ResumeAIResponseError(f"ResumeAI request failed: {exc}") from exc
    except ValueError as exc:
        logger.error("ResumeAI returned a non-JSON body")
        raise ResumeAIResponseError("ResumeAI returned a non-JSON body.") from exc

    if not isinstance(payload, dict):
        logger.error("ResumeAI returned %s, expected a JSON object", type(payload).__name__)
        raise ResumeAIResponseError("ResumeAI returned an unexpected JSON shape.")

    logger.info("ResumeAI parsed resume '%s' successfully", filename)
    return payload


async def map_resumeai_to_profile(raw_response: dict[str, Any]) -> ProfileExtraction:
    """Map a ResumeAI payload onto a :class:`StudentProfile`.

    Args:
        raw_response: The JSON object returned by :func:`forward_to_resumeai`.

    Returns:
        A mapping with the populated ``profile`` and the ``missing_fields``
        that ResumeAI could not fill (``None``, blank string, or empty list).

    Raises:
        ResumeAIResponseError: The payload could not be mapped onto the
            profile schema.
    """
    data = _unwrap(raw_response)

    try:
        profile = StudentProfile(
            full_name=_text(data, "full_name", "name", "candidate_name"),
            email=_text(data, "email", "email_address", "contact_email"),
            phone=_text(data, "phone", "phone_number", "mobile", "contact_number"),
            location=_text(data, "location", "address", "city"),
            summary=_text(data, "summary", "objective", "about", "profile_summary"),
            linkedin_url=_text(data, "linkedin_url", "linkedin", "linkedIn"),
            github_url=_text(data, "github_url", "github"),
            portfolio_url=_text(data, "portfolio_url", "portfolio", "website"),
            skills=_str_list(data, "skills", "technical_skills", "skill_set"),
            certifications=_str_list(data, "certifications", "certificates"),
            languages=_str_list(data, "languages", "languages_known"),
            education=[
                _education(item) for item in _entries(data, "education", "education_history")
            ],
            experience=[
                _experience(item)
                for item in _entries(
                    data, "experience", "work_experience", "employment", "internships"
                )
            ],
            projects=[_project(item) for item in _entries(data, "projects")],
        )
    except Exception as exc:  # pydantic validation or unexpected member types
        logger.exception("Failed to map ResumeAI response to StudentProfile")
        raise ResumeAIResponseError(
            f"Could not map ResumeAI response to a student profile: {exc}"
        ) from exc

    missing_fields = _missing_fields(profile)
    logger.info(
        "Mapped ResumeAI response; %d missing field(s): %s",
        len(missing_fields),
        missing_fields,
    )
    return {"profile": profile, "missing_fields": missing_fields}


def _unwrap(raw_response: dict[str, Any]) -> dict[str, Any]:
    """Return the inner payload when ResumeAI wraps it in an envelope key."""
    for key in _ENVELOPE_KEYS:
        inner = raw_response.get(key)
        if isinstance(inner, dict) and inner:
            logger.debug("Unwrapped ResumeAI payload from envelope key '%s'", key)
            return inner
    return raw_response


def _pick(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-``None`` value among ``keys``."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _text(data: dict[str, Any], *keys: str) -> str | None:
    """Return the first key's value coerced to a trimmed, non-empty string."""
    value = _pick(data, *keys)
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def _str_list(data: dict[str, Any], *keys: str) -> list[str]:
    """Return the first key's value as a list of trimmed, non-empty strings."""
    return _coerce_str_list(_pick(data, *keys))


def _coerce_str_list(value: Any) -> list[str]:
    """Coerce a scalar, comma-separated string, or list into a string list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                # Skill/certification objects such as {"name": "Python"}.
                item = _pick(item, "name", "title", "skill", "value")
            if item is None or isinstance(item, (dict, list)):
                continue
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def _entries(data: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    """Return the first key's value as a list of dict entries."""
    value = _pick(data, *keys)
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _education(item: dict[str, Any]) -> EducationEntry:
    """Map one ResumeAI education entry."""
    return EducationEntry(
        degree=_text(item, "degree", "qualification", "course"),
        institution=_text(item, "institution", "school", "college", "university"),
        field_of_study=_text(item, "field_of_study", "major", "specialization", "branch"),
        start_year=_text(item, "start_year", "start_date", "from"),
        end_year=_text(item, "end_year", "end_date", "to", "graduation_year"),
        grade=_text(item, "grade", "gpa", "cgpa", "percentage", "score"),
    )


def _experience(item: dict[str, Any]) -> ExperienceEntry:
    """Map one ResumeAI work/internship entry."""
    return ExperienceEntry(
        title=_text(item, "title", "role", "position", "job_title"),
        organization=_text(item, "organization", "company", "employer"),
        start_date=_text(item, "start_date", "from", "start"),
        end_date=_text(item, "end_date", "to", "end"),
        description=_text(item, "description", "summary", "details", "responsibilities"),
    )


def _project(item: dict[str, Any]) -> ProjectEntry:
    """Map one ResumeAI project entry."""
    return ProjectEntry(
        name=_text(item, "name", "title", "project_name"),
        description=_text(item, "description", "summary", "details"),
        technologies=_coerce_str_list(_pick(item, "technologies", "tech_stack", "tools", "skills")),
    )


def _missing_fields(profile: StudentProfile) -> list[str]:
    """List profile fields left null, blank, or empty by ResumeAI."""
    missing: list[str] = []
    for name in type(profile).model_fields:
        value = getattr(profile, name)
        if value is None or (isinstance(value, (str, list)) and not value):
            missing.append(name)
    return missing
