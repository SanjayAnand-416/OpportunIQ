"""UTC reminder-time calculations and scheduler orchestration."""

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import APP_TIMEZONE


logger = logging.getLogger(__name__)

REMINDER_OFFSETS = {
    "7d": timedelta(days=7),
    "3d": timedelta(days=3),
    "1d": timedelta(days=1),
}
ALL_REMINDER_OFFSETS = (*REMINDER_OFFSETS, "0d")

scheduler = AsyncIOScheduler(timezone=timezone.utc)


def parse_deadline_datetime(value: Any) -> datetime | None:
    """Parse a deadline value and normalize it to aware UTC."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        clean_value = value.strip()
        if not clean_value:
            return None
        if clean_value.endswith("Z"):
            clean_value = f"{clean_value[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(clean_value)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def calculate_reminder_times(
    deadline_datetime: datetime | str,
    *,
    now: datetime | None = None,
    app_timezone: ZoneInfo | None = None,
) -> dict[str, datetime]:
    """Calculate future reminder fire times as timezone-aware UTC datetimes."""
    deadline = parse_deadline_datetime(deadline_datetime)
    if deadline is None:
        return {}
    comparison_now = parse_deadline_datetime(now) or datetime.now(timezone.utc)
    local_timezone = app_timezone or APP_TIMEZONE

    candidates = {
        offset: deadline - lead_time
        for offset, lead_time in REMINDER_OFFSETS.items()
    }
    local_deadline_date = deadline.astimezone(local_timezone).date()
    candidates["0d"] = datetime.combine(
        local_deadline_date,
        time(hour=9),
        tzinfo=local_timezone,
    ).astimezone(timezone.utc)
    return {
        offset: fire_time
        for offset, fire_time in candidates.items()
        if fire_time > comparison_now
    }


def build_job_id(deadline_id: str, offset: str) -> str:
    """Build the stable APScheduler identifier for one reminder offset."""
    return f"reminder:{deadline_id}:{offset}"


def scheduler_is_running() -> bool:
    """Return whether the process-local scheduler is running."""
    return bool(scheduler.running)


def start_scheduler() -> bool:
    """Start the process-local scheduler once."""
    if scheduler_is_running():
        return False
    scheduler.start()
    logger.info("Started APScheduler in UTC")
    return True


def shutdown_scheduler(wait: bool = False) -> bool:
    """Stop the scheduler safely and idempotently."""
    if not scheduler_is_running():
        return False
    try:
        scheduler.shutdown(wait=wait)
    except RuntimeError:
        logger.warning("APScheduler was already stopped")
        return False
    logger.info("Stopped APScheduler")
    return True


def list_scheduled_jobs() -> list[dict[str, str | None]]:
    """Return serializable scheduler job summaries."""
    return [
        {
            "id": job.id,
            "next_run_time": (
                job.next_run_time.astimezone(timezone.utc).isoformat()
                if job.next_run_time is not None
                else None
            ),
        }
        for job in scheduler.get_jobs()
    ]
