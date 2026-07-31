"""Gmail OAuth and scan orchestration routes."""

import importlib
import inspect
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.models import (
    GmailDisconnectResponse,
    GmailScanRequest,
    GmailScanResponse,
    GmailStatusResponse,
)
from app.oauth_state import oauth_state_manager
from app.repositories.gmail_repository import (
    get_gmail_connection,
    mark_gmail_disconnected,
    update_gmail_scan_metadata,
    upsert_gmail_connection,
)
from app.repositories.profile_repository import get_profile_by_id
from app.websocket_manager import emit_trace


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/gmail",
    tags=["Gmail"],
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def _load_gmail_service() -> Any | None:
    """Load teammate-owned Gmail service if it is available."""
    try:
        return importlib.import_module("app.services.gmail_service")
    except ImportError as exc:
        logger.info("Gmail service unavailable: %s", exc)
        return None


def _load_guardian_agent() -> Any | None:
    """Load teammate-owned Guardian Agent if it is available."""
    try:
        return importlib.import_module("app.agents.guardian_agent")
    except ImportError as exc:
        logger.info("Guardian Agent unavailable: %s", exc)
        return None


async def _maybe_await(value: Any) -> Any:
    """Await coroutine values and return synchronous values unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value


async def _require_profile(profile_id: str) -> dict[str, Any]:
    """Return a profile or raise a 404 for public profile IDs."""
    clean_profile_id = profile_id.strip()
    if not clean_profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    profile = await get_profile_by_id(clean_profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return profile
