"""Deadline reminder scheduling and delivery, backed by APScheduler.

Orchestrates the reminder pipeline; it does not own persistence or the
websocket transport. Those live behind small ``Protocol`` interfaces
(``ProfileRepository``, ``OpportunityRepository``, ``NotificationRepository``,
``WebSocketPublisher``) injected via ``configure()``. This module ships an
in-memory default for each so it runs standalone, but a real app wires in
its actual database/websocket layer once those exist — see the docstring on
each Protocol.

Public API:
    schedule_reminders() - schedule one job per lead time before a deadline.
    cancel_reminders()   - remove every scheduled job for a student/opportunity.
    send_reminder()      - the job body: load -> generate -> save -> push -> email.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Protocol

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from pydantic import BaseModel, Field

from models import StudentProfile
from services.email_service import EmailSendResult, send_reminder_email
from services.groq_service import GroqServiceError, Opportunity, ReminderMessage, generate_reminder

logger = logging.getLogger(__name__)

# How long before the deadline to fire a reminder. Multiple lead times give
# a student an early heads-up plus a last-chance nudge.
DEFAULT_LEAD_TIMES: tuple[timedelta, ...] = (
    timedelta(days=7),
    timedelta(days=1),
    timedelta(hours=2),
)

# The hour (24h, local time) a reminder fires on days with no specific time.
DEFAULT_REMINDER_HOUR = 9

_JOB_ID_PREFIX = "reminder"


def _job_group(student_id: str, opportunity_id: str) -> str:
    """Shared prefix for every job scheduled for one student+opportunity pair."""
    return f"{_JOB_ID_PREFIX}:{student_id}:{opportunity_id}"


class ScheduleReminderResult(BaseModel):
    """One scheduled reminder job."""

    job_id: str = Field(description="APScheduler job id; pass to cancel a single reminder.")
    run_at: datetime = Field(description="When this reminder will fire.")


class SendReminderResult(BaseModel):
    """Outcome of running the ``send_reminder`` pipeline once."""

    success: bool = Field(description="True only if every step completed.")
    student_id: str
    opportunity_id: str
    notification_id: str | None = Field(default=None, description="Id from save_notification.")
    reminder: ReminderMessage | None = Field(default=None, description="The generated reminder.")
    email_result: EmailSendResult | None = Field(
        default=None, description="Email delivery outcome."
    )
    error: str | None = Field(default=None, description="Reason for failure, if any.")


# --------------------------------------------------------------------------
# Dependency interfaces. A real deployment implements these against its own
# database and websocket layer, then calls configure() with the instances.
# --------------------------------------------------------------------------


class ProfileRepository(Protocol):
    """Loads a student's profile by id."""

    async def get_profile(self, student_id: str) -> StudentProfile | None: ...


class OpportunityRepository(Protocol):
    """Loads an opportunity (including its deadline) by id."""

    async def get_opportunity(self, opportunity_id: str) -> Opportunity | None: ...


class NotificationRepository(Protocol):
    """Persists a generated reminder as a notification record."""

    async def save_notification(
        self, student_id: str, opportunity_id: str, reminder: ReminderMessage
    ) -> str:
        """Save the notification and return its generated id."""
        ...


class WebSocketPublisher(Protocol):
    """Pushes a real-time event to a student's connected clients."""

    async def push(self, student_id: str, payload: dict) -> None: ...


class InMemoryProfileRepository:
    """Dict-backed :class:`ProfileRepository` default; register profiles manually."""

    def __init__(self) -> None:
        self._profiles: dict[str, StudentProfile] = {}

    def register(self, student_id: str, profile: StudentProfile) -> None:
        """Add or replace the profile for ``student_id``."""
        self._profiles[student_id] = profile

    async def get_profile(self, student_id: str) -> StudentProfile | None:
        return self._profiles.get(student_id)


class InMemoryOpportunityRepository:
    """Dict-backed :class:`OpportunityRepository` default; register opportunities manually."""

    def __init__(self) -> None:
        self._opportunities: dict[str, Opportunity] = {}

    def register(self, opportunity_id: str, opportunity: Opportunity) -> None:
        """Add or replace the opportunity stored under ``opportunity_id``."""
        self._opportunities[opportunity_id] = opportunity

    async def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        return self._opportunities.get(opportunity_id)


class InMemoryNotificationRepository:
    """List-backed :class:`NotificationRepository` default."""

    def __init__(self) -> None:
        self.notifications: list[dict] = []

    async def save_notification(
        self, student_id: str, opportunity_id: str, reminder: ReminderMessage
    ) -> str:
        notification_id = str(uuid.uuid4())
        self.notifications.append(
            {
                "id": notification_id,
                "student_id": student_id,
                "opportunity_id": opportunity_id,
                "subject": reminder.subject,
                "body": reminder.body,
                "urgency": reminder.urgency.value,
                "created_at": datetime.now().isoformat(),
            }
        )
        return notification_id


class InMemoryWebSocketPublisher:
    """Process-local pub/sub default; a router registers callbacks per connection."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list] = {}

    def subscribe(self, student_id: str, callback) -> None:
        """Register a callback invoked with the payload dict on push()."""
        self._subscribers.setdefault(student_id, []).append(callback)

    def unsubscribe(self, student_id: str, callback) -> None:
        """Remove a previously registered callback."""
        subscribers = self._subscribers.get(student_id, [])
        if callback in subscribers:
            subscribers.remove(callback)

    async def push(self, student_id: str, payload: dict) -> None:
        for callback in list(self._subscribers.get(student_id, [])):
            try:
                await callback(payload)
            except Exception:
                logger.exception("Websocket subscriber callback failed for %s", student_id)


# Injected dependencies; swap via configure(). Defaults keep this module
# runnable in isolation (e.g. for tests) with no external services wired up.
_profile_repository: ProfileRepository = InMemoryProfileRepository()
_opportunity_repository: OpportunityRepository = InMemoryOpportunityRepository()
_notification_repository: NotificationRepository = InMemoryNotificationRepository()
_websocket_publisher: WebSocketPublisher = InMemoryWebSocketPublisher()

_scheduler: AsyncIOScheduler | None = None


def configure(
    *,
    profile_repository: ProfileRepository | None = None,
    opportunity_repository: OpportunityRepository | None = None,
    notification_repository: NotificationRepository | None = None,
    websocket_publisher: WebSocketPublisher | None = None,
) -> None:
    """Inject real implementations in place of the in-memory defaults.

    Call once at application startup, after the real database/websocket
    layers exist. Any argument left as ``None`` keeps its current binding.
    """
    global _profile_repository, _opportunity_repository
    global _notification_repository, _websocket_publisher

    if profile_repository is not None:
        _profile_repository = profile_repository
    if opportunity_repository is not None:
        _opportunity_repository = opportunity_repository
    if notification_repository is not None:
        _notification_repository = notification_repository
    if websocket_publisher is not None:
        _websocket_publisher = websocket_publisher


def get_scheduler() -> AsyncIOScheduler:
    """Return the lazily created, process-wide APScheduler instance.

    The scheduler is created but only ``start()``ed once (idempotent). The
    caller (typically the app's startup hook) owns calling ``shutdown()``.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
        logger.info("Started APScheduler")
    return _scheduler


def shutdown_scheduler(*, wait: bool = True) -> None:
    """Stop the scheduler, if running. Safe to call more than once."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=wait)
        logger.info("Stopped APScheduler")
        _scheduler = None


def schedule_reminders(
    student_id: str,
    opportunity_id: str,
    deadline: date | datetime,
    *,
    lead_times: tuple[timedelta, ...] = DEFAULT_LEAD_TIMES,
    now: datetime | None = None,
) -> list[ScheduleReminderResult]:
    """Schedule one reminder job per lead time before ``deadline``.

    Only future run times are scheduled; a lead time that has already
    passed relative to ``now`` (e.g. the "7 days before" slot when the
    deadline is tomorrow) is silently skipped. ``send_reminder`` is only
    ever called with ``student_id``/``opportunity_id`` — it re-loads the
    profile and opportunity fresh at run time, so edits made after
    scheduling are picked up automatically.

    Args:
        student_id: Id of the student to remind (resolved at run time via
            :class:`ProfileRepository`).
        opportunity_id: Id of the opportunity (resolved at run time via
            :class:`OpportunityRepository`).
        deadline: The application/submission deadline. A bare ``date`` is
            combined with :data:`DEFAULT_REMINDER_HOUR`.
        lead_times: How long before the deadline each reminder should fire.
        now: Current time, for testability; defaults to ``datetime.now()``.

    Returns:
        One :class:`ScheduleReminderResult` per job actually scheduled, in
        chronological order.
    """
    deadline_at = (
        datetime.combine(deadline, datetime.min.time().replace(hour=DEFAULT_REMINDER_HOUR))
        if isinstance(deadline, date) and not isinstance(deadline, datetime)
        else deadline
    )
    reference_time = now or datetime.now()
    scheduler = get_scheduler()
    group = _job_group(student_id, opportunity_id)

    scheduled: list[ScheduleReminderResult] = []
    for lead_time in lead_times:
        run_at = deadline_at - lead_time
        if run_at <= reference_time:
            logger.debug(
                "Skipping lead time %s for %s: run time %s already passed", lead_time, group, run_at
            )
            continue

        job_id = f"{group}:{lead_time.total_seconds():.0f}"
        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=run_at),
            id=job_id,
            args=[student_id, opportunity_id],
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduled.append(ScheduleReminderResult(job_id=job_id, run_at=run_at))
        logger.info("Scheduled reminder job %s to fire at %s", job_id, run_at)

    scheduled.sort(key=lambda r: r.run_at)
    return scheduled


def cancel_reminders(student_id: str, opportunity_id: str) -> int:
    """Cancel every scheduled reminder job for one student+opportunity pair.

    Safe to call when nothing is scheduled (returns ``0``).

    Args:
        student_id: The student whose reminders should be cancelled.
        opportunity_id: The opportunity whose reminders should be cancelled.

    Returns:
        The number of jobs removed.
    """
    scheduler = get_scheduler()
    group = _job_group(student_id, opportunity_id)

    removed = 0
    for job in scheduler.get_jobs():
        if job.id == group or job.id.startswith(f"{group}:"):
            try:
                scheduler.remove_job(job.id)
                removed += 1
            except JobLookupError:
                # Job fired and self-removed between get_jobs() and here.
                pass

    logger.info("Cancelled %d reminder job(s) for %s", removed, group)
    return removed


async def send_reminder(student_id: str, opportunity_id: str) -> SendReminderResult:
    """Run one reminder end-to-end: load, generate, save, push, email.

    This is the APScheduler job body — it never raises. Every step is
    guarded so a failure (missing profile, Groq outage, SMTP error) is
    logged and reflected in the returned result instead of crashing the
    scheduler thread.

    Steps:
        1. Load the student profile.
        2. Load the opportunity (and its deadline).
        3. Generate the reminder text via Groq.
        4. Save it as a notification record.
        5. Push it to the student over the websocket channel.
        6. Email it to the student.

    Args:
        student_id: Id passed to :class:`ProfileRepository`.
        opportunity_id: Id passed to :class:`OpportunityRepository`.

    Returns:
        A :class:`SendReminderResult` describing how far the pipeline got.
    """
    try:
        # 1. Load profile.
        profile = await _profile_repository.get_profile(student_id)
        if profile is None:
            logger.warning("send_reminder: no profile found for student_id=%s", student_id)
            return SendReminderResult(
                success=False,
                student_id=student_id,
                opportunity_id=opportunity_id,
                error="Student profile not found.",
            )

        # 2. Load deadline (via the opportunity it belongs to).
        opportunity = await _opportunity_repository.get_opportunity(opportunity_id)
        if opportunity is None:
            logger.warning("send_reminder: no opportunity found for id=%s", opportunity_id)
            return SendReminderResult(
                success=False,
                student_id=student_id,
                opportunity_id=opportunity_id,
                error="Opportunity not found.",
            )

        days_remaining = (
            (opportunity.deadline - date.today()).days if opportunity.deadline else None
        )

        # 3. Generate reminder using Groq.
        try:
            reminder = await generate_reminder(
                opportunity, days_remaining=days_remaining, student_name=profile.full_name
            )
        except GroqServiceError as exc:
            logger.error("send_reminder: Groq generation failed for %s: %s", student_id, exc)
            return SendReminderResult(
                success=False,
                student_id=student_id,
                opportunity_id=opportunity_id,
                error=f"Reminder generation failed: {exc}",
            )

        # 4. Save notification.
        notification_id = await _notification_repository.save_notification(
            student_id, opportunity_id, reminder
        )

        # 5. Push over websocket (best-effort: a disconnected client shouldn't
        #    block the email step below).
        try:
            await _websocket_publisher.push(
                student_id,
                {
                    "type": "reminder",
                    "notification_id": notification_id,
                    "opportunity_id": opportunity_id,
                    "subject": reminder.subject,
                    "body": reminder.body,
                    "urgency": reminder.urgency.value,
                },
            )
        except Exception:
            logger.exception("send_reminder: websocket push failed for %s", student_id)

        # 6. Send email.
        email_result: EmailSendResult | None = None
        if profile.email:
            try:
                email_result = await send_reminder_email(
                    profile.email, reminder.subject, reminder.body
                )
            except Exception as exc:
                logger.exception("send_reminder: email send raised for %s", student_id)
                email_result = EmailSendResult(success=False, attempts=0, error=str(exc))
        else:
            logger.warning("send_reminder: student %s has no email on file", student_id)

        success = email_result is None or email_result.success
        return SendReminderResult(
            success=success,
            student_id=student_id,
            opportunity_id=opportunity_id,
            notification_id=notification_id,
            reminder=reminder,
            email_result=email_result,
            error=None if success else (email_result.error if email_result else None),
        )

    except Exception as exc:  # last-resort guard: a job body must never raise
        logger.exception("send_reminder: unexpected failure for student_id=%s", student_id)
        return SendReminderResult(
            success=False,
            student_id=student_id,
            opportunity_id=opportunity_id,
            error=f"Unexpected failure: {exc}",
        )
