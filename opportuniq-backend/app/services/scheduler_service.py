"""UTC reminder-time calculations and scheduler orchestration."""

import asyncio
import importlib
import inspect
import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.date import DateTrigger

from app.config import APP_TIMEZONE
from app.models import ReminderExecutionResult
from app.repositories import (
    deadline_repository,
    notification_repository,
    profile_repository,
)
from app.websocket_manager import emit_trace


logger = logging.getLogger(__name__)

REMINDER_OFFSETS = {
    "7d": timedelta(days=7),
    "3d": timedelta(days=3),
    "1d": timedelta(days=1),
}
ALL_REMINDER_OFFSETS = (*REMINDER_OFFSETS, "0d")

def _new_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone=timezone.utc)


scheduler = _new_scheduler()


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
    global scheduler
    if not scheduler_is_running():
        return False
    active_scheduler = scheduler
    scheduler = _new_scheduler()
    try:
        active_scheduler.shutdown(wait=wait)
    except RuntimeError:
        logger.warning("APScheduler event loop was already closed")
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


async def _invoke_optional(function: Any, **kwargs: Any) -> Any:
    """Invoke a sync or async optional integration with a bounded timeout."""
    if inspect.iscoroutinefunction(function):
        return await asyncio.wait_for(function(**kwargs), timeout=10)
    result = await asyncio.wait_for(
        asyncio.to_thread(function, **kwargs),
        timeout=10,
    )
    if inspect.isawaitable(result):
        return await asyncio.wait_for(result, timeout=10)
    return result


def _optional_function(module_names: tuple[str, ...], function_name: str) -> Any | None:
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
        except (ImportError, ModuleNotFoundError):
            continue
        function = getattr(module, function_name, None)
        if callable(function):
            return function
    return None


def _fallback_reminder_content(
    deadline: dict[str, Any], days_remaining: int | None
) -> tuple[str, str]:
    title = str(deadline.get("title") or "Upcoming deadline")
    organization = str(deadline.get("organization") or "the organization")
    if days_remaining is None:
        due_text = "soon"
    elif days_remaining < 0:
        due_text = "overdue"
    elif days_remaining == 0:
        due_text = "today"
    elif days_remaining == 1:
        due_text = "in 1 day"
    else:
        due_text = f"in {days_remaining} days"
    body = f"{title} for {organization} is due {due_text}."
    action_required = str(deadline.get("action_required") or "Review and complete it.")
    body += f" Required action: {action_required}"
    return f"Deadline reminder: {title}", body


async def _generate_reminder_content(
    profile: dict[str, Any],
    deadline: dict[str, Any],
    days_remaining: int | None,
) -> tuple[str, str]:
    """Generate reminder content through a compatible adapter or local fallback."""
    function = _optional_function(
        ("app.services.groq_service", "services.groq_service"),
        "generate_reminder",
    )
    if function is not None:
        expected = {
            "profile_name",
            "skills",
            "deadline_title",
            "deadline_dt",
            "days_left",
        }
        if expected.issubset(inspect.signature(function).parameters):
            try:
                result = await _invoke_optional(
                    function,
                    profile_name=str(profile.get("name") or "Student"),
                    skills=list(profile.get("skills") or []),
                    deadline_title=str(deadline.get("title") or "Deadline"),
                    deadline_dt=str(deadline.get("deadline_datetime") or ""),
                    days_left=days_remaining or 0,
                )
                if hasattr(result, "model_dump"):
                    result = result.model_dump()
                if isinstance(result, dict):
                    subject = result.get("subject")
                    body = result.get("body") or result.get("message")
                    if subject and body:
                        return str(subject), str(body)
            except Exception as exc:
                logger.warning("Groq reminder generation failed: %s", exc)
    return _fallback_reminder_content(deadline, days_remaining)


async def _send_email_if_available(
    *, profile: dict[str, Any], subject: str, body: str
) -> bool:
    email = str(profile.get("email") or "").strip()
    if not email:
        return False
    function = _optional_function(
        ("app.services.email_service", "services.email_service"),
        "send_reminder_email",
    )
    if function is None:
        return False
    try:
        result = await _invoke_optional(
            function,
            to_email=email,
            subject=subject,
            body=body,
        )
        if hasattr(result, "success"):
            return bool(result.success)
        if isinstance(result, dict):
            return bool(result.get("success"))
        return bool(result)
    except Exception as exc:
        logger.warning("Reminder email delivery skipped or failed: %s", exc)
        return False


async def execute_reminder(
    deadline_id: str,
    profile_id: str,
    reminder_offset: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Execute one reminder without allowing integration failures to escape."""
    result_base = {
        "deadline_id": deadline_id,
        "profile_id": profile_id,
        "reminder_offset": reminder_offset,
    }
    try:
        if reminder_offset not in ALL_REMINDER_OFFSETS and not reminder_offset.startswith("test"):
            return ReminderExecutionResult(
                success=False, skipped=True, reason="invalid_offset", **result_base
            ).model_dump()
        deadline = await deadline_repository.get_deadline_by_id(deadline_id)
        if deadline is None:
            return ReminderExecutionResult(
                success=False, skipped=True, reason="deadline_not_found", **result_base
            ).model_dump()
        profile = await profile_repository.get_profile_by_id(profile_id)
        if profile is None:
            return ReminderExecutionResult(
                success=False, skipped=True, reason="profile_not_found", **result_base
            ).model_dump()
        if not force:
            reason = None
            if deadline.get("is_completed"):
                reason = "deadline_completed"
            elif deadline.get("is_cancelled"):
                reason = "deadline_cancelled"
            elif not deadline.get("deadline_datetime"):
                reason = "deadline_datetime_missing"
            elif await notification_repository.notification_exists(
                deadline_id=deadline_id,
                reminder_offset=reminder_offset,
                channel="dashboard",
            ):
                reason = "notification_exists"
            if reason:
                return ReminderExecutionResult(
                    success=True, skipped=True, reason=reason, **result_base
                ).model_dump()

        days_remaining = deadline_repository.calculate_days_remaining(
            deadline.get("deadline_datetime")
        )
        subject, body = await _generate_reminder_content(
            profile, deadline, days_remaining
        )
        stored_offset = (
            f"test:{uuid.uuid4()}" if force and reminder_offset == "test" else reminder_offset
        )
        notification = await notification_repository.create_notification(
            profile_id=profile_id,
            deadline_id=deadline_id,
            subject=subject,
            message=body,
            channel="dashboard",
            reminder_offset=stored_offset,
            delivery_status="created",
        )
        try:
            await emit_trace(
                session_id=profile_id,
                agent="notifier",
                status="notification",
                message=body,
                metadata={
                    "notification_id": notification["id"],
                    "deadline_id": deadline_id,
                    "subject": subject,
                    "reminder_offset": stored_offset,
                },
            )
        except Exception as exc:
            logger.warning("Reminder WebSocket push failed: %s", exc)

        email_sent = await _send_email_if_available(
            profile=profile, subject=subject, body=body
        )
        if email_sent:
            await notification_repository.create_notification(
                profile_id=profile_id,
                deadline_id=deadline_id,
                subject=subject,
                message=body,
                channel="email",
                reminder_offset=stored_offset,
                delivery_status="sent",
            )
        return ReminderExecutionResult(
            success=True,
            notification_id=notification["id"],
            subject=subject,
            message=body,
            email_sent=email_sent,
            **result_base,
        ).model_dump()
    except Exception as exc:
        logger.exception("Reminder execution failed for deadline %s", deadline_id)
        return ReminderExecutionResult(
            success=False,
            skipped=True,
            reason=type(exc).__name__,
            **result_base,
        ).model_dump()


def schedule_reminders(
    deadline_id: str,
    deadline_datetime: datetime | str,
    profile_id: str,
) -> dict[str, Any]:
    """Schedule every future reminder offset for one active deadline."""
    if not scheduler_is_running():
        start_scheduler()
    fire_times = calculate_reminder_times(deadline_datetime)
    scheduled_jobs: list[str] = []
    for offset, fire_time in fire_times.items():
        job_id = build_job_id(deadline_id, offset)
        scheduler.add_job(
            execute_reminder,
            trigger=DateTrigger(run_date=fire_time, timezone=timezone.utc),
            args=[deadline_id, profile_id, offset],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
        )
        scheduled_jobs.append(job_id)
    return {
        "deadline_id": deadline_id,
        "scheduled_jobs": scheduled_jobs,
        "skipped_offsets": [
            offset for offset in ALL_REMINDER_OFFSETS if offset not in fire_times
        ],
    }


def cancel_reminders(deadline_id: str) -> list[str]:
    """Remove all known reminder jobs for one deadline."""
    removed: list[str] = []
    for offset in ALL_REMINDER_OFFSETS:
        job_id = build_job_id(deadline_id, offset)
        try:
            scheduler.remove_job(job_id)
            removed.append(job_id)
        except JobLookupError:
            continue
    return removed


def reschedule_reminders(
    deadline_id: str,
    deadline_datetime: datetime | str,
    profile_id: str,
) -> dict[str, Any]:
    """Replace all reminder jobs for an updated deadline."""
    cancel_reminders(deadline_id)
    return schedule_reminders(deadline_id, deadline_datetime, profile_id)


def get_deadline_jobs(deadline_id: str) -> list[dict[str, str | None]]:
    """Return serializable jobs belonging to one deadline."""
    prefix = f"reminder:{deadline_id}:"
    return [job for job in list_scheduled_jobs() if job["id"].startswith(prefix)]


async def restore_scheduled_reminders() -> dict[str, int]:
    """Recreate future in-memory jobs from the durable deadline registry."""
    deadlines = await deadline_repository.list_schedulable_deadlines()
    summary = {
        "deadlines_processed": 0,
        "jobs_scheduled": 0,
        "errors": 0,
    }
    for deadline in deadlines:
        summary["deadlines_processed"] += 1
        try:
            if parse_deadline_datetime(deadline.get("deadline_datetime")) is None:
                raise ValueError("Malformed deadline datetime")
            result = schedule_reminders(
                deadline["deadline_id"],
                deadline["deadline_datetime"],
                deadline["profile_id"],
            )
            summary["jobs_scheduled"] += len(result["scheduled_jobs"])
        except Exception as exc:
            summary["errors"] += 1
            logger.warning(
                "Could not restore reminders for deadline %s: %s",
                deadline.get("deadline_id"),
                exc,
            )
    logger.info("Reminder restoration summary: %s", summary)
    return summary
