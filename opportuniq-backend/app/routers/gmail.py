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


def _build_authorization_url(gmail_service: Any, profile_id: str, state: str) -> str:
    """Build a Google authorization URL using the teammate service interface."""
    get_authorization_url = getattr(gmail_service, "get_authorization_url", None)
    if get_authorization_url is not None:
        return get_authorization_url(profile_id=profile_id, state=state)

    get_oauth_flow = getattr(gmail_service, "get_oauth_flow", None)
    if get_oauth_flow is None:
        raise RuntimeError("Gmail service does not expose an OAuth URL interface")

    flow = get_oauth_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return authorization_url


@router.get("/connect")
async def connect_gmail(profile_id: str = Query(...)) -> RedirectResponse:
    """Redirect a profile owner to Google's Gmail OAuth consent screen."""
    profile = await _require_profile(profile_id)
    public_profile_id = str(profile["profile_id"])

    gmail_service = _load_gmail_service()
    if gmail_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration service is not available.",
        )

    state = oauth_state_manager.create_state(public_profile_id)
    try:
        authorization_url = _build_authorization_url(
            gmail_service,
            public_profile_id,
            state,
        )
    except Exception as exc:
        logger.warning("Unable to build Gmail authorization URL: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration service is not available.",
        ) from exc

    return RedirectResponse(url=authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


async def run_guardian_scan_task(profile_id: str, session_id: str) -> None:
    """Run teammate-owned Guardian Agent and update safe scan metadata."""
    guardian_agent = _load_guardian_agent()
    if guardian_agent is None:
        await emit_trace(
            session_id,
            "guardian",
            "error",
            "Guardian Agent is not available",
            {"profile_id": profile_id},
        )
        return

    runner = getattr(guardian_agent, "run_guardian_agent", None)
    if runner is None:
        await emit_trace(
            session_id,
            "guardian",
            "error",
            "Guardian Agent is not available",
            {"profile_id": profile_id},
        )
        return

    await emit_trace(
        session_id,
        "guardian",
        "running",
        "Gmail deadline scan started",
        {"profile_id": profile_id},
    )
    try:
        try:
            result = await _maybe_await(runner(profile_id=profile_id, session_id=session_id))
        except TypeError:
            result = await _maybe_await(runner(profile_id=profile_id))
        result = result if isinstance(result, dict) else {}
        await update_gmail_scan_metadata(
            profile_id,
            last_scanned=datetime.now(UTC),
            deadlines_found=int(result.get("deadlines_found") or 0),
            needs_review=int(result.get("needs_review") or 0),
        )
        await emit_trace(
            session_id,
            "guardian",
            "complete",
            "Gmail deadline scan complete",
            {
                "emails_scanned": int(result.get("emails_scanned") or 0),
                "deadlines_found": int(result.get("deadlines_found") or 0),
                "needs_review": int(result.get("needs_review") or 0),
                "errors": result.get("errors") or [],
            },
        )
    except Exception as exc:
        logger.warning("Guardian scan failed safely: %s", exc)
        await emit_trace(
            session_id,
            "guardian",
            "error",
            "Gmail deadline scan failed",
            {"profile_id": profile_id},
        )


def _exchange_code_for_credentials(gmail_service: Any, code: str, state: str | None) -> Any:
    exchanger = getattr(gmail_service, "exchange_code_for_credentials", None)
    if exchanger is None:
        raise RuntimeError("Gmail service cannot exchange OAuth codes")
    try:
        return exchanger(code=code, state=state)
    except TypeError:
        return exchanger(code)


def _save_credentials(gmail_service: Any, credentials: Any, profile_id: str) -> None:
    saver = getattr(gmail_service, "save_credentials", None)
    if saver is None:
        raise RuntimeError("Gmail service cannot save credentials")
    saver(credentials=credentials, profile_id=profile_id)


def _connected_email(gmail_service: Any, profile_id: str) -> str | None:
    getter = getattr(gmail_service, "get_connected_email", None)
    if getter is None:
        return None
    return getter(profile_id)


@router.get("/callback")
async def gmail_oauth_callback(
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google's OAuth callback and persist credentials via gmail_service."""
    if error:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/dashboard?gmail=denied",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth code or state.",
        )

    profile_id = oauth_state_manager.consume_state(state)
    if profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        )

    await _require_profile(profile_id)
    gmail_service = _load_gmail_service()
    if gmail_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration service is not available.",
        )

    try:
        credentials = _exchange_code_for_credentials(gmail_service, code, state)
        _save_credentials(gmail_service, credentials, profile_id)
        email = _connected_email(gmail_service, profile_id)
        await upsert_gmail_connection(profile_id, email=email, connected=True)
    except Exception as exc:
        logger.warning("Gmail OAuth callback failed safely: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration service is not available.",
        ) from exc

    session_id = str(uuid.uuid4())
    background_tasks.add_task(run_guardian_scan_task, profile_id, session_id)
    return RedirectResponse(
        url=f"{FRONTEND_URL}/dashboard?gmail=connected&profile_id={profile_id}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
