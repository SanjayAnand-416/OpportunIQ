"""Tests for the SQLite notification repository (database.py, root package)."""

import asyncio

import pytest

from database import SQLiteNotificationRepository
from services.groq_service import ReminderMessage, Urgency


@pytest.fixture()
def repo(tmp_path) -> SQLiteNotificationRepository:
    return SQLiteNotificationRepository(database_path=str(tmp_path / "notifications.sqlite"))


def test_create_returns_populated_record(repo):
    record = asyncio.run(
        repo.create(student_id="stu-1", subject="s", body="b", opportunity_id="opp-1")
    )
    assert record.id
    assert record.student_id == "stu-1"
    assert record.is_read is False
    assert record.read_at is None
    assert record.urgency == Urgency.MEDIUM


def test_save_notification_matches_scheduler_protocol(repo):
    reminder = ReminderMessage(
        subject="Apply soon", body="Deadline in 3 days.", call_to_action="Apply", urgency=Urgency.HIGH
    )
    notification_id = asyncio.run(repo.save_notification("stu-1", "opp-1", reminder))
    record = asyncio.run(repo.get(notification_id))
    assert record is not None
    assert record.subject == "Apply soon" and record.urgency == Urgency.HIGH


def test_list_for_student_orders_newest_first_and_scopes_by_student(repo):
    async def seed():
        await repo.create(student_id="stu-1", subject="first", body="b")
        await repo.create(student_id="stu-1", subject="second", body="b")
        await repo.create(student_id="stu-2", subject="other", body="b")

    asyncio.run(seed())

    records = asyncio.run(repo.list_for_student("stu-1"))
    assert [r.subject for r in records] == ["second", "first"]

    other = asyncio.run(repo.list_for_student("stu-2"))
    assert len(other) == 1


def test_list_for_student_pagination(repo):
    async def seed():
        for i in range(5):
            await repo.create(student_id="stu-1", subject=f"n{i}", body="b")

    asyncio.run(seed())

    page1 = asyncio.run(repo.list_for_student("stu-1", limit=2, offset=0))
    page2 = asyncio.run(repo.list_for_student("stu-1", limit=2, offset=2))
    assert len(page1) == 2 and len(page2) == 2
    assert {r.id for r in page1}.isdisjoint({r.id for r in page2})


def test_list_for_student_unread_only(repo):
    async def seed():
        n1 = await repo.create(student_id="stu-1", subject="a", body="b")
        await repo.create(student_id="stu-1", subject="b", body="b")
        await repo.mark_read(n1.id)

    asyncio.run(seed())

    unread = asyncio.run(repo.list_for_student("stu-1", unread_only=True))
    assert [r.subject for r in unread] == ["b"]


def test_get_returns_none_when_missing(repo):
    assert asyncio.run(repo.get("does-not-exist")) is None


def test_mark_read_updates_and_sets_read_at(repo):
    record = asyncio.run(repo.create(student_id="stu-1", subject="s", body="b"))
    updated = asyncio.run(repo.mark_read(record.id))
    assert updated.is_read is True
    assert updated.read_at is not None


def test_mark_read_is_idempotent(repo):
    record = asyncio.run(repo.create(student_id="stu-1", subject="s", body="b"))
    first = asyncio.run(repo.mark_read(record.id))
    second = asyncio.run(repo.mark_read(record.id))
    assert first.is_read is True and second.is_read is True
    assert first.read_at == second.read_at


def test_mark_read_returns_none_when_missing(repo):
    assert asyncio.run(repo.mark_read("does-not-exist")) is None


def test_mark_all_read_only_touches_target_student(repo):
    async def seed():
        await repo.create(student_id="stu-1", subject="a", body="b")
        await repo.create(student_id="stu-1", subject="b", body="b")
        await repo.create(student_id="stu-2", subject="c", body="b")

    asyncio.run(seed())

    updated = asyncio.run(repo.mark_all_read("stu-1"))
    assert updated == 2

    assert asyncio.run(repo.list_for_student("stu-1", unread_only=True)) == []
    assert len(asyncio.run(repo.list_for_student("stu-2", unread_only=True))) == 1


def test_mark_all_read_returns_zero_when_nothing_unread(repo):
    assert asyncio.run(repo.mark_all_read("ghost-student")) == 0


def test_delete_removes_row_and_reports_result(repo):
    record = asyncio.run(repo.create(student_id="stu-1", subject="s", body="b"))
    assert asyncio.run(repo.delete(record.id)) is True
    assert asyncio.run(repo.get(record.id)) is None
    assert asyncio.run(repo.delete(record.id)) is False


def test_schema_creation_is_safe_to_repeat(repo):
    # _ensure_schema is called on every connection; running several operations
    # back to back must not raise or duplicate the schema.
    async def run_many():
        for _ in range(3):
            await repo.create(student_id="stu-1", subject="s", body="b")

    asyncio.run(run_many())
    assert len(asyncio.run(repo.list_for_student("stu-1"))) == 3


def test_save_notification_preserves_opportunity_id(repo):
    reminder = ReminderMessage(subject="s", body="b", call_to_action="Apply", urgency=Urgency.LOW)
    notification_id = asyncio.run(repo.save_notification("stu-1", "opp-ml", reminder))
    record = asyncio.run(repo.get(notification_id))
    assert record.opportunity_id == "opp-ml"
