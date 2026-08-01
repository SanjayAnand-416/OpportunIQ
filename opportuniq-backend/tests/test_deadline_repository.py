import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app import database
from app.repositories import deadline_repository


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def deadline_db(tmp_path, monkeypatch):
    db_path = tmp_path / "deadline-repository.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(deadline_repository, "get_db", database.get_db)
    run(database.init_db())
    return db_path


def test_create_manual_deadline_normalizes_utc_status_and_fetches(deadline_db):
    soon = datetime.now(UTC) + timedelta(days=5)

    created = run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Submit application",
            deadline_datetime=soon,
            source="manual",
            event_type="application",
        )
    )
    loaded = run(deadline_repository.get_deadline_by_id(created["deadline_id"]))

    assert loaded["deadline_id"] == created["deadline_id"]
    assert loaded["profile_id"] == "profile-1"
    assert loaded["status"] == "upcoming"
    assert loaded["days_remaining"] == 5
    assert loaded["deadline_datetime"].endswith("+00:00")


def test_manual_deadline_requires_datetime(deadline_db):
    with pytest.raises(ValueError, match="deadline_datetime"):
        run(
            deadline_repository.create_deadline(
                profile_id="profile-1",
                title="Missing date",
                source="manual",
            )
        )


def test_gmail_duplicate_returns_existing_deadline(deadline_db):
    created = run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="First extraction",
            deadline_datetime=None,
            source="gmail",
            gmail_message_id="msg-1",
            confidence=1.4,
            needs_review=True,
        )
    )
    duplicate = run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Second extraction",
            deadline_datetime=None,
            source="gmail",
            gmail_message_id="msg-1",
            needs_review=True,
        )
    )

    assert duplicate["deadline_id"] == created["deadline_id"]
    assert duplicate["title"] == "First extraction"
    assert duplicate["confidence"] == 1.0


def test_query_filters_and_update_statuses(deadline_db):
    now = datetime.now(UTC)
    overdue = run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Past submission",
            deadline_datetime=now - timedelta(days=2),
            source="manual",
        )
    )
    run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Today interview",
            deadline_datetime=now,
            source="manual",
            event_type="interview",
        )
    )
    run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Future assessment",
            deadline_datetime=now + timedelta(days=3),
            source="manual",
        )
    )
    run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Review extraction",
            deadline_datetime=None,
            source="gmail",
            needs_review=True,
            gmail_message_id="msg-review",
        )
    )

    assert len(run(deadline_repository.list_today_deadlines(profile_id="profile-1"))) == 1
    assert len(run(deadline_repository.list_upcoming_deadlines(profile_id="profile-1", days=7))) == 1
    assert len(run(deadline_repository.list_overdue_deadlines(profile_id="profile-1"))) == 1
    assert len(run(deadline_repository.list_needs_review_deadlines(profile_id="profile-1"))) == 1

    updated = run(
        deadline_repository.update_deadline(
            overdue["deadline_id"],
            {"is_completed": True, "title": "Completed submission"},
        )
    )

    assert updated["status"] == "completed"
    assert updated["title"] == "Completed submission"
    assert run(deadline_repository.list_overdue_deadlines(profile_id="profile-1")) == []


def test_delete_deadline_removes_row(deadline_db):
    created = run(
        deadline_repository.create_deadline(
            profile_id="profile-1",
            title="Temporary deadline",
            deadline_datetime=datetime.now(UTC) + timedelta(days=1),
            source="manual",
        )
    )

    assert run(deadline_repository.delete_deadline(created["deadline_id"])) is True
    assert run(deadline_repository.get_deadline_by_id(created["deadline_id"])) is None
