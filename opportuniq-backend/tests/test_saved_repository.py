import asyncio
import pytest
from app import database
from app.repositories import opportunity_repository, saved_repository

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "saved.sqlite"))
    monkeypatch.setattr(opportunity_repository, "get_db", database.get_db)
    monkeypatch.setattr(saved_repository, "get_db", database.get_db)
    asyncio.run(database.init_db())

async def seed():
    return (await opportunity_repository.save_opportunities(session_id="s", profile_id="p", opportunities=[{"title":"ML Intern","company":"Acme","platform":"jobspy","url":"https://x.test","skills_required":["Python"],"also_on":["LinkedIn"]}]))[0]

def test_status_normalization():
    assert saved_repository.normalize_application_status("interview_scheduled") == "Interview Scheduled"
    assert saved_repository.normalize_application_status("offer") == "Offer Received"
    with pytest.raises(ValueError): saved_repository.normalize_application_status("maybe")

def test_save_join_duplicate_update_list_delete(db):
    async def run():
        opp = await seed(); first = await saved_repository.save_opportunity(profile_id="p", opportunity_id=opp["opportunity_id"])
        duplicate = await saved_repository.save_opportunity(profile_id="p", opportunity_id=opp["opportunity_id"])
        assert first["saved_id"] == duplicate["saved_id"] and first["status"] == "Not Applied"
        assert first["title"] == "ML Intern" and first["skills_required"] == ["Python"]
        updated = await saved_repository.update_saved_opportunity(first["saved_id"], {"status":"applied", "notes":"Sent"})
        assert updated["status"] == "Applied" and updated["notes"] == "Sent"
        assert len(await saved_repository.list_saved_opportunities("p", status="applied", platform="JOBSPY")) == 1
        assert await saved_repository.delete_saved_opportunity(first["saved_id"])
        assert await opportunity_repository.get_opportunity_by_id(opp["opportunity_id"]) is not None
    asyncio.run(run())
