"""Tests for the active-package reminder scheduler lifecycle."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app import database
from app.models import StudentProfile
from app.repositories import deadline_repository, notification_repository, profile_repository
from app.services import scheduler_service


@pytest.fixture()
def scheduler_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "scheduler.sqlite"))
    for repository in (deadline_repository, notification_repository, profile_repository):
        monkeypatch.setattr(repository, "get_db", database.get_db)
    monkeypatch.setattr(scheduler_service, "_optional_function", lambda *args: None)
    asyncio.run(database.init_db())
    yield
    if scheduler_service.scheduler.running:
        scheduler_service.scheduler.remove_all_jobs()
        scheduler_service.shutdown_scheduler(wait=False)


async def _create_records(*, completed=False, cancelled=False):
    profile = StudentProfile(name="Ada", email=None, skills=["Python"])
    created_profile = await profile_repository.create_profile(profile)
    deadline = await deadline_repository.create_deadline(
        profile_id=created_profile["profile_id"],
        title="Final Submission",
        organization="NIT",
        deadline_datetime=datetime.now(timezone.utc) + timedelta(days=10),
        action_required="Upload the solution",
        is_completed=completed,
        is_cancelled=cancelled,
    )
    return created_profile, deadline


def test_scheduler_lifecycle_is_idempotent():
    async def scenario():
        assert scheduler_service.start_scheduler() is True
        assert scheduler_service.start_scheduler() is False
        assert scheduler_service.scheduler_is_running() is True
        assert scheduler_service.shutdown_scheduler() is True
        assert scheduler_service.shutdown_scheduler() is False

    asyncio.run(scenario())


def test_scheduler_can_be_disabled(monkeypatch):
    monkeypatch.setattr(scheduler_service.config, "ENABLE_SCHEDULER", False)

    assert scheduler_service.start_scheduler() is False
    assert scheduler_service.scheduler_is_running() is False
    result = scheduler_service.schedule_reminders(
        "d1", datetime.now(timezone.utc) + timedelta(days=10), "p1"
    )
    assert result["scheduler_disabled"] is True
    assert result["scheduled_jobs"] == []
    assert asyncio.run(scheduler_service.restore_scheduled_reminders()) == {
        "deadlines_processed": 0,
        "jobs_scheduled": 0,
        "errors": 0,
    }


def test_schedule_cancel_reschedule_and_inspect(scheduler_db):
    async def scenario():
        deadline = datetime.now(timezone.utc) + timedelta(days=10)
        first = scheduler_service.schedule_reminders("d1", deadline, "p1")
        assert len(first["scheduled_jobs"]) == 4
        assert len(scheduler_service.get_deadline_jobs("d1")) == 4
        assert len(scheduler_service.reschedule_reminders("d1", deadline, "p1")["scheduled_jobs"]) == 4
        assert len(scheduler_service.get_deadline_jobs("d1")) == 4
        assert len(scheduler_service.cancel_reminders("d1")) == 4

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("completed", "cancelled", "reason"),
    [(True, False, "deadline_completed"), (False, True, "deadline_cancelled")],
)
def test_execution_skips_inactive_deadlines(scheduler_db, completed, cancelled, reason):
    async def scenario():
        profile, deadline = await _create_records(completed=completed, cancelled=cancelled)
        result = await scheduler_service.execute_reminder(
            deadline["deadline_id"], profile["profile_id"], "7d"
        )
        assert result["skipped"] is True
        assert result["reason"] == reason

    asyncio.run(scenario())


def test_missing_records_are_skipped(scheduler_db):
    result = asyncio.run(scheduler_service.execute_reminder("missing", "profile", "1d"))
    assert result["reason"] == "deadline_not_found"


def test_fallback_persists_dashboard_and_is_idempotent(scheduler_db, monkeypatch):
    async def failing_emit(*args, **kwargs):
        raise RuntimeError("socket closed")

    async def failing_generate_reminder(**kwargs):
        raise RuntimeError("Groq unavailable during fallback test")

    monkeypatch.setattr(scheduler_service, "emit_trace", failing_emit)
    monkeypatch.setattr(
        scheduler_service,
        "generate_reminder",
        failing_generate_reminder,
    )

    async def scenario():
        profile, deadline = await _create_records()
        first = await scheduler_service.execute_reminder(
            deadline["deadline_id"], profile["profile_id"], "7d"
        )
        duplicate = await scheduler_service.execute_reminder(
            deadline["deadline_id"], profile["profile_id"], "7d"
        )
        assert first["success"] is True
        assert first["subject"] == "Deadline reminder: Final Submission"
        assert first["email_sent"] is False
        assert duplicate["reason"] == "notification_exists"
        stored = await notification_repository.get_notification_by_id(
            first["notification_id"]
        )
        assert stored["channel"] == "dashboard"

    asyncio.run(scenario())


def test_force_reminder_can_execute_twice(scheduler_db):
    async def scenario():
        profile, deadline = await _create_records(completed=True)
        first = await scheduler_service.execute_reminder(
            deadline["deadline_id"], profile["profile_id"], "test", force=True
        )
        second = await scheduler_service.execute_reminder(
            deadline["deadline_id"], profile["profile_id"], "test", force=True
        )
        assert first["success"] and second["success"]
        assert first["notification_id"] != second["notification_id"]

    asyncio.run(scenario())


def test_restore_continues_after_bad_record(scheduler_db, monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()

    async def fake_list():
        return [
            {"deadline_id": "bad", "profile_id": "p", "deadline_datetime": object()},
            {"deadline_id": "good", "profile_id": "p", "deadline_datetime": future},
        ]

    monkeypatch.setattr(deadline_repository, "list_schedulable_deadlines", fake_list)

    async def scenario():
        scheduler_service.start_scheduler()
        summary = await scheduler_service.restore_scheduled_reminders()
        assert summary == {"deadlines_processed": 2, "jobs_scheduled": 4, "errors": 1}
        assert len(scheduler_service.get_deadline_jobs("good")) == 4

    asyncio.run(scenario())
