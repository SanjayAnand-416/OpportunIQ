"""Guardian Agent orchestration over Person C's Gmail and Groq services."""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, time
from typing import Any

from app.config import APP_TIMEZONE
from app.services import deadline_service, gmail_service, groq_service


logger = logging.getLogger(__name__)

REVIEW_CONFIDENCE_THRESHOLD = 0.6


async def run_guardian_agent(
    *,
    profile_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Fetch Gmail messages, extract deadlines, and persist through active services."""
    del session_id  # The active Gmail router owns public progress tracing.

    service = gmail_service.get_gmail_service(profile_id=profile_id)
    emails = await asyncio.to_thread(gmail_service.fetch_emails_3pass, service)

    deadlines: list[dict[str, Any]] = []
    needs_review = 0
    errors: list[str] = []

    for email in emails:
        message_id = str(email.get("id") or "").strip()
        email_text = str(email.get("body") or email.get("snippet") or "").strip()
        if not email_text:
            continue

        try:
            extraction = await _extract_deadline(email_text)
            if not extraction.has_deadline:
                continue

            requires_review = (
                extraction.confidence < REVIEW_CONFIDENCE_THRESHOLD
                or extraction.deadline_date is None
            )
            result = await deadline_service.create_gmail_deadline(
                profile_id=profile_id,
                title=extraction.raw_deadline_text or "Gmail deadline",
                deadline_datetime=_deadline_datetime(extraction),
                event_type="other",
                action_required=extraction.raw_deadline_text,
                notes="Extracted from Gmail.",
                gmail_message_id=message_id or None,
                confidence=extraction.confidence,
                needs_review=requires_review,
            )
            deadline = result["deadline"]
            deadlines.append(deadline)
            if requires_review:
                needs_review += 1
        except Exception as exc:
            logger.warning("Guardian could not process Gmail message %s: %s", message_id, exc)
            errors.append(message_id or "unknown-message")

    return {
        "emails_scanned": len(emails),
        "deadlines_found": len(deadlines),
        "needs_review": needs_review,
        "errors": errors,
        "deadlines": deadlines,
    }


async def _extract_deadline(email_text: str) -> Any:
    """Invoke Person C's extractor without changing its sync/async behavior."""
    extracted = groq_service.extract_deadline(email_text)
    if inspect.isawaitable(extracted):
        return await extracted
    return extracted


def _deadline_datetime(extraction: Any) -> datetime | None:
    """Adapt the extracted date/time fields to the active persistence contract."""
    if extraction.deadline_date is None:
        return None

    deadline_time = time(23, 59)
    if extraction.deadline_time:
        try:
            deadline_time = time.fromisoformat(extraction.deadline_time)
        except ValueError:
            logger.warning("Invalid extracted Gmail deadline time; using end of day")

    return datetime.combine(extraction.deadline_date, deadline_time, tzinfo=APP_TIMEZONE)
