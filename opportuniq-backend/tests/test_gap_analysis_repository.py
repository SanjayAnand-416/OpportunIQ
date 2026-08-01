import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from app import database
from app.repositories import gap_analysis_repository as repo

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "gap.sqlite")); monkeypatch.setattr(repo, "get_db", database.get_db); asyncio.run(database.init_db())

def analysis(**overrides):
    data={"profile_id":"p","target_role":"ML Intern","analysis_mode":"profile_vs_role","overall_assessment":"A sufficiently detailed overall assessment.","missing_skills":[{"skill":"Docker","priority":"high","reason":"Needed","evidence_level":0,"learning_path_order":0,"learning_resources":[]}],"suggested_projects":[],"evidence_data":[],"profile_snapshot":{"skills":["Python"]},"generated_at":datetime.now(timezone.utc).isoformat()}
    data.update(overrides); return data

def test_json_and_stale_helpers():
    assert repo._deserialize_list("bad") == [] and repo._deserialize_dict("[]") == {}
    now=datetime.now(timezone.utc); assert not repo.calculate_is_stale(now, now=now)
    assert repo.calculate_is_stale(now-timedelta(days=8), now=now) and repo.calculate_is_stale(None)

def test_role_upsert_and_jd_ephemeral(db):
    async def run():
        first=await repo.save_gap_analysis(analysis(id="one", jd_snippet="x"*400)); second=await repo.save_gap_analysis(analysis(id="two"))
        assert len(first["jd_snippet"]) == 300 and (await repo.get_latest_role_analysis("p"))["id"] == "two"
        jd=await repo.save_gap_analysis(analysis(id="jd",analysis_mode="profile_vs_jd"), persist=False)
        assert jd["id"] == "jd" and await repo.get_analysis_by_id("jd") is None
    asyncio.run(run())

def test_opportunity_isolation_and_decoding(db):
    async def run():
        saved=await repo.save_gap_analysis(analysis(id="opp",analysis_mode="profile_vs_opportunity",opportunity_id="o"))
        loaded=await repo.get_opportunity_analysis("p","o")
        assert loaded["opportunity_id"] == "o" and loaded["missing_skills"][0]["skill"] == "Docker"
        assert await repo.get_opportunity_analysis("p","missing") is None
    asyncio.run(run())
