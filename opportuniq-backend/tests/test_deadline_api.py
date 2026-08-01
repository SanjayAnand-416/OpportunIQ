from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.repositories import deadline_repository, profile_repository


VALID_PROFILE = {
    "name": "Deadline Demo",
    "email": "deadline@example.com",
    "year_of_study": "4th Year",
    "graduation_year": 2027,
    "degree": "B.Tech CSE",
    "college": "Amrita Vishwa Vidyapeetham",
    "skills": ["Python", "FastAPI"],
    "target_roles": ["Backend Intern"],
    "location": "Chennai",
    "opportunity_type": "Internship",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "deadline-api.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(profile_repository, "get_db", database.get_db)
    monkeypatch.setattr(deadline_repository, "get_db", database.get_db)
    with TestClient(app) as test_client:
        yield test_client


def create_profile(client: TestClient) -> str:
    response = client.post("/api/profile/manual", json=VALID_PROFILE)
    assert response.status_code == 201
    return response.json()["profile_id"]


def create_deadline(
    client: TestClient,
    profile_id: str,
    *,
    title: str = "Submit application",
    deadline_datetime: datetime | None = None,
) -> dict:
    response = client.post(
        "/api/deadlines",
        json={
            "profile_id": profile_id,
            "title": title,
            "organization": "Acme",
            "deadline_datetime": (
                deadline_datetime or datetime.now(UTC) + timedelta(days=4)
            ).isoformat(),
            "event_type": "application",
            "action_required": "Submit form",
        },
    )
    assert response.status_code == 201
    return response.json()["deadline"]


def test_create_list_detail_update_and_delete_deadline(client):
    profile_id = create_profile(client)
    created = create_deadline(client, profile_id)

    listing = client.get(f"/api/deadlines?profile_id={profile_id}")
    detail = client.get(f"/api/deadlines/{created['deadline_id']}")
    updated = client.put(
        f"/api/deadlines/{created['deadline_id']}",
        json={"is_completed": True, "title": "Submitted application"},
    )
    deleted = client.delete(f"/api/deadlines/{created['deadline_id']}")
    missing = client.get(f"/api/deadlines/{created['deadline_id']}")

    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert detail.json()["deadline_id"] == created["deadline_id"]
    assert updated.json()["deadline"]["status"] == "completed"
    assert updated.json()["deadline"]["title"] == "Submitted application"
    assert deleted.json() == {"success": True, "deadline_id": created["deadline_id"]}
    assert missing.status_code == 404


def test_create_missing_profile_returns_404(client):
    response = client.post(
        "/api/deadlines",
        json={
            "profile_id": "missing",
            "title": "Submit application",
            "deadline_datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 404


def test_static_filter_routes_are_not_captured_as_deadline_ids(client):
    profile_id = create_profile(client)
    now = datetime.now(UTC)
    create_deadline(client, profile_id, title="Past", deadline_datetime=now - timedelta(days=1))
    create_deadline(client, profile_id, title="Today", deadline_datetime=now)
    create_deadline(client, profile_id, title="Future", deadline_datetime=now + timedelta(days=3))

    calendar = client.get(f"/api/deadlines/calendar?profile_id={profile_id}")
    upcoming = client.get(f"/api/deadlines/upcoming?profile_id={profile_id}&days=7")
    today = client.get(f"/api/deadlines/today?profile_id={profile_id}")
    overdue = client.get(f"/api/deadlines/overdue?profile_id={profile_id}")
    needs_review = client.get(f"/api/deadlines/needs-review?profile_id={profile_id}")

    assert calendar.status_code == 200
    assert len(calendar.json()) == 3
    assert upcoming.json()["count"] == 1
    assert today.json()["count"] == 1
    assert overdue.json()["count"] == 1
    assert needs_review.json()["count"] == 0


def test_needs_review_endpoint_includes_gmail_registry_rows(client):
    profile_id = create_profile(client)
    import asyncio

    asyncio.run(
        deadline_repository.create_deadline(
            profile_id=profile_id,
            title="Extracted deadline needs review",
            deadline_datetime=None,
            source="gmail",
            gmail_message_id="gmail-msg-1",
            needs_review=True,
            confidence=0.4,
        )
    )

    response = client.get(f"/api/deadlines/needs-review?profile_id={profile_id}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["deadlines"][0]["source"] == "gmail"


def test_validation_rejects_blank_title_and_invalid_event_type(client):
    profile_id = create_profile(client)

    blank = client.post(
        "/api/deadlines",
        json={
            "profile_id": profile_id,
            "title": " ",
            "deadline_datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    invalid_event = client.post(
        "/api/deadlines",
        json={
            "profile_id": profile_id,
            "title": "Submit",
            "deadline_datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "event_type": "party",
        },
    )

    assert blank.status_code == 422
    assert invalid_event.status_code == 422
