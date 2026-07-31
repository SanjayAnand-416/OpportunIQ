import asyncio

import pytest

from app import database
from app.repositories import opportunity_repository
from app.repositories.opportunity_repository import _deserialize_list, _serialize_list


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "opportunities.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(opportunity_repository, "get_db", database.get_db)
    asyncio.run(database.init_db())
    return db_path


def fake_opportunity(**overrides):
    data = {
        "title": "ML Intern",
        "company": "Acme",
        "platform": "jobspy",
        "url": "https://example.com/ml",
        "location": "Chennai",
        "skills_required": ["Python"],
        "also_on": ["LinkedIn"],
        "combined_score": 0.8,
    }
    data.update(overrides)
    return data


def test_list_serialization_and_malformed_fallback():
    assert _deserialize_list(_serialize_list(["Python"])) == ["Python"]
    assert _deserialize_list("{bad") == []


def test_bulk_save_and_session_retrieval(temp_db):
    saved = asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="session-1",
            profile_id="profile-uuid",
            opportunities=[
                fake_opportunity(combined_score=0.2),
                fake_opportunity(
                    title="Data Analyst",
                    url="https://example.com/data",
                    combined_score=0.9,
                ),
            ],
        )
    )

    assert len(saved) == 2
    assert saved[0]["combined_score"] == 0.9
    assert saved[0]["profile_id"] == "profile-uuid"
    assert saved[0]["skills_required"] == ["Python"]
    assert saved[0]["also_on"] == ["LinkedIn"]


def test_latest_profile_session_returns_only_latest(temp_db):
    asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="old-session",
            profile_id="profile-uuid",
            opportunities=[fake_opportunity(url="https://example.com/old", combined_score=0.1)],
        )
    )
    asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="new-session",
            profile_id="profile-uuid",
            opportunities=[fake_opportunity(url="https://example.com/new", combined_score=0.9)],
        )
    )

    latest = asyncio.run(
        opportunity_repository.get_latest_opportunities_by_profile("profile-uuid")
    )

    assert len(latest) == 1
    assert latest[0]["session_id"] == "new-session"


def test_expired_and_duplicate_records_are_excluded(temp_db):
    saved = asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="session-dup",
            profile_id="profile-uuid",
            opportunities=[
                fake_opportunity(url="https://example.com/dup"),
                fake_opportunity(title="Duplicate", url="https://example.com/dup"),
                fake_opportunity(
                    title="Expired",
                    url="https://example.com/expired",
                    is_expired=True,
                ),
            ],
        )
    )

    assert len(saved) == 1
    assert saved[0]["url"] == "https://example.com/dup"


def test_single_opportunity_retrieval(temp_db):
    saved = asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="session-one",
            profile_id="profile-uuid",
            opportunities=[fake_opportunity()],
        )
    )

    retrieved = asyncio.run(
        opportunity_repository.get_opportunity_by_id(saved[0]["opportunity_id"])
    )

    assert retrieved["title"] == "ML Intern"


def test_cache_hit_and_miss_after_expiry(temp_db):
    asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="cache-session",
            profile_id="profile-uuid",
            opportunities=[fake_opportunity()],
        )
    )

    cached = asyncio.run(opportunity_repository.get_cached_discovery("profile-uuid", 30))
    assert cached is not None
    assert cached[0] == "cache-session"

    async def age_records():
        async with database.get_db() as db:
            await db.execute(
                "UPDATE opportunities SET fetched_at = '2000-01-01 00:00:00'"
            )
            await db.commit()

    asyncio.run(age_records())

    assert asyncio.run(opportunity_repository.get_cached_discovery("profile-uuid", 30)) is None


def test_delete_session_works(temp_db):
    asyncio.run(
        opportunity_repository.save_opportunities(
            session_id="delete-session",
            profile_id="profile-uuid",
            opportunities=[fake_opportunity()],
        )
    )

    deleted = asyncio.run(opportunity_repository.delete_opportunities_by_session("delete-session"))
    remaining = asyncio.run(
        opportunity_repository.get_opportunities_by_session("delete-session")
    )

    assert deleted == 1
    assert remaining == []
