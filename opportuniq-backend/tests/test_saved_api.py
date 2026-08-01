import asyncio
import pytest
from fastapi.testclient import TestClient
from app import database
from app.main import app
from app.repositories import opportunity_repository

PROFILE={"name":"Ada","email":"a@b.com","year_of_study":"4","graduation_year":2027,"degree":"B.Tech","college":"NIT","skills":["Python"],"target_roles":["Engineer"],"location":"Chennai","opportunity_type":"Internship"}

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "api.sqlite")); asyncio.run(database.init_db())
    with TestClient(app) as c: yield c

def setup_data(client):
    pid=client.post("/api/profile/manual", json=PROFILE).json()["profile_id"]
    opp=asyncio.run(opportunity_repository.save_opportunities(session_id="s", profile_id=pid, opportunities=[{"title":"Intern","company":"Acme","platform":"jobspy","url":"https://x.test","skills_required":["Python"]}]))[0]
    return pid, opp

def test_saved_crud_join_and_validation(client):
    pid, opp=setup_data(client); url=f"/api/saved/{opp['opportunity_id']}?profile_id={pid}"
    first=client.post(url); second=client.post(url)
    assert first.status_code == second.status_code == 201 and first.json()["saved_id"] == second.json()["saved_id"]
    saved_id=first.json()["saved_id"]
    listed=client.get("/api/saved", params={"profile_id":pid,"platform":"JOBSPY"}).json()
    assert listed["count"] == 1 and listed["saved"][0]["title"] == "Intern"
    assert client.patch(f"/api/saved/{saved_id}", json={"status":"nonsense"}).status_code == 422
    assert client.patch(f"/api/saved/{saved_id}", json={"status":"offer","notes":"Great"}).json()["status"] == "Offer Received"
    assert client.delete(f"/api/saved/{saved_id}").status_code == 200
    assert asyncio.run(opportunity_repository.get_opportunity_by_id(opp["opportunity_id"])) is not None

def test_saved_missing_entities(client):
    assert client.post("/api/saved/missing?profile_id=missing").status_code == 404
