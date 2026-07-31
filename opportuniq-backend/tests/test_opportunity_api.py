import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.models import StudentProfile
from app.repositories import opportunity_repository, profile_repository
from app.routers import opportunities as opportunities_router


VALID_PROFILE = {
    "name": "Discovery Demo",
    "email": "discovery@example.com",
    "year_of_study": "4th Year",
    "graduation_year": 2027,
    "degree": "B.Tech CSE",
    "college": "Amrita Vishwa Vidyapeetham",
    "skills": ["Python", "FastAPI", "SQL"],
    "target_roles": ["ML Intern", "Data Analyst"],
    "location": "Chennai",
    "opportunity_type": "Internship",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "opportunity-api.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(profile_repository, "get_db", database.get_db)
    monkeypatch.setattr(opportunity_repository, "get_db", database.get_db)
    with TestClient(app) as test_client:
        yield test_client


def create_profile(client):
    response = client.post("/api/profile/manual", json=VALID_PROFILE)
    assert response.status_code == 201
    return response.json()["profile_id"]


def fake_raw(title="ML Intern", url="https://example.com/ml", company="Acme"):
    return {
        "title": title,
        "company": company,
        "platform": "jobspy",
        "url": url,
        "description": "Python FastAPI internship",
        "location": "Chennai",
        "skills_required": ["Python"],
    }


def test_query_endpoints_validate_parameters(client):
    assert client.get("/api/opportunities").status_code == 400
    assert client.get("/api/opportunities?session_id=s&profile_id=p").status_code == 400
    assert client.get("/api/opportunities?session_id=missing").json()["count"] == 0
    assert client.get("/api/opportunities/missing").status_code == 404


def test_query_returns_session_profile_and_single_opportunity(client):
    profile_id = create_profile(client)
    saved = client.app.dependency_overrides
    del saved
    import asyncio

    opportunities = asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="session-1",
            profile_id=profile_id,
            opportunities=[fake_raw(title="ML Intern")],
        )
    )

    by_session = client.get("/api/opportunities?session_id=session-1")
    by_profile = client.get(f"/api/opportunities?profile_id={profile_id}")
    single = client.get(f"/api/opportunities/{opportunities[0]['opportunity_id']}")

    assert by_session.status_code == 200
    assert by_session.json()["count"] == 1
    assert by_profile.json()["opportunities"][0]["session_id"] == "session-1"
    assert single.json()["profile_id"] == profile_id


def test_search_missing_profile_and_no_roles(client):
    assert client.post(
        "/api/opportunities/search",
        json={"profile_id": "missing"},
    ).status_code == 404

    import asyncio

    asyncio.run(
        profile_repository.create_profile(
            StudentProfile(profile_id="no-roles", name="No Roles", skills=["Python"])
        )
    )
    assert client.post(
        "/api/opportunities/search",
        json={"profile_id": "no-roles"},
    ).status_code == 422


def test_cached_search_and_force_refresh_bypass(client, monkeypatch):
    profile_id = create_profile(client)
    import asyncio

    asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="cached-session",
            profile_id=profile_id,
            opportunities=[fake_raw()],
        )
    )

    cached = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": False},
    )
    assert cached.json()["cached"] is True
    assert cached.json()["session_id"] == "cached-session"

    async def fake_execute(session_id, profile):
        await opportunity_repository.save_opportunities(
            session_id=session_id,
            profile_id=profile["profile_id"],
            opportunities=[fake_raw(url="https://example.com/new")],
        )

    monkeypatch.setattr(opportunities_router, "execute_and_persist_discovery", fake_execute)
    fresh = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": True},
    )

    assert fresh.status_code == 200
    assert fresh.json()["cached"] is False
    assert fresh.json()["status"] == "started"


def test_background_pipeline_persists_jobspy_only_results(client, monkeypatch):
    profile_id = create_profile(client)

    async def fake_search_jobs(role, location, opportunity_type):
        return [fake_raw(title=f"{role} Role", url=f"https://example.com/{role.replace(' ', '-')}")]

    monkeypatch.setattr(opportunities_router.jobspy_service, "search_jobs", fake_search_jobs)
    monkeypatch.setattr(opportunities_router, "_resolve_service_function", lambda module, fn: None)

    response = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": True},
    )
    session_id = response.json()["session_id"]
    results = client.get(f"/api/opportunities?session_id={session_id}").json()

    assert response.json()["status"] == "started"
    assert results["count"] == 2
    assert results["opportunities"][0]["profile_id"] == profile_id


def test_tavily_only_success_when_jobspy_empty(client, monkeypatch):
    profile_id = create_profile(client)

    async def fake_search_jobs(role, location, opportunity_type):
        return []

    async def fake_tavily(role, skills):
        return [fake_raw(title=f"{role} Hackathon", url=f"https://example.com/tavily-{role}")]

    def fake_resolver(module, function):
        if module == "tavily_service":
            return fake_tavily
        return None

    monkeypatch.setattr(opportunities_router.jobspy_service, "search_jobs", fake_search_jobs)
    monkeypatch.setattr(opportunities_router, "_resolve_service_function", fake_resolver)

    session_id = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": True},
    ).json()["session_id"]

    assert client.get(f"/api/opportunities?session_id={session_id}").json()["count"] == 2


def test_groq_failure_is_skipped_and_ranker_missing_fallback_used(client, monkeypatch):
    profile_id = create_profile(client)

    async def fake_search_jobs(role, location, opportunity_type):
        return [
            fake_raw(title="Bad", url="https://example.com/bad"),
            fake_raw(title="Good", url="https://example.com/good"),
        ]

    def fake_extract(raw_text):
        if "Bad" in raw_text:
            raise RuntimeError("llm failed")
        return {
            "title": "Good",
            "company": "Acme",
            "platform": "jobspy",
            "url": "https://example.com/good",
            "skills_required": ["Python"],
        }

    def fake_resolver(module, function):
        if module == "groq_service":
            return fake_extract
        return None

    monkeypatch.setattr(opportunities_router.jobspy_service, "search_jobs", fake_search_jobs)
    monkeypatch.setattr(opportunities_router, "_resolve_service_function", fake_resolver)

    session_id = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": True},
    ).json()["session_id"]

    body = client.get(f"/api/opportunities?session_id={session_id}").json()
    assert body["count"] == 1
    assert body["opportunities"][0]["title"] == "Good"


def test_all_sources_fail_does_not_crash(client, monkeypatch):
    profile_id = create_profile(client)

    async def fake_search_jobs(role, location, opportunity_type):
        return []

    monkeypatch.setattr(opportunities_router.jobspy_service, "search_jobs", fake_search_jobs)
    monkeypatch.setattr(opportunities_router, "_resolve_service_function", lambda module, fn: None)

    response = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": True},
    )

    assert response.status_code == 200
    empty_results = client.get(
        f"/api/opportunities?session_id={response.json()['session_id']}"
    ).json()
    assert empty_results["count"] == 0


def test_top_15_limit_is_enforced(client, monkeypatch):
    profile_id = create_profile(client)

    async def fake_search_jobs(role, location, opportunity_type):
        return [
            fake_raw(title=f"Role {index}", url=f"https://example.com/{role}-{index}")
            for index in range(20)
        ]

    monkeypatch.setattr(opportunities_router.jobspy_service, "search_jobs", fake_search_jobs)
    monkeypatch.setattr(opportunities_router, "_resolve_service_function", lambda module, fn: None)

    session_id = client.post(
        "/api/opportunities/search",
        json={"profile_id": profile_id, "force_refresh": True},
    ).json()["session_id"]

    assert client.get(f"/api/opportunities?session_id={session_id}").json()["count"] == 15
