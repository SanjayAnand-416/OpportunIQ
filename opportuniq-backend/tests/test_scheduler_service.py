"""Tests for services/scheduler_service.py (root package)."""

import asyncio
from datetime import date, datetime, timedelta

import pytest

import services.scheduler_service as scheduler_service
from models import StudentProfile
from services.email_service import EmailSendResult
from services.groq_service import (
    GroqServiceError,
    Opportunity,
    OpportunityType,
    ReminderMessage,
    Urgency,
)


@pytest.fixture(autouse=True)
def _isolated_scheduler_state():
    """Give every test a clean scheduler + fresh in-memory repos, and tear down after."""
    scheduler_service._profile_repository = scheduler_service.InMemoryProfileRepository()
    scheduler_service._opportunity_repository = scheduler_service.InMemoryOpportunityRepository()
    scheduler_service._notification_repository = scheduler_service.InMemoryNotificationRepository()
    scheduler_service._websocket_publisher = scheduler_service.InMemoryWebSocketPublisher()
    scheduler_service._scheduler = None
    yield
    # AsyncIOScheduler binds to the loop that started it; asyncio.run() (used
    # by run_in_loop) closes that loop as soon as the test body returns, so
    # shutdown() here would hit a closed loop. AsyncIOScheduler runs no
    # background thread, so just dropping the reference is enough in tests.
    scheduler_service._scheduler = None


def run_in_loop(fn, *args, **kwargs):
    """Run a sync callable inside a live asyncio loop.

    ``AsyncIOScheduler`` (used by schedule_reminders/cancel_reminders) needs
    ``asyncio.get_running_loop()`` to succeed, which plain sync pytest
    functions don't provide on their own.
    """

    async def _call():
        return fn(*args, **kwargs)

    return asyncio.run(_call())


def make_opportunity(**overrides) -> Opportunity:
    defaults = dict(
        title="SDE Intern",
        organization="Acme",
        opportunity_type=OpportunityType.INTERNSHIP,
        deadline=date.today() + timedelta(days=3),
    )
    defaults.update(overrides)
    return Opportunity(**defaults)


# ---------------------------------------------------------------------------
# schedule_reminders / cancel_reminders
# ---------------------------------------------------------------------------


def test_schedule_reminders_skips_lead_times_already_passed():
    now = datetime(2026, 8, 1, 9, 0)
    deadline = date(2026, 8, 5)  # combined with DEFAULT_REMINDER_HOUR -> 08-05 09:00

    results = run_in_loop(scheduler_service.schedule_reminders, "stu-1", "opp-1", deadline, now=now)

    # 7d lead (07-29) is already past; 1d (08-04 09:00) and 2h (08-05 07:00) remain.
    assert [r.run_at for r in results] == [
        datetime(2026, 8, 4, 9, 0),
        datetime(2026, 8, 5, 7, 0),
    ]
    assert len(scheduler_service.get_scheduler().get_jobs()) == 2


def test_schedule_reminders_accepts_bare_datetime_deadline():
    now = datetime(2026, 8, 1, 9, 0)
    deadline = datetime(2026, 8, 5, 18, 30)

    results = run_in_loop(scheduler_service.schedule_reminders, "stu-1", "opp-1", deadline, now=now)

    assert results[-1].run_at == deadline - timedelta(hours=2)


def test_schedule_reminders_is_replace_existing_not_additive():
    now = datetime(2026, 8, 1, 9, 0)
    deadline = date(2026, 8, 5)

    def _schedule_twice():
        scheduler_service.schedule_reminders("stu-1", "opp-1", deadline, now=now)
        scheduler_service.schedule_reminders("stu-1", "opp-1", deadline, now=now)

    run_in_loop(_schedule_twice)

    assert len(scheduler_service.get_scheduler().get_jobs()) == 2


def test_cancel_reminders_removes_only_matching_jobs():
    now = datetime(2026, 8, 1, 9, 0)

    def _schedule_both():
        scheduler_service.schedule_reminders("stu-1", "opp-1", date(2026, 8, 5), now=now)
        scheduler_service.schedule_reminders("stu-2", "opp-2", date(2026, 8, 5), now=now)

    run_in_loop(_schedule_both)

    removed = scheduler_service.cancel_reminders("stu-1", "opp-1")

    assert removed == 2
    remaining_ids = [job.id for job in scheduler_service.get_scheduler().get_jobs()]
    assert all("stu-1:opp-1" not in job_id for job_id in remaining_ids)
    assert any("stu-2:opp-2" in job_id for job_id in remaining_ids)


def test_cancel_reminders_is_safe_when_nothing_scheduled():
    assert run_in_loop(scheduler_service.cancel_reminders, "nobody", "nothing") == 0


# ---------------------------------------------------------------------------
# send_reminder
# ---------------------------------------------------------------------------


def test_send_reminder_full_happy_path(monkeypatch):
    profile = StudentProfile(full_name="Asha", email="asha@example.com", skills=["Python"])
    opportunity = make_opportunity()
    scheduler_service._profile_repository.register("stu-1", profile)
    scheduler_service._opportunity_repository.register("opp-1", opportunity)

    reminder = ReminderMessage(
        subject="Apply soon",
        body="Deadline in 3 days.",
        call_to_action="Apply",
        urgency=Urgency.HIGH,
    )

    async def fake_generate_reminder(*args, **kwargs):
        fake_generate_reminder.kwargs = kwargs
        return reminder

    async def fake_send_email(to_email, subject, body, **kwargs):
        fake_send_email.args = (to_email, subject, body)
        return EmailSendResult(success=True, attempts=1, message_id="<x@y>")

    pushed = []

    async def ws_callback(payload):
        pushed.append(payload)

    scheduler_service._websocket_publisher.subscribe("stu-1", ws_callback)
    monkeypatch.setattr(scheduler_service, "generate_reminder", fake_generate_reminder)
    monkeypatch.setattr(scheduler_service, "send_reminder_email", fake_send_email)

    result = asyncio.run(scheduler_service.send_reminder("stu-1", "opp-1"))

    assert result.success is True
    assert result.notification_id
    assert any(
        n["id"] == result.notification_id
        for n in scheduler_service._notification_repository.notifications
    )
    assert pushed and pushed[0]["subject"] == "Apply soon"
    assert fake_send_email.args[0] == "asha@example.com"
    assert fake_generate_reminder.kwargs["days_remaining"] == 3


def test_send_reminder_missing_profile_fails_cleanly():
    scheduler_service._opportunity_repository.register("opp-1", make_opportunity())

    result = asyncio.run(scheduler_service.send_reminder("ghost-student", "opp-1"))

    assert result.success is False
    assert "profile" in result.error.lower()


def test_send_reminder_missing_opportunity_fails_cleanly():
    scheduler_service._profile_repository.register("stu-1", StudentProfile(email="a@b.com"))

    result = asyncio.run(scheduler_service.send_reminder("stu-1", "ghost-opp"))

    assert result.success is False
    assert "opportunity" in result.error.lower()


def test_send_reminder_groq_failure_is_caught(monkeypatch):
    scheduler_service._profile_repository.register("stu-1", StudentProfile(email="a@b.com"))
    scheduler_service._opportunity_repository.register("opp-1", make_opportunity())

    async def failing_generate(*args, **kwargs):
        raise GroqServiceError("groq is down")

    monkeypatch.setattr(scheduler_service, "generate_reminder", failing_generate)

    result = asyncio.run(scheduler_service.send_reminder("stu-1", "opp-1"))

    assert result.success is False
    assert "generation failed" in result.error.lower()


def test_send_reminder_email_failure_still_saves_notification(monkeypatch):
    scheduler_service._profile_repository.register("stu-1", StudentProfile(email="a@b.com"))
    scheduler_service._opportunity_repository.register("opp-1", make_opportunity())

    reminder = ReminderMessage(subject="s", body="b", call_to_action="Apply", urgency=Urgency.LOW)

    async def fake_generate_reminder(*args, **kwargs):
        return reminder

    async def failing_email(*args, **kwargs):
        return EmailSendResult(success=False, attempts=3, error="smtp down")

    monkeypatch.setattr(scheduler_service, "generate_reminder", fake_generate_reminder)
    monkeypatch.setattr(scheduler_service, "send_reminder_email", failing_email)

    result = asyncio.run(scheduler_service.send_reminder("stu-1", "opp-1"))

    assert result.success is False
    assert result.error == "smtp down"
    assert result.notification_id is not None


def test_send_reminder_skips_email_when_student_has_no_address(monkeypatch):
    scheduler_service._profile_repository.register("stu-1", StudentProfile(full_name="No Email"))
    scheduler_service._opportunity_repository.register("opp-1", make_opportunity())

    reminder = ReminderMessage(subject="s", body="b", call_to_action="Apply", urgency=Urgency.LOW)

    async def fake_generate_reminder(*args, **kwargs):
        return reminder

    async def unexpected_email_call(*args, **kwargs):
        raise AssertionError("send_reminder_email should not be called without an email")

    monkeypatch.setattr(scheduler_service, "generate_reminder", fake_generate_reminder)
    monkeypatch.setattr(scheduler_service, "send_reminder_email", unexpected_email_call)

    result = asyncio.run(scheduler_service.send_reminder("stu-1", "opp-1"))

    assert result.success is True
    assert result.email_result is None


def test_send_reminder_websocket_failure_does_not_block_email(monkeypatch):
    scheduler_service._profile_repository.register("stu-1", StudentProfile(email="a@b.com"))
    scheduler_service._opportunity_repository.register("opp-1", make_opportunity())

    reminder = ReminderMessage(subject="s", body="b", call_to_action="Apply", urgency=Urgency.LOW)

    async def fake_generate_reminder(*args, **kwargs):
        return reminder

    async def fake_send_email(*args, **kwargs):
        return EmailSendResult(success=True, attempts=1, message_id="<x@y>")

    async def bad_callback(payload):
        raise RuntimeError("socket closed")

    scheduler_service._websocket_publisher.subscribe("stu-1", bad_callback)
    monkeypatch.setattr(scheduler_service, "generate_reminder", fake_generate_reminder)
    monkeypatch.setattr(scheduler_service, "send_reminder_email", fake_send_email)

    result = asyncio.run(scheduler_service.send_reminder("stu-1", "opp-1"))

    assert result.success is True
