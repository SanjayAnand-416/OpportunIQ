"""Guardian Agent orchestration over Person C's Gmail and Groq services."""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app import config
from app.services import deadline_service, gmail_service, groq_service


logger = logging.getLogger(__name__)

REVIEW_CONFIDENCE_THRESHOLD = 0.6
MAX_CONCURRENT_EXTRACTIONS = 5

TIMEZONE_ALIASES = {
    "UTC": timezone.utc,
    "GMT": timezone.utc,
    "IST": ZoneInfo("Asia/Kolkata"),
    "PST": timezone(timedelta(hours=-8), "PST"),
    "PDT": timezone(timedelta(hours=-7), "PDT"),
    "EST": timezone(timedelta(hours=-5), "EST"),
    "EDT": timezone(timedelta(hours=-4), "EDT"),
    "CST": timezone(timedelta(hours=-6), "CST"),
    "CDT": timezone(timedelta(hours=-5), "CDT"),
    "CET": timezone(timedelta(hours=1), "CET"),
    "CEST": timezone(timedelta(hours=2), "CEST"),
}


async def run_guardian_agent(
    *,
    profile_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Fetch Gmail messages, extract deadlines, and persist through active services."""
    del session_id  # The active Gmail router owns public progress tracing.
    try:
        async with asyncio.timeout(config.AGENT_TIMEOUT_SECONDS):
            return await _run_guardian_pipeline(profile_id)
    except TimeoutError:
        logger.warning(
            "Guardian execution exceeded %.1f seconds for profile %s",
            config.AGENT_TIMEOUT_SECONDS,
            profile_id,
        )
        raise


async def _run_guardian_pipeline(profile_id: str) -> dict[str, Any]:
    """Execute the bounded concurrent adapter pipeline."""

    service = gmail_service.get_gmail_service(profile_id=profile_id)
    emails = await asyncio.to_thread(gmail_service.fetch_emails_3pass, service)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)

    async def process_email(email: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        message_id = str(email.get("id") or "").strip()
        email_text = str(email.get("body") or email.get("snippet") or "").strip()
        if not email_text:
            return None, None

        try:
            async with semaphore:
                extraction = await _extract_deadline(email_text)
            if not extraction.has_deadline:
                return None, None

            requires_review = (
                extraction.confidence < REVIEW_CONFIDENCE_THRESHOLD
                or extraction.deadline_date is None
            )
            organization = _optional_text(extraction, "organization")
            event_type = _event_type(extraction)
            action_required = _optional_text(extraction, "action_required")
            raw_deadline_text = _optional_text(extraction, "raw_deadline_text")
            result = await deadline_service.create_gmail_deadline(
                profile_id=profile_id,
                title=_deadline_title(
                    extraction,
                    organization=organization,
                    event_type=event_type,
                    action_required=action_required,
                ),
                deadline_datetime=_deadline_datetime(extraction),
                organization=organization,
                event_type=event_type,
                action_required=action_required or raw_deadline_text,
                notes=_deadline_notes(extraction),
                gmail_message_id=message_id or None,
                confidence=extraction.confidence,
                needs_review=requires_review,
            )
            return result["deadline"], None
        except Exception as exc:
            logger.warning("Guardian could not process Gmail message %s: %s", message_id, exc)
            return None, message_id or "unknown-message"

    processed = await asyncio.gather(*(process_email(email) for email in emails))
    deadlines = [deadline for deadline, _error in processed if deadline is not None]
    errors = [error for _deadline, error in processed if error is not None]
    needs_review = sum(bool(deadline.get("needs_review")) for deadline in deadlines)

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

    return datetime.combine(
        extraction.deadline_date,
        deadline_time,
        tzinfo=_extracted_timezone(_optional_text(extraction, "timezone")),
    )


def _extracted_timezone(value: str | None) -> tzinfo:
    """Resolve Person C's timezone while safely falling back to app configuration."""
    if value is None:
        return config.APP_TIMEZONE
    normalized = value.strip()
    alias = TIMEZONE_ALIASES.get(normalized.upper())
    if alias is not None:
        return alias
    offset_match = re.fullmatch(
        r"(?:UTC|GMT)?\s*([+-])(\d{1,2})(?::?(\d{2}))?",
        normalized,
        flags=re.IGNORECASE,
    )
    if offset_match:
        hours = int(offset_match.group(2))
        minutes = int(offset_match.group(3) or 0)
        if hours <= 14 and minutes < 60:
            offset = timedelta(hours=hours, minutes=minutes)
            if offset_match.group(1) == "-":
                offset = -offset
            return timezone(offset, normalized)
    try:
        return ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("Unknown extracted timezone %r; using APP_TIMEZONE", value)
        return config.APP_TIMEZONE


def _event_type(extraction: Any) -> str:
    """Map extracted event metadata onto the active deadline vocabulary."""
    value = (_optional_text(extraction, "event_type") or "other").lower()
    normalized = value.replace("-", "_").replace(" ", "_")
    aliases = {
        "test": "assessment",
        "online_test": "assessment",
        "oa": "assessment",
        "offer": "offer_acceptance",
    }
    normalized = aliases.get(normalized, normalized)
    allowed = {
        "interview",
        "submission",
        "offer_acceptance",
        "application",
        "assessment",
        "registration",
        "joining",
        "other",
    }
    return normalized if normalized in allowed else "other"


def _deadline_title(
    extraction: Any,
    *,
    organization: str | None,
    event_type: str,
    action_required: str | None,
) -> str:
    """Build a meaningful title from Person C output without new extraction."""
    explicit_title = _optional_text(extraction, "title", "deadline_title")
    if explicit_title:
        return explicit_title
    if action_required:
        return action_required
    event_label = (
        "Deadline" if event_type == "other" else event_type.replace("_", " ").title()
    )
    if organization:
        return f"{event_label} — {organization}"
    raw_deadline_text = _optional_text(extraction, "raw_deadline_text")
    return raw_deadline_text or f"{event_label} deadline"


def _deadline_notes(extraction: Any) -> str:
    """Retain source and timezone metadata supported by active persistence."""
    details = ["Extracted from Gmail."]
    timezone_name = _optional_text(extraction, "timezone")
    if timezone_name:
        details.append(f"Extracted timezone: {timezone_name}.")
    if bool(getattr(extraction, "is_relative", False)):
        details.append("Deadline was expressed as a relative date.")
    return " ".join(details)


def _optional_text(value: Any, *fields: str) -> str | None:
    """Read the first nonblank optional Person C field."""
    for field in fields:
        candidate = getattr(value, field, None)
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return None
