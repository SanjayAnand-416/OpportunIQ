"""Mocked end-to-end coverage for the principal backend demo journey."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import config, database
from app.main import app
from app.routers import gap_analysis, opportunities as opportunities_router
from app.services import scheduler_service


PROFILE = {
    "name": "Integration Student",
    "email": "integration@example.com",
    "year_of_study": "3rd Year",
    "graduation_year": 2027,
    "degree": "B.Tech CSE",
    "college": "NIT Demo",
    "skills": ["Python", "FastAPI", "SQL"],
    "target_roles": ["Backend Intern", "Software Intern"],
    "location": "India",
    "opportunity_type": "Internship",
}


def test_profile_to_reminder_and_gap_journey(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "journey.sqlite"))
    monkeypatch.setattr(config, "ENABLE_SCHEDULER", True)

    async def fake_search(role, location, opportunity_type):
        return [
            {
                "title": f"{role} {index}",
                "company": "Demo Company",
                "platform": "jobspy",
                "url": f"https://example.test/{role.replace(' ', '-')}/{index}",
                "skills_required": ["Python", "Docker"],
                "location": location,
                "match_score": 1 - index / 100,
                "combined_score": 1 - index / 100,
            }
            for index in range(20)
        ]

    monkeypatch.setattr(opportunities_router.jobspy_service, "search_jobs", fake_search)
    monkeypatch.setattr(
        opportunities_router, "_resolve_service_function", lambda *_args: None
    )

    async def fake_skill_gap(**_kwargs):
        return {
            "matched": ["Python"],
            "partial": [],
            "missing": ["Docker"],
            "match_percentage": 50.0,
        }

    monkeypatch.setattr(opportunities_router, "calculate_skill_gap", fake_skill_gap)

    async def fake_gap_runner(**kwargs):
        mode = (
            "profile_vs_opportunity"
            if kwargs.get("opportunity_id")
            else "profile_vs_jd"
            if kwargs.get("job_description")
            else "profile_vs_role"
        )
        return {
            "id": f"analysis-{mode}",
            "profile_id": kwargs["profile_id"],
            "opportunity_id": kwargs.get("opportunity_id"),
            "target_role": kwargs.get("target_role") or "Backend Intern",
            "analysis_mode": mode,
            "overall_assessment": "Mock-verified integration analysis.",
            "missing_skills": [],
            "suggested_projects": [],
            "evidence_data": [],
            "profile_snapshot": {"skills": PROFILE["skills"]},
            "generated_at": datetime.now(UTC).isoformat(),
        }

    monkeypatch.setattr(
        gap_analysis, "_load_gap_analysis_agent", lambda: fake_gap_runner
    )

    async def fake_reminder(**_kwargs):
        return {"subject": "Mock reminder", "body": "Mock reminder body"}

    async def fake_email(**_kwargs):
        return False

    monkeypatch.setattr(scheduler_service, "generate_reminder", fake_reminder)
    monkeypatch.setattr(scheduler_service, "send_reminder_email", fake_email)

    with TestClient(app) as client:
        created = client.post("/api/profile/manual", json=PROFILE)
        assert created.status_code == 201
        profile_id = created.json()["profile_id"]
        assert client.get(f"/api/profile/{profile_id}").status_code == 200
        updated = client.patch(
            f"/api/profile/{profile_id}", json={"location": "Remote"}
        )
        assert updated.json()["profile"]["location"] == "Remote"

        search = client.post(
            "/api/opportunities/search",
            json={"profile_id": profile_id, "force_refresh": True},
        )
        assert search.status_code == 200
        session_id = search.json()["session_id"]
        results = client.get(
            "/api/opportunities", params={"session_id": session_id}
        ).json()
        assert results["count"] == 15
        assert all(item["profile_id"] == profile_id for item in results["opportunities"])
        opportunity_id = results["opportunities"][0]["opportunity_id"]

        saved = client.post(
            f"/api/saved/{opportunity_id}", params={"profile_id": profile_id}
        )
        assert saved.status_code == 201
        saved_id = saved.json()["saved_id"]
        tracker = client.patch(f"/api/saved/{saved_id}", json={"status": "Applied"})
        assert tracker.json()["status"] == "Applied"
        skill_gap = client.get(
            f"/api/opportunities/{opportunity_id}/skill-gap",
            params={"profile_id": profile_id},
        )
        assert skill_gap.status_code == 200

        settings = client.put(
            "/api/settings/notifications",
            json={"profile_id": profile_id, "r_7d": False},
        )
        assert settings.json()["r_7d"] is False
        deadline_at = datetime.now(UTC) + timedelta(days=10)
        deadline = client.post(
            "/api/deadlines",
            json={
                "profile_id": profile_id,
                "title": "Integration Demo Deadline",
                "deadline_datetime": deadline_at.isoformat(),
                "event_type": "submission",
            },
        )
        assert deadline.status_code == 201
        deadline_id = deadline.json()["deadline"]["deadline_id"]
        assert all(not job.endswith(":7d") for job in deadline.json()["reminders_scheduled"])

        reminder = client.post(
            "/api/notifications/test", json={"deadline_id": deadline_id}
        )
        assert reminder.status_code == 200
        notifications = client.get(
            "/api/notifications", params={"profile_id": profile_id}
        ).json()
        notification_id = notifications["notifications"][0]["id"]
        assert client.patch(
            f"/api/notifications/{notification_id}/read"
        ).status_code == 200

        role_gap = client.post(
            "/api/gap-analysis/run",
            json={"profile_id": profile_id, "target_role": "Backend Intern"},
        )
        assert role_gap.status_code == 200
        assert client.get(f"/api/gap-analysis/{profile_id}").status_code == 200
        jd_gap = client.post(
            "/api/gap-analysis/run",
            json={
                "profile_id": profile_id,
                "job_description": "Python backend role requiring Docker and cloud skills. "
                * 2,
            },
        )
        assert jd_gap.json()["analysis_mode"] == "profile_vs_jd"
        opportunity_gap = client.post(
            "/api/gap-analysis/run",
            json={"profile_id": profile_id, "opportunity_id": opportunity_id},
        )
        assert opportunity_gap.status_code == 200
        assert client.get(
            f"/api/gap-analysis/{profile_id}/for-opportunity/{opportunity_id}"
        ).status_code == 200

        scheduler_service.scheduler.remove_all_jobs()
        restored = client.app.state
        del restored
        summary = client.portal.call(scheduler_service.restore_scheduled_reminders)
        assert summary["jobs_scheduled"] == 3
        assert len(scheduler_service.get_deadline_jobs(deadline_id)) == 3

        completed = client.put(
            f"/api/deadlines/{deadline_id}", json={"is_completed": True}
        )
        assert completed.status_code == 200
        assert scheduler_service.get_deadline_jobs(deadline_id) == []

    if scheduler_service.scheduler.running:
        scheduler_service.scheduler.remove_all_jobs()
        scheduler_service.shutdown_scheduler(wait=False)
