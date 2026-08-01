"""Tests for active-package reminder notification persistence."""

import asyncio

import pytest

from app import database
from app.repositories import notification_repository


@pytest.fixture()
def notification_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "notifications.sqlite"))
    monkeypatch.setattr(notification_repository, "get_db", database.get_db)
    asyncio.run(database.init_db())


def create_notification(**overrides):
    values = {
        "profile_id": "profile-public",
        "deadline_id": "deadline-public",
        "subject": "Deadline reminder",
        "message": "Submit today.",
        "channel": "dashboard",
        "reminder_offset": "1d",
    }
    values.update(overrides)
    return asyncio.run(notification_repository.create_notification(**values))


def test_create_fetch_and_duplicate_are_idempotent(notification_db):
    first = create_notification()
    fetched = asyncio.run(notification_repository.get_notification_by_id(first["id"]))
    duplicate = create_notification(subject="Changed", message="Changed")
    assert fetched == first
    assert duplicate["id"] == first["id"]
    assert first["profile_id"] == "profile-public"
    assert first["deadline_id"] == "deadline-public"


@pytest.mark.parametrize(
    ("field", "value"),
    [("channel", "sms"), ("delivery_status", "unknown")],
)
def test_rejects_invalid_enums(notification_db, field, value):
    with pytest.raises(ValueError):
        create_notification(**{field: value})


def test_updates_delivery_status_and_safe_error(notification_db):
    created = create_notification(channel="email", delivery_status="created")
    updated = asyncio.run(
        notification_repository.update_delivery_status(
            created["id"], delivery_status="failed", error_message="SMTP unavailable"
        )
    )
    assert updated["delivery_status"] == "failed"
    assert updated["error_message"] == "SMTP unavailable"


def test_lists_and_marks_notifications_read(notification_db):
    first = create_notification(reminder_offset="7d")
    create_notification(reminder_offset="3d")
    unread = asyncio.run(
        notification_repository.list_notifications("profile-public", unread_only=True)
    )
    assert len(unread) == 2
    marked = asyncio.run(notification_repository.mark_notification_read(first["id"]))
    assert marked["is_read"] is True
    assert asyncio.run(
        notification_repository.mark_all_notifications_read("profile-public")
    ) == 1
    assert asyncio.run(
        notification_repository.list_notifications("profile-public", unread_only=True)
    ) == []
