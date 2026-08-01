"""Seed and safely reset deterministic records for an offline demo."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import config
from app.database import get_db, init_db
from app.models import GapAnalysisResult, StudentProfile
from app.repositories import (
    gap_analysis_repository,
    notification_repository,
    opportunity_repository,
    profile_repository,
    saved_repository,
    settings_repository,
)
from app.services import deadline_service, scheduler_service


DEMO_PROFILE_ID = "10000000-0000-4000-8000-000000000001"
DEMO_SESSION_ID = "20000000-0000-4000-8000-000000000001"
DEMO_OPPORTUNITY_IDS = [
    f"30000000-0000-4000-8000-{index:012d}" for index in range(1, 11)
]


OPPORTUNITIES = [
    ("Backend Engineering Intern", "Razorpay", "Python", 0.96),
    ("Machine Learning Intern", "Google", "Machine Learning", 0.92),
    ("Software Engineering Intern", "Microsoft", "Java", 0.89),
    ("HackNITR 2026", "NIT Rourkela", "React", 0.86),
    ("Cloud Engineering Intern", "Salesforce", "AWS", 0.82),
    ("Data Science Intern", "Swiggy", "SQL", 0.79),
    ("Full Stack Intern", "Zoho", "JavaScript", 0.76),
    ("DevOps Intern", "Freshworks", "Docker", 0.73),
    ("Open Source Fellowship", "GSoC", "Git", 0.70),
    ("Research Internship", "IISc", "Python", 0.68),
]


async def reset_demo_records() -> None:
    """Delete only records owned by the fixed demo profile/session."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM deadline_registry WHERE profile_id = ?", (DEMO_PROFILE_ID,)
        )
        deadline_ids = [row[0] for row in await cursor.fetchall()]
        await cursor.close()
        for deadline_id in deadline_ids:
            scheduler_service.cancel_reminders(deadline_id)
        for statement, values in (
            ("DELETE FROM notifications WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM deadline_registry WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM gap_analyses WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM saved_opportunities WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM notification_settings WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM gmail_connections WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM opportunities WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
            ("DELETE FROM student_profiles WHERE profile_id = ?", (DEMO_PROFILE_ID,)),
        ):
            await db.execute(statement, values)
        await db.commit()


async def seed_demo(*, with_scheduler: bool) -> dict[str, int | str]:
    await init_db()
    await reset_demo_records()
    config.ENABLE_SCHEDULER = with_scheduler
    if with_scheduler:
        scheduler_service.start_scheduler()

    profile = await profile_repository.create_profile(
        StudentProfile(
            profile_id=DEMO_PROFILE_ID,
            name="Demo Student",
            email="demo.student@example.com",
            year_of_study="3rd Year",
            graduation_year=2027,
            degree="B.Tech Computer Science",
            college="OpportunIQ Demo University",
            skills=["Python", "FastAPI", "SQL", "React", "Git"],
            target_roles=["Backend Engineer", "Software Engineer"],
            location="India",
            opportunity_type="Internship",
        )
    )

    now = datetime.now(UTC).replace(microsecond=0)
    opportunity_payloads = []
    for index, (title, company, skill, score) in enumerate(OPPORTUNITIES):
        opportunity_payloads.append(
            {
                "opportunity_id": DEMO_OPPORTUNITY_IDS[index],
                "title": title,
                "company": company,
                "platform": ("company-portal", "jobspy", "unstop")[index % 3],
                "url": f"https://example.com/opportuniq-demo/{index + 1}",
                "location": "Remote" if index % 2 else "Bengaluru, India",
                "deadline": (now + timedelta(days=index + 5)).date().isoformat(),
                "skills_required": [skill, "Communication"],
                "description": "Deterministic offline demo opportunity.",
                "match_score": score,
                "urgency_score": round(0.5 + index * 0.03, 2),
                "combined_score": score,
            }
        )
    opportunities = await opportunity_repository.save_opportunities(
        session_id=DEMO_SESSION_ID,
        profile_id=DEMO_PROFILE_ID,
        opportunities=opportunity_payloads,
    )

    saved = []
    for opportunity_id, status in zip(
        DEMO_OPPORTUNITY_IDS[:3],
        ("Not Applied", "Applied", "Interview Scheduled"),
        strict=True,
    ):
        item = await saved_repository.save_opportunity(
            profile_id=DEMO_PROFILE_ID, opportunity_id=opportunity_id
        )
        saved.append(
            await saved_repository.update_saved_opportunity(
                item["saved_id"], {"status": status}
            )
        )

    deadline_specs = (
        ("Future application deadline", now + timedelta(days=30), False, "future"),
        ("Due soon assessment", now + timedelta(days=2), False, "due-soon"),
        ("Overdue follow-up", now - timedelta(days=2), False, "overdue"),
        ("Deadline date needs review", None, True, "needs-review"),
    )
    deadlines = []
    for title, due_at, needs_review, key in deadline_specs:
        result = await deadline_service.create_gmail_deadline(
            profile_id=DEMO_PROFILE_ID,
            title=title,
            organization="OpportunIQ Demo",
            deadline_datetime=due_at,
            action_required="Review this clearly marked demo item.",
            notes="Seeded offline demo data; not extracted from live Gmail.",
            gmail_message_id=f"opportuniq-demo-{key}",
            confidence=0.95 if not needs_review else 0.4,
            needs_review=needs_review,
        )
        deadline = result["deadline"]
        deadlines.append(deadline)
        await notification_repository.create_notification(
            profile_id=DEMO_PROFILE_ID,
            deadline_id=deadline["deadline_id"],
            subject=f"Demo: {title}",
            message="Offline demo notification; no email was sent.",
            channel="dashboard",
            reminder_offset=f"demo-{key}",
        )

    await settings_repository.update_notification_settings(
        DEMO_PROFILE_ID,
        {"r_7d": True, "r_3d": True, "r_1d": True, "r_same_day": True},
    )

    common_gap = {
        "profile_id": DEMO_PROFILE_ID,
        "target_role": "Backend Engineer",
        "overall_assessment": "Seeded demo analysis for offline presentation.",
        "missing_skills": [
            {
                "skill": "Docker",
                "priority": "high",
                "reason": "Not present in the demo profile.",
                "evidence_level": 0,
                "learning_path_order": 1,
                "cluster_name": "Deployment",
                "learning_resources": [],
            }
        ],
        "suggested_projects": [
            {
                "project_type": "API deployment",
                "description": "Containerize and deploy a FastAPI service.",
                "skills_addressed": ["Docker"],
            }
        ],
        "evidence_data": [],
        "profile_snapshot": {"skills": profile["skills"], "demo": True},
        "generated_at": now,
    }
    role_analysis = GapAnalysisResult(
        id="40000000-0000-4000-8000-000000000001",
        analysis_mode="profile_vs_role",
        **common_gap,
    )
    opportunity_analysis = GapAnalysisResult(
        id="40000000-0000-4000-8000-000000000002",
        opportunity_id=DEMO_OPPORTUNITY_IDS[0],
        analysis_mode="profile_vs_opportunity",
        **common_gap,
    )
    await gap_analysis_repository.save_gap_analysis(role_analysis)
    await gap_analysis_repository.save_gap_analysis(opportunity_analysis)

    return {
        "profile_id": DEMO_PROFILE_ID,
        "opportunities": len(opportunities),
        "saved": len(saved),
        "deadlines": len(deadlines),
        "notifications": len(deadlines),
        "gap_analyses": 2,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Reset before reseeding")
    parser.add_argument("--with-scheduler", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    summary = await seed_demo(with_scheduler=args.with_scheduler)
    if args.print_summary:
        for key, value in summary.items():
            print(f"{key}: {value}")
    if args.with_scheduler:
        scheduler_service.shutdown_scheduler(wait=False)


if __name__ == "__main__":
    asyncio.run(async_main())
