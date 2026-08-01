"""Active-package adapter for the existing ResumeAI service.

This module owns no ResumeAI or profile-mapping business logic.  It only
adapts the active router's byte-oriented contract to the legacy Person C
implementation and translates its return containers to active app schemas.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, TypeVar

import httpx

from app.config import EXTERNAL_HTTP_TIMEOUT_SECONDS
from app.models import ResumeAIResponse, StudentProfile


_T = TypeVar("_T")
logger = logging.getLogger(__name__)

RESUMEAI_EXTRACT_PATH = "/api/v1/profile/extract"


async def forward_to_resumeai(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> ResumeAIResponse:
    """Forward an upload using the confirmed active ResumeAI API contract."""
    base_url = os.getenv("RESUMEAI_API_URL", "").strip()
    if not base_url:
        return ResumeAIResponse(
            success=False,
            data=None,
            error="ResumeAI is not configured.",
        )

    endpoint = _resumeai_endpoint(base_url)
    headers = {"Accept": "application/json"}
    api_key = os.getenv("RESUMEAI_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.post(
                endpoint,
                files={"resume": (filename, file_bytes, content_type)},
                headers=headers,
            )
            response.raise_for_status()
            return ResumeAIResponse.model_validate(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("ResumeAI upload failed: %s", type(exc).__name__)
        return ResumeAIResponse(
            success=False,
            data=None,
            error="ResumeAI extraction failed.",
        )


def map_resumeai_to_profile(
    resumeai_data: dict[str, Any],
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Delegate profile mapping and expose its result in router-ready form."""
    mapped = _run_legacy_mapper(
        _person_c_resume().map_resumeai_to_profile(resumeai_data)
    )
    legacy_profile = mapped["profile"].model_dump()

    # Person C owns extraction and its canonical resume mapping. This boundary
    # adds the active fields returned by ResumeAI but absent from the legacy
    # StudentProfile schema.
    profile = StudentProfile(
        profile_id=profile_id,
        name=resumeai_data.get("full_name") or legacy_profile.get("full_name"),
        full_name=resumeai_data.get("full_name") or legacy_profile.get("full_name"),
        email=legacy_profile.get("email"),
        phone=legacy_profile.get("phone"),
        year_of_study=resumeai_data.get("year_of_study"),
        graduation_year=resumeai_data.get("graduation_year"),
        degree=None,
        college=None,
        target_roles=resumeai_data.get("target_roles") or [],
        skills=resumeai_data.get("skills") or legacy_profile.get("skills") or [],
        location=(
            resumeai_data.get("preferred_location")
            or legacy_profile.get("location")
        ),
        preferred_location=resumeai_data.get("preferred_location"),
        opportunity_type=resumeai_data.get("opportunity_type"),
    ).model_dump()

    required_fields = ("name", "skills", "target_roles", "location", "opportunity_type")
    missing_fields = [field for field in required_fields if not profile.get(field)]
    missing_fields.extend(("email", "degree", "college"))
    return {
        "profile": profile,
        "missing_fields": missing_fields,
    }


def _run_legacy_mapper(awaitable: Awaitable[_T]) -> _T:
    """Run the legacy async mapper behind the active synchronous contract."""
    def invoke() -> _T:
        return asyncio.run(awaitable)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(invoke).result()


def _person_c_resume() -> Any:
    """Resolve the legacy implementation only at the adapter boundary."""
    return importlib.import_module("services.resume_service")


def _resumeai_endpoint(base_url: str) -> str:
    """Accept either the documented base URL or an already-complete endpoint."""
    normalized = base_url.rstrip("/")
    if normalized.endswith(RESUMEAI_EXTRACT_PATH):
        return normalized
    return f"{normalized}{RESUMEAI_EXTRACT_PATH}"
