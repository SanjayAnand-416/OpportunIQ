import asyncio
from datetime import UTC, datetime

import pytest

from app import database
from app.repositories import gmail_repository


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "gmail.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(gmail_repository, "get_db", database.get_db)
    asyncio.run(database.init_db())
    return db_path


def test_upsert_connection_preserves_public_profile_id(temp_db):
    connection = asyncio.run(
        gmail_repository.upsert_gmail_connection(
            "profile-uuid",
            email="student@example.com",
            connected=True,
        )
    )

    assert connection["profile_id"] == "profile-uuid"
    assert connection["email"] == "student@example.com"
    assert connection["connected"] is True


def test_update_scan_metadata_stores_counts(temp_db):
    asyncio.run(gmail_repository.upsert_gmail_connection("profile-uuid", connected=True))

    connection = asyncio.run(
        gmail_repository.update_gmail_scan_metadata(
            "profile-uuid",
            last_scanned=datetime.now(UTC),
            deadlines_found=4,
            needs_review=2,
        )
    )

    assert connection["deadlines_found"] == 4
    assert connection["needs_review"] == 2
    assert connection["last_scanned"]


def test_missing_record_returns_none(temp_db):
    assert asyncio.run(gmail_repository.get_gmail_connection("missing")) is None


def test_disconnect_marks_connected_false(temp_db):
    asyncio.run(gmail_repository.upsert_gmail_connection("profile-uuid", connected=True))

    connection = asyncio.run(gmail_repository.mark_gmail_disconnected("profile-uuid"))

    assert connection["connected"] is False


def test_disconnect_missing_record_is_idempotent(temp_db):
    connection = asyncio.run(gmail_repository.mark_gmail_disconnected("profile-uuid"))

    assert connection["profile_id"] == "profile-uuid"
    assert connection["connected"] is False


def test_no_token_fields_exist_in_stored_row(temp_db):
    connection = asyncio.run(
        gmail_repository.upsert_gmail_connection(
            "profile-uuid",
            email="student@example.com",
            connected=True,
        )
    )

    assert "access_token" not in connection
    assert "refresh_token" not in connection
    assert "credentials" not in connection
