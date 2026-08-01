"""Active-package adapter for the external ResumeAI HTTP service."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from app.config import EXTERNAL_HTTP_TIMEOUT_SECONDS


RESUMEAI_URL_ENV = "RESUMEAI_API_URL"
RESUMEAI_KEY_ENV = "RESUMEAI_API_KEY"
_ENVELOPE_KEYS = ("data", "result", "resume", "parsed_resume", "profile")
_REQUIRED_PROFILE_FIELDS = (
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


class ResumeServiceError(Exception):
    """Base class for controlled ResumeAI integration failures."""


class ResumeAIConfigurationError(ResumeServiceError):
    """Raised when the ResumeAI endpoint is not configured."""


class ResumeAIConnectionError(ResumeServiceError):
    """Raised when the ResumeAI endpoint cannot be reached."""


class ResumeAITimeoutError(ResumeServiceError):
    """Raised when ResumeAI exceeds the configured timeout."""


class ResumeAIExtractionError(ResumeServiceError):
    """Raised when ResumeAI rejects or cannot extract the resume."""


class ResumeAIResponseError(ResumeServiceError):
    """Raised when ResumeAI returns an invalid response contract."""


@dataclass(frozen=True)
class ResumeAIResult:
    """Minimal result envelope consumed by the profile router."""

    success: bool
    data: dict[str, Any] | None
    error: str | None = None


async def forward_to_resumeai(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> ResumeAIResult:
    """Forward an uploaded resume to the configured ResumeAI HTTP endpoint."""
    url = os.getenv(RESUMEAI_URL_ENV, "").strip()
    if not url:
        raise ResumeAIConfigurationError("ResumeAI endpoint is not configured.")

    headers = {"Accept": "application/json"}
    api_key = os.getenv(RESUMEAI_KEY_ENV, "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    files = {
        "file": (
            filename or "resume.pdf",
            file_bytes,
            content_type or "application/octet-stream",
        )
    }
    try:
        async with httpx.AsyncClient(timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(url, files=files, headers=headers)
    except httpx.TimeoutException as exc:
        raise ResumeAITimeoutError("ResumeAI request timed out.") from exc
    except httpx.HTTPError as exc:
        raise ResumeAIConnectionError("ResumeAI endpoint is unavailable.") from exc

    if not response.is_success:
        raise ResumeAIExtractionError("ResumeAI rejected the extraction request.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ResumeAIResponseError("ResumeAI returned non-JSON content.") from exc
    if not isinstance(payload, dict):
        raise ResumeAIResponseError("ResumeAI returned an invalid JSON shape.")

    success = payload.get("success")
    if success is False:
        return ResumeAIResult(success=False, data=None, error="Extraction failed.")

    data = _unwrap(payload)
    if not isinstance(data, dict) or not data:
        raise ResumeAIResponseError("ResumeAI response contains no profile data.")
    return ResumeAIResult(success=True, data=data)


def map_resumeai_to_profile(
    resumeai_data: dict[str, Any] | Any,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Map Person C's structured ResumeAI payload to the active profile schema."""
    data = _as_dict(resumeai_data)
    data = _unwrap(data)
    education = _first_mapping(data, "education", "education_history")

    profile = {
        "profile_id": profile_id or str(uuid.uuid4()),
        "name": _text(data, "full_name", "name", "candidate_name"),
        "email": _text(data, "email", "email_address", "contact_email"),
        "year_of_study": _text(data, "year_of_study", "study_year"),
        "graduation_year": _year(
            _pick(data, "graduation_year")
            or _pick(education, "graduation_year", "end_year", "end_date", "to")
        ),
        "degree": _text(data, "degree", "qualification", "course")
        or _text(education, "degree", "qualification", "course"),
        "college": _text(data, "college", "institution", "university", "school")
        or _text(education, "institution", "college", "university", "school"),
        "skills": _string_list(data, "skills", "technical_skills", "skill_set"),
        "target_roles": _string_list(
            data, "target_roles", "preferred_roles", "desired_roles"
        ),
        "location": _text(data, "preferred_location", "location", "city"),
        "opportunity_type": _opportunity_type(
            _pick(data, "opportunity_type", "preferred_opportunity_type")
        ),
    }
    missing_fields = [
        name for name in _REQUIRED_PROFILE_FIELDS if not profile.get(name)
    ]
    return {"profile": profile, "missing_fields": missing_fields}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    raise ResumeAIResponseError("ResumeAI profile data is not an object.")


def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    for key in _ENVELOPE_KEYS:
        value = payload.get(key)
        if isinstance(value, dict) and value:
            return value
    return payload


def _pick(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return None


def _text(data: Mapping[str, Any], *keys: str) -> str | None:
    value = _pick(data, *keys)
    if value is None or isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def _string_list(data: Mapping[str, Any], *keys: str) -> list[str]:
    value = _pick(data, *keys)
    if isinstance(value, str):
        values: list[Any] = value.split(",")
    elif isinstance(value, list):
        values = value
    elif value is None:
        values = []
    else:
        values = [value]

    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if isinstance(item, dict):
            item = _pick(item, "name", "title", "skill", "value")
        if item is None or isinstance(item, (dict, list)):
            continue
        text = str(item).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _first_mapping(data: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    value = _pick(data, *keys)
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _year(value: Any) -> int | None:
    if isinstance(value, int) and 1900 <= value <= 2200:
        return value
    if value is None:
        return None
    match = re.search(r"\b(19|20|21)\d{2}\b", str(value))
    return int(match.group()) if match else None


def _opportunity_type(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().casefold().replace("_", " ")
    options = {
        "internship": "Internship",
        "full time": "Full-time",
        "full-time": "Full-time",
        "hackathon": "Hackathon",
        "all": "All",
    }
    return options.get(normalized)
