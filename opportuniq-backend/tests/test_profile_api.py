from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.repositories import profile_repository
from app.routers import profile as profile_router
from app.services.resume_service import (
    ResumeAIExtractionError,
    ResumeAIResponseError,
    ResumeAITimeoutError,
)


VALID_PROFILE = {
    "name": "Demo Student",
    "email": "demo@example.com",
    "year_of_study": "4th Year",
    "graduation_year": 2027,
    "degree": "B.Tech CSE",
    "college": "Amrita Vishwa Vidyapeetham",
    "skills": ["Python", "SQL"],
    "target_roles": ["Data Analyst", "ML Intern"],
    "location": "Chennai",
    "opportunity_type": "Internship",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "api.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(profile_repository, "get_db", database.get_db)
    with TestClient(app) as test_client:
        yield test_client


def create_profile(client: TestClient) -> dict:
    response = client.post("/api/profile/manual", json=VALID_PROFILE)
    assert response.status_code == 201
    return response.json()


def test_manual_profile_create_returns_201_and_lists(client):
    data = create_profile(client)

    assert data["profile_id"]
    assert data["profile"]["skills"] == ["Python", "SQL"]
    assert data["profile"]["target_roles"] == ["Data Analyst", "ML Intern"]


def test_manual_profile_missing_required_field_returns_422(client):
    payload = VALID_PROFILE.copy()
    payload.pop("name")

    response = client.post("/api/profile/manual", json=payload)

    assert response.status_code == 422


def test_manual_profile_empty_skills_returns_422(client):
    payload = {**VALID_PROFILE, "skills": []}

    response = client.post("/api/profile/manual", json=payload)

    assert response.status_code == 422


def test_manual_profile_empty_target_roles_returns_422(client):
    payload = {**VALID_PROFILE, "target_roles": []}

    response = client.post("/api/profile/manual", json=payload)

    assert response.status_code == 422


def test_get_existing_profile_returns_200(client):
    created = create_profile(client)

    response = client.get(f"/api/profile/{created['profile_id']}")

    assert response.status_code == 200
    assert response.json()["profile_id"] == created["profile_id"]


def test_get_missing_profile_returns_404(client):
    response = client.get("/api/profile/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


def test_patch_scalar_update_preserves_unrelated_fields(client):
    created = create_profile(client)

    response = client.patch(
        f"/api/profile/{created['profile_id']}",
        json={"location": "Bengaluru"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["profile"]["location"] == "Bengaluru"
    assert body["profile"]["email"] == VALID_PROFILE["email"]


def test_patch_skills_update_preserves_target_roles(client):
    created = create_profile(client)

    response = client.patch(
        f"/api/profile/{created['profile_id']}",
        json={"skills": ["Python", "SQL", "FastAPI"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["skills"] == ["Python", "SQL", "FastAPI"]
    assert body["profile"]["target_roles"] == VALID_PROFILE["target_roles"]


def test_patch_missing_profile_returns_404(client):
    response = client.patch("/api/profile/missing", json={"location": "Bengaluru"})

    assert response.status_code == 404


def test_upload_unsupported_extension_returns_415(client):
    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415


def test_upload_empty_file_returns_400(client):
    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Uploaded file is empty."}


def test_upload_large_file_returns_413(client):
    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.pdf", b"x" * (profile_router.MAX_FILE_SIZE + 1), "application/pdf")},
    )

    assert response.status_code == 413


def test_upload_service_unavailable_returns_503(client, monkeypatch):
    monkeypatch.setattr(profile_router, "_resume_service_functions", lambda: (None, None))

    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["fallback"] == "manual"


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("resume.pdf", "application/pdf"),
        ("resume.doc", "application/msword"),
        (
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ],
)
def test_upload_accepts_supported_document_types(
    client, monkeypatch, filename, content_type
):
    monkeypatch.setattr(profile_router, "_resume_service_functions", lambda: (None, None))

    response = client.post(
        "/api/profile/upload",
        files={"file": (filename, b"document", content_type)},
    )

    assert response.status_code == 503
    assert response.json()["fallback"] == "manual"


@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_detail"),
    [
        (
            ResumeAITimeoutError("timeout"),
            504,
            "Resume extraction service timed out.",
        ),
        (
            ResumeAIExtractionError("rejected"),
            422,
            "Resume extraction failed.",
        ),
        (
            ResumeAIResponseError("invalid"),
            502,
            "Resume extraction returned an invalid response.",
        ),
    ],
)
def test_upload_translates_resume_service_failures(
    client, monkeypatch, exception, expected_status, expected_detail
):
    async def fail(*_args):
        raise exception

    monkeypatch.setattr(
        profile_router,
        "_resume_service_functions",
        lambda: (fail, lambda *_args, **_kwargs: {}),
    )

    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == expected_status
    assert response.json() == {
        "detail": expected_detail,
        "fallback": "manual",
    }


def test_upload_resumeai_failure_returns_422(client, monkeypatch):
    async def fake_forward_to_resumeai(file_bytes, filename, content_type):
        return SimpleNamespace(success=False, data=None)

    monkeypatch.setattr(
        profile_router,
        "_resume_service_functions",
        lambda: (fake_forward_to_resumeai, lambda data, profile_id=None: {}),
    )

    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["fallback"] == "manual"


def test_successful_resume_upload_uses_mocked_resumeai(client, monkeypatch):
    class FakeResumeData:
        def model_dump(self):
            return {
                "full_name": "Resume Student",
                "year_of_study": "3rd Year",
                "graduation_year": 2028,
                "skills": ["Python"],
                "target_roles": ["Backend Intern"],
                "preferred_location": "Remote",
                "opportunity_type": "Internship",
            }

    async def fake_forward_to_resumeai(file_bytes, filename, content_type):
        return SimpleNamespace(success=True, data=FakeResumeData())

    def fake_map_resumeai_to_profile(resumeai_data, profile_id=None):
        return {
            "profile": {
                "profile_id": profile_id,
                "name": resumeai_data["full_name"],
                "email": None,
                "year_of_study": resumeai_data["year_of_study"],
                "graduation_year": resumeai_data["graduation_year"],
                "degree": None,
                "college": None,
                "skills": resumeai_data["skills"],
                "target_roles": resumeai_data["target_roles"],
                "location": resumeai_data["preferred_location"],
                "opportunity_type": resumeai_data["opportunity_type"],
            },
            "missing_fields": ["email", "degree", "college"],
        }

    monkeypatch.setattr(
        profile_router,
        "_resume_service_functions",
        lambda: (fake_forward_to_resumeai, fake_map_resumeai_to_profile),
    )

    response = client.post(
        "/api/profile/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["profile"]["name"] == "Resume Student"
    assert body["missing_fields"] == ["email", "degree", "college"]
    stored = client.get(f"/api/profile/{body['profile_id']}")
    assert stored.status_code == 200
    assert stored.json()["name"] == "Resume Student"
    assert b"%PDF-1.4" not in Path(database.DATABASE_PATH).read_bytes()
