"""Tests for routers/notifications.py (root package) end-to-end via TestClient."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from database import SQLiteNotificationRepository
from routers.notifications import ConnectionManager, get_connection_manager, get_repository, router


@pytest.fixture()
def client(tmp_path):
    """An isolated app + repo + connection manager per test (no shared global state)."""
    app = FastAPI()
    app.include_router(router)

    repo = SQLiteNotificationRepository(database_path=str(tmp_path / "notifications.sqlite"))
    connections = ConnectionManager()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_connection_manager] = lambda: connections

    with TestClient(app) as test_client:
        yield test_client


def create(client, *, student_id="stu-1", subject="s", body="b", **extra) -> dict:
    payload = {"student_id": student_id, "subject": subject, "body": body, **extra}
    response = client.post("/notifications", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_notification_returns_201(client):
    data = create(client, subject="Deadline soon", body="Apply by Friday.", urgency="high")
    assert data["is_read"] is False
    assert data["urgency"] == "high"
    assert data["id"]


def test_create_notification_rejects_blank_fields(client):
    response = client.post(
        "/notifications", json={"student_id": "stu-1", "subject": "", "body": "b"}
    )
    assert response.status_code == 422


def test_list_notifications_returns_200_newest_first(client):
    create(client, subject="first")
    second = create(client, subject="second")

    response = client.get("/notifications", params={"student_id": "stu-1"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["id"] == second["id"]


def test_list_notifications_scoped_by_student(client):
    create(client, student_id="stu-1")
    create(client, student_id="stu-2")

    response = client.get("/notifications", params={"student_id": "stu-1"})
    assert len(response.json()) == 1


def test_list_notifications_requires_student_id(client):
    response = client.get("/notifications")
    assert response.status_code == 422


def test_list_notifications_pagination(client):
    for i in range(5):
        create(client, subject=f"n{i}")

    page1 = client.get("/notifications", params={"student_id": "stu-1", "limit": 2, "offset": 0})
    page2 = client.get("/notifications", params={"student_id": "stu-1", "limit": 2, "offset": 2})
    ids1 = {item["id"] for item in page1.json()}
    ids2 = {item["id"] for item in page2.json()}
    assert len(ids1) == 2 and len(ids2) == 2
    assert ids1.isdisjoint(ids2)


def test_get_unread_returns_200_and_excludes_read(client):
    n1 = create(client, subject="a")
    create(client, subject="b")
    client.patch(f"/notifications/{n1['id']}/read")

    response = client.get("/notifications/unread", params={"student_id": "stu-1"})
    assert response.status_code == 200
    subjects = [item["subject"] for item in response.json()]
    assert subjects == ["b"]


def test_mark_notification_read_returns_200(client):
    n1 = create(client)
    response = client.patch(f"/notifications/{n1['id']}/read")
    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert response.json()["read_at"] is not None


def test_mark_notification_read_is_idempotent(client):
    n1 = create(client)
    first = client.patch(f"/notifications/{n1['id']}/read")
    second = client.patch(f"/notifications/{n1['id']}/read")
    assert first.status_code == 200 and second.status_code == 200
    assert second.json()["is_read"] is True


def test_mark_notification_read_404_when_missing(client):
    response = client.patch("/notifications/does-not-exist/read")
    assert response.status_code == 404


def test_mark_all_read_returns_count_and_is_scoped(client):
    create(client, student_id="stu-1")
    create(client, student_id="stu-1")
    create(client, student_id="stu-2")

    response = client.patch("/notifications/read-all", params={"student_id": "stu-1"})
    assert response.status_code == 200
    assert response.json() == {"updated": 2}

    assert client.get("/notifications/unread", params={"student_id": "stu-1"}).json() == []
    assert len(client.get("/notifications/unread", params={"student_id": "stu-2"}).json()) == 1


def test_mark_all_read_returns_zero_when_nothing_unread(client):
    response = client.patch("/notifications/read-all", params={"student_id": "ghost"})
    assert response.status_code == 200
    assert response.json() == {"updated": 0}


def test_delete_notification_returns_204(client):
    n1 = create(client)
    response = client.delete(f"/notifications/{n1['id']}")
    assert response.status_code == 204
    assert response.content == b""

    assert client.get("/notifications", params={"student_id": "stu-1"}).json() == []


def test_delete_notification_404_when_missing_or_already_deleted(client):
    n1 = create(client)
    client.delete(f"/notifications/{n1['id']}")
    response = client.delete(f"/notifications/{n1['id']}")
    assert response.status_code == 404


def test_websocket_receives_push_on_create(client):
    with client.websocket_connect("/notifications/ws/stu-live") as ws:
        data = create(client, student_id="stu-live", subject="live update")
        message = ws.receive_json()
        assert message["type"] == "notification"
        assert message["id"] == data["id"]
        assert message["subject"] == "live update"


def test_create_with_no_active_socket_does_not_error(client):
    response = client.post(
        "/notifications", json={"student_id": "stu-lonely", "subject": "s", "body": "b"}
    )
    assert response.status_code == 201


def test_websocket_disconnect_stops_further_pushes(client):
    with client.websocket_connect("/notifications/ws/stu-2") as ws:
        create(client, student_id="stu-2", subject="first")
        ws.receive_json()

    # Socket now closed; a second create for the same student must not raise.
    response = client.post(
        "/notifications", json={"student_id": "stu-2", "subject": "second", "body": "b"}
    )
    assert response.status_code == 201
