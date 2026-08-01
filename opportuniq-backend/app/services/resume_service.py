"""Active-package adapter for the existing ResumeAI service.

This module owns no ResumeAI or profile-mapping business logic.  It only
adapts the active router's byte-oriented contract to the legacy Person C
implementation and translates its return containers to active app schemas.
"""

from __future__ import annotations

import asyncio
import importlib
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Any, Awaitable, TypeVar

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.models import ResumeAIResponse


_T = TypeVar("_T")


async def forward_to_resumeai(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> ResumeAIResponse:
    """Forward an active-router upload through the legacy ResumeAI client."""
    upload = UploadFile(
        file=BytesIO(file_bytes),
        size=len(file_bytes),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )
    try:
        payload = await _person_c_resume().forward_to_resumeai(upload)
    finally:
        await upload.close()
    return ResumeAIResponse.model_validate(payload)


def map_resumeai_to_profile(
    resumeai_data: dict[str, Any],
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Delegate profile mapping and expose its result in router-ready form."""
    mapped = _run_legacy_mapper(
        _person_c_resume().map_resumeai_to_profile(resumeai_data)
    )
    profile = mapped["profile"].model_dump()

    # Translate only the identity aliases at the package boundary. All field
    # extraction and missing-field decisions remain owned by Person C's mapper.
    profile["profile_id"] = profile_id
    profile["name"] = profile.get("full_name")
    return {
        "profile": profile,
        "missing_fields": mapped["missing_fields"],
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
