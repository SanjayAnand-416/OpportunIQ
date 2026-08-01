"""Deadline API integration tests for scheduling and notifications."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.repositories import deadline_repository, notification_repository, profile_repository
from app.services import scheduler_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "api.sqlite"))
    for repository in (deadline_repository, notification_repository, profile_repository):
        monkeypatch.setattr(repository, "get_db", database.get_db)
    monkeypatch.setattr(scheduler_service, "_optional_function", lambda *args: None)
    with TestClient(app) as test_client:
        yield test_client
        scheduler_service.scheduler.remove_all_jobs()


def create_profile(client: TestClient) -> str:
    response = client.post(
        "/api/profile/manual",
        json={
            "name": "Ada",
            "email": "ada@example.com",
            "year_of_study": "4th Year",
            "graduation_year": 2027,
            "degree": "B.Tech CSE",
            "college": "NIT Tiruchirappalli",
            "skills": ["Python"],
            "target_roles": ["Engineer"],
            "location": "Chennai",
            "opportunity_type": "Hackathon",
        },
    )
    assert response.status_code == 201
    return response.json()["profile_id"]


def create_deadline(client: TestClient, profile_id: str, *, days: float = 10) -> dict:
    deadline_at = datetime.now(timezone.utc) + timedelta(days=days)
    response = client.post(
        "/api/deadlines",
        json={
            "profile_id": profile_id,
            "title": "Hackathon Final Submission",
            "organization": "NIT Tiruchirappalli",
            "deadline_datetime": deadline_at.isoformat(),
            "event_type": "submission",
            "action_required": "Upload final solution",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_future_deadline_returns_four_jobs(client):
    result = create_deadline(client, create_profile(client))
    assert len(result["reminders_scheduled"]) == 4
    assert all(result["deadline"]["deadline_id"] in job for job in result["reminders_scheduled"])


def test_near_and_past_deadlines_schedule_only_future_offsets(client):
    profile_id = create_profile(client)
    near = create_deadline(client, profile_id, days=2)
    past = create_deadline(client, profile_id, days=-1)
    assert {job.rsplit(":", 1)[-1] for job in near["reminders_scheduled"]} == {"1d", "0d"}
    assert past["reminders_scheduled"] == []


@pytest.mark.parametrize("field", ["is_completed", "is_cancelled"])
def test_inactive_update_cancels_jobs(client, field):
    created = create_deadline(client, create_profile(client))
    deadline_id = created["deadline"]["deadline_id"]
    assert len(scheduler_service.get_deadline_jobs(deadline_id)) == 4
    response = client.put(f"/api/deadlines/{deadline_id}", json={field: True})
    assert response.status_code == 200
    assert scheduler_service.get_deadline_jobs(deadline_id) == []


def test_datetime_update_reschedules_and_delete_cancels(client):
    created = create_deadline(client, create_profile(client))
    deadline_id = created["deadline"]["deadline_id"]
    new_time = datetime.now(timezone.utc) + timedelta(days=2)
    response = client.put(
        f"/api/deadlines/{deadline_id}",
        json={"deadline_datetime": new_time.isoformat()},
    )
    assert response.status_code == 200
    assert len(scheduler_service.get_deadline_jobs(deadline_id)) == 2
    assert client.delete(f"/api/deadlines/{deadline_id}").status_code == 200
    assert scheduler_service.get_deadline_jobs(deadline_id) == []


def test_test_reminder_is_repeatable_and_listed(client):
    profile_id = create_profile(client)
    created = create_deadline(client, profile_id)
    deadline_id = created["deadline"]["deadline_id"]
    first = client.post("/api/notifications/test", json={"deadline_id": deadline_id})
    second = client.post("/api/notifications/test", json={"deadline_id": deadline_id})
    assert first.status_code == second.status_code == 200
    assert first.json()["notification_id"] != second.json()["notification_id"]
    response = client.get("/api/notifications", params={"profile_id": profile_id})
    assert response.status_code == 200
    assert response.json()["count"] == 2


def test_scheduler_status_is_serializable(client):
    create_deadline(client, create_profile(client))
    response = client.get("/api/notifications/scheduler/status")
    assert response.status_code == 200
    assert response.json()["running"] is True
    assert response.json()["job_count"] == 4
    assert set(response.json()["jobs"][0]) == {"id", "next_run_time"}
