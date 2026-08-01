"""Contract tests for the active ResumeAI HTTP adapter."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
from pydantic import BaseModel

from app.services import resume_service


class FakeAsyncClient:
    response = None
    raised = None
    request = None

    def __init__(self, *, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, *, files, headers):
        type(self).request = {"url": url, "files": files, "headers": headers}
        if type(self).raised is not None:
            raise type(self).raised
        return type(self).response


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch):
    FakeAsyncClient.response = None
    FakeAsyncClient.raised = None
    FakeAsyncClient.request = None
    monkeypatch.setattr(resume_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setenv("RESUMEAI_API_URL", "https://resume.test/extract")
    monkeypatch.delenv("RESUMEAI_API_KEY", raising=False)


def test_active_adapter_imports():
    assert callable(resume_service.forward_to_resumeai)
    assert callable(resume_service.map_resumeai_to_profile)


def test_forward_uses_person_c_multipart_contract_without_real_call():
    FakeAsyncClient.response = SimpleNamespace(
        is_success=True,
        json=lambda: {"success": True, "data": {"full_name": "Ada"}},
    )

    result = asyncio.run(
        resume_service.forward_to_resumeai(
            b"resume bytes", "resume.pdf", "application/pdf"
        )
    )

    assert result.success is True
    assert result.data == {"full_name": "Ada"}
    assert FakeAsyncClient.request["url"] == "https://resume.test/extract"
    assert FakeAsyncClient.request["files"]["file"] == (
        "resume.pdf",
        b"resume bytes",
        "application/pdf",
    )


def test_forward_requires_configuration(monkeypatch):
    monkeypatch.delenv("RESUMEAI_API_URL")
    with pytest.raises(resume_service.ResumeAIConfigurationError):
        asyncio.run(
            resume_service.forward_to_resumeai(
                b"x", "resume.pdf", "application/pdf"
            )
        )


def test_forward_translates_timeout():
    request = httpx.Request("POST", "https://resume.test/extract")
    FakeAsyncClient.raised = httpx.ReadTimeout("timeout", request=request)
    with pytest.raises(resume_service.ResumeAITimeoutError):
        asyncio.run(
            resume_service.forward_to_resumeai(
                b"x", "resume.pdf", "application/pdf"
            )
        )


def test_forward_rejects_malformed_json():
    def invalid_json():
        raise ValueError("not json")

    FakeAsyncClient.response = SimpleNamespace(is_success=True, json=invalid_json)
    with pytest.raises(resume_service.ResumeAIResponseError):
        asyncio.run(
            resume_service.forward_to_resumeai(
                b"x", "resume.pdf", "application/pdf"
            )
        )


class PersonCResult(BaseModel):
    full_name: str
    email: str
    skills: list[str]
    target_roles: list[str]
    education: list[dict]
    preferred_location: str
    opportunity_type: str


@pytest.mark.parametrize("as_model", [False, True])
def test_mapping_normalizes_person_c_shape(as_model):
    payload = {
        "full_name": "  Ada Lovelace  ",
        "email": "ada@example.com",
        "skills": ["Python", "python", " SQL "],
        "target_roles": ["Backend Intern", "backend intern", "ML Intern"],
        "education": [
            {
                "degree": "B.Tech CSE",
                "institution": "NIT Demo",
                "end_year": "May 2027",
            }
        ],
        "preferred_location": "Remote",
        "opportunity_type": "internship",
    }
    source = PersonCResult(**payload) if as_model else payload

    mapped = resume_service.map_resumeai_to_profile(source, profile_id="profile-1")

    assert mapped["profile"] == {
        "profile_id": "profile-1",
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "year_of_study": None,
        "graduation_year": 2027,
        "degree": "B.Tech CSE",
        "college": "NIT Demo",
        "skills": ["Python", "SQL"],
        "target_roles": ["Backend Intern", "ML Intern"],
        "location": "Remote",
        "opportunity_type": "Internship",
    }
    assert mapped["missing_fields"] == ["year_of_study"]


def test_mapping_generates_id_and_reports_missing_fields():
    mapped = resume_service.map_resumeai_to_profile({"full_name": "Ada"})

    assert mapped["profile"]["profile_id"]
    assert "email" in mapped["missing_fields"]
    assert "skills" in mapped["missing_fields"]
    assert "target_roles" in mapped["missing_fields"]
