from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.oauth_state import oauth_state_manager
from app.repositories import gmail_repository, profile_repository
from app.routers import gmail as gmail_router


VALID_PROFILE = {
    "name": "Gmail Demo",
    "email": "gmail@example.com",
    "year_of_study": "4th Year",
    "graduation_year": 2027,
    "degree": "B.Tech CSE",
    "college": "Amrita Vishwa Vidyapeetham",
    "skills": ["Python"],
    "target_roles": ["ML Intern"],
    "location": "Chennai",
    "opportunity_type": "Internship",
}


class FakeGmailService:
    def __init__(self):
        self.saved = []
        self.deleted = []
        self.token_profiles = set()

    def get_authorization_url(self, profile_id, state):
        return f"https://accounts.google.com/o/oauth2/auth?scope=gmail.readonly&state={state}"

    def exchange_code_for_credentials(self, code, state=None):
        return SimpleNamespace(code=code)

    def save_credentials(self, credentials, profile_id):
        self.saved.append((credentials, profile_id))
        self.token_profiles.add(profile_id)

    def credentials_exist(self, profile_id):
        return profile_id in self.token_profiles

    def get_connected_email(self, profile_id):
        return "student@gmail.com"

    def delete_credentials(self, profile_id):
        self.deleted.append(profile_id)
        self.token_profiles.discard(profile_id)
        return True


class FakeGuardianAgent:
    def __init__(self):
        self.calls = []

    async def run_guardian_agent(self, profile_id, session_id=None):
        self.calls.append((profile_id, session_id))
        return {
            "emails_scanned": 3,
            "deadlines_found": 2,
            "needs_review": 1,
            "errors": [],
        }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "gmail-api.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(profile_repository, "get_db", database.get_db)
    monkeypatch.setattr(gmail_repository, "get_db", database.get_db)
    oauth_state_manager._states.clear()
    with TestClient(app) as test_client:
        yield test_client
    oauth_state_manager._states.clear()


def create_profile(client, **overrides):
    response = client.post(
        "/api/profile/manual",
        json={**VALID_PROFILE, **overrides},
    )
    assert response.status_code == 201
    return response.json()["profile_id"]


def test_connect_missing_profile_returns_404(client):
    assert client.get("/api/gmail/connect?profile_id=missing").status_code == 404


def test_connect_missing_service_returns_503(client, monkeypatch):
    profile_id = create_profile(client)
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: None)

    response = client.get(f"/api/gmail/connect?profile_id={profile_id}")

    assert response.status_code == 503


def test_connect_valid_request_redirects_with_state(client, monkeypatch):
    profile_id = create_profile(client)
    service = FakeGmailService()
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)

    response = client.get(f"/api/gmail/connect?profile_id={profile_id}", follow_redirects=False)

    assert response.status_code == 307
    assert "state=" in response.headers["location"]
    assert "credentials" not in response.text.lower()


def test_callback_denial_redirects_safely(client):
    response = client.get("/api/gmail/callback?error=access_denied", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].endswith("/dashboard?gmail=denied")


def test_callback_missing_code_returns_400(client):
    assert client.get("/api/gmail/callback?state=abc").status_code == 400


def test_callback_invalid_state_returns_400(client):
    response = client.get("/api/gmail/callback?code=abc&state=bad")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired OAuth state."}


def test_callback_valid_state_saves_credentials_and_updates_metadata(client, monkeypatch):
    profile_id = create_profile(client)
    state = oauth_state_manager.create_state(profile_id)
    service = FakeGmailService()
    guardian = FakeGuardianAgent()
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)
    monkeypatch.setattr(gmail_router, "_load_guardian_agent", lambda: guardian)

    response = client.get(
        f"/api/gmail/callback?code=abc&state={state}",
        follow_redirects=False,
    )
    status = client.get(f"/api/gmail/status?profile_id={profile_id}").json()

    assert response.status_code == 307
    assert "gmail=connected" in response.headers["location"]
    assert "token" not in response.headers["location"]
    assert service.saved[0][1] == profile_id
    assert guardian.calls[0][0] == profile_id
    assert status["connected"] is True
    assert status["email"] == "student@gmail.com"
    assert status["deadlines_found"] == 2


def test_status_missing_and_never_connected(client):
    assert client.get("/api/gmail/status?profile_id=missing").status_code == 404
    profile_id = create_profile(client)

    response = client.get(f"/api/gmail/status?profile_id={profile_id}")

    assert response.status_code == 200
    assert response.json()["connected"] is False


def test_status_metadata_without_token_is_not_connected(client, monkeypatch):
    profile_id = create_profile(client)
    service = FakeGmailService()
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)
    import asyncio

    asyncio.run(
        gmail_repository.upsert_gmail_connection(
            profile_id,
            email="student@gmail.com",
            connected=True,
        )
    )

    assert client.get(f"/api/gmail/status?profile_id={profile_id}").json()["connected"] is False


def test_scan_missing_profile_disconnected_and_missing_guardian(client, monkeypatch):
    assert client.post("/api/gmail/scan", json={"profile_id": "missing"}).status_code == 404
    profile_id = create_profile(client)
    assert client.post("/api/gmail/scan", json={"profile_id": profile_id}).status_code == 409

    service = FakeGmailService()
    service.token_profiles.add(profile_id)
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)
    monkeypatch.setattr(gmail_router, "_load_guardian_agent", lambda: None)

    assert client.post("/api/gmail/scan", json={"profile_id": profile_id}).status_code == 503


def test_scan_connected_flow_returns_202_and_updates_metadata(client, monkeypatch):
    profile_id = create_profile(client)
    service = FakeGmailService()
    service.token_profiles.add(profile_id)
    guardian = FakeGuardianAgent()
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)
    monkeypatch.setattr(gmail_router, "_load_guardian_agent", lambda: guardian)

    response = client.post("/api/gmail/scan", json={"profile_id": profile_id})
    status = client.get(f"/api/gmail/status?profile_id={profile_id}").json()

    assert response.status_code == 202
    assert response.json()["status"] == "started"
    assert guardian.calls[0][0] == profile_id
    assert status["deadlines_found"] == 2


def test_disconnect_missing_connected_and_already_disconnected(client, monkeypatch):
    assert client.delete("/api/gmail/disconnect?profile_id=missing").status_code == 404
    profile_id = create_profile(client)
    service = FakeGmailService()
    service.token_profiles.add(profile_id)
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)

    connected = client.delete(f"/api/gmail/disconnect?profile_id={profile_id}")
    again = client.delete(f"/api/gmail/disconnect?profile_id={profile_id}")

    assert connected.status_code == 200
    assert connected.json() == {"success": True, "profile_id": profile_id}
    assert again.status_code == 200
    assert service.deleted == [profile_id, profile_id]


def test_two_profile_oauth_sessions_and_disconnect_are_isolated(client, monkeypatch):
    first_profile = create_profile(client)
    second_profile = create_profile(
        client,
        name="Second Gmail Demo",
        email="second-gmail@example.com",
    )
    service = FakeGmailService()
    guardian = FakeGuardianAgent()
    monkeypatch.setattr(gmail_router, "_load_gmail_service", lambda: service)
    monkeypatch.setattr(gmail_router, "_load_guardian_agent", lambda: guardian)

    first_state = oauth_state_manager.create_state(first_profile)
    second_state = oauth_state_manager.create_state(second_profile)
    first_callback = client.get(
        f"/api/gmail/callback?code=first&state={first_state}",
        follow_redirects=False,
    )
    second_callback = client.get(
        f"/api/gmail/callback?code=second&state={second_state}",
        follow_redirects=False,
    )

    assert first_callback.status_code == 307
    assert second_callback.status_code == 307
    assert service.saved[0][1] == first_profile
    assert service.saved[1][1] == second_profile
    assert service.token_profiles == {first_profile, second_profile}

    disconnected = client.delete(f"/api/gmail/disconnect?profile_id={first_profile}")

    assert disconnected.status_code == 200
    assert service.credentials_exist(first_profile) is False
    assert service.credentials_exist(second_profile) is True
    assert client.get(f"/api/gmail/status?profile_id={second_profile}").json()[
        "connected"
    ] is True
