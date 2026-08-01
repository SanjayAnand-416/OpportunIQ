import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app import database
from app.main import app
from app.services import scheduler_service

PROFILE={"name":"Ada","email":"a@b.com","year_of_study":"4","graduation_year":2027,"degree":"B.Tech","college":"NIT","skills":["Python"],"target_roles":["Engineer"],"location":"Chennai","opportunity_type":"Internship"}

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "settings.sqlite")); asyncio.run(database.init_db())
    with TestClient(app) as c: yield c

def test_defaults_partial_update_and_scheduler_filter(client):
    pid=client.post("/api/profile/manual", json=PROFILE).json()["profile_id"]
    initial=client.get("/api/settings/notifications", params={"profile_id":pid}).json()
    assert all(initial[key] for key in ("r_7d","r_3d","r_1d","r_same_day"))
    updated=client.put("/api/settings/notifications", json={"profile_id":pid,"r_7d":False,"r_same_day":False}).json()
    assert updated["r_7d"] is False and updated["r_3d"] is True
    result=scheduler_service.schedule_reminders("d", datetime.now(timezone.utc)+timedelta(days=10), pid, preferences=updated)
    assert {job.rsplit(":",1)[-1] for job in result["scheduled_jobs"]} == {"3d","1d"}
    scheduler_service.cancel_reminders("d")

def test_missing_profile(client):
    assert client.get("/api/settings/notifications", params={"profile_id":"missing"}).status_code == 404
