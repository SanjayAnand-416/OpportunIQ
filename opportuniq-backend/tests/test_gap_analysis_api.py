import asyncio
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app import database
from app.main import app
from app.models import StudentProfile
from app.repositories import opportunity_repository, profile_repository
from app.routers import gap_analysis

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database,"DATABASE_PATH",str(tmp_path/"api.sqlite")); asyncio.run(database.init_db())
    with TestClient(app) as c: yield c

def seed():
    profile=asyncio.run(profile_repository.create_profile(StudentProfile(name="Ada",email="a@b.com",skills=["Python"])))
    opp=asyncio.run(opportunity_repository.save_opportunities(session_id="s",profile_id=profile["profile_id"],opportunities=[{"title":"ML Intern","company":"Acme","platform":"jobspy","url":"https://x.test"}]))[0]
    return profile,opp

def result(profile_id, mode="profile_vs_role", opportunity_id=None):
    return {"id":"analysis","profile_id":profile_id,"opportunity_id":opportunity_id,"target_role":"ML Intern","analysis_mode":mode,"overall_assessment":"A sufficiently detailed overall assessment.","missing_skills":[],"suggested_projects":[],"evidence_data":[],"profile_snapshot":{},"generated_at":datetime.now(timezone.utc).isoformat()}

def test_validation_and_missing_entities(client):
    assert client.post("/api/gap-analysis/run",json={"profile_id":"p"}).status_code == 422
    assert client.post("/api/gap-analysis/run",json={"profile_id":"missing","target_role":"ML"}).status_code == 404

def test_agent_unavailable_is_503(client,monkeypatch):
    profile,_=seed(); monkeypatch.setattr(gap_analysis,"_load_gap_analysis_agent",lambda:None)
    assert client.post("/api/gap-analysis/run",json={"profile_id":profile["profile_id"],"target_role":"ML"}).status_code == 503

def test_role_run_persists_and_gets_latest(client,monkeypatch):
    profile,_=seed()
    async def run(**kwargs): return result(profile["profile_id"])
    monkeypatch.setattr(gap_analysis,"_load_gap_analysis_agent",lambda:run)
    response=client.post("/api/gap-analysis/run",json={"profile_id":profile["profile_id"],"target_role":"ML"})
    assert response.status_code == 200
    assert client.get(f"/api/gap-analysis/{profile['profile_id']}").status_code == 200

def test_opportunity_precedence_and_jd_ephemeral(client,monkeypatch):
    profile,opp=seed(); calls=[]
    async def run(**kwargs):
        calls.append(kwargs); mode="profile_vs_opportunity" if kwargs.get("opportunity_id") else "profile_vs_jd"
        return result(profile["profile_id"],mode,kwargs.get("opportunity_id"))
    monkeypatch.setattr(gap_analysis,"_load_gap_analysis_agent",lambda:run)
    payload={"profile_id":profile["profile_id"],"opportunity_id":opp["opportunity_id"],"job_description":"x"*60,"target_role":"Role"}
    response=client.post("/api/gap-analysis/run",json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["analysis_mode"] == "profile_vs_opportunity"
    assert client.get(f"/api/gap-analysis/{profile['profile_id']}/for-opportunity/{opp['opportunity_id']}").status_code == 200
    assert client.post("/api/gap-analysis/run",json={"profile_id":profile["profile_id"],"job_description":"y"*60,"target_role":"Role"}).status_code == 200
