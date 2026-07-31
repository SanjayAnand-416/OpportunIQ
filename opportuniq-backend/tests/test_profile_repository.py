import asyncio

import pytest

from app import database
from app.models import StudentProfile
from app.repositories import profile_repository
from app.repositories.profile_repository import _deserialize_list, _serialize_list


@pytest.fixture()
def temp_profile_db(tmp_path, monkeypatch):
    db_path = tmp_path / "profiles.sqlite"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(profile_repository, "get_db", database.get_db)
    asyncio.run(database.init_db())
    return db_path


def test_serialize_and_deserialize_list_fields():
    assert _deserialize_list(_serialize_list(["Python", "SQL"])) == ["Python", "SQL"]


def test_malformed_json_deserializes_to_empty_list():
    assert _deserialize_list("{not-json") == []
    assert _deserialize_list('"Python"') == []
    assert _deserialize_list(None) == []


def test_insert_and_retrieve_profile(temp_profile_db):
    profile = StudentProfile(
        profile_id="profile-1",
        name="Demo Student",
        email="demo@example.com",
        year_of_study="4th Year",
        graduation_year=2027,
        degree="B.Tech CSE",
        college="Amrita Vishwa Vidyapeetham",
        skills=["Python", "SQL"],
        target_roles=["Data Analyst"],
        location="Chennai",
        opportunity_type="Internship",
    )

    created = asyncio.run(profile_repository.create_profile(profile))
    retrieved = asyncio.run(profile_repository.get_profile_by_id("profile-1"))

    assert created["profile_id"] == "profile-1"
    assert retrieved == created
    assert retrieved["skills"] == ["Python", "SQL"]
    assert retrieved["target_roles"] == ["Data Analyst"]


def test_partial_update_preserves_unrelated_fields(temp_profile_db):
    profile = StudentProfile(
        profile_id="profile-2",
        name="Demo Student",
        email="demo@example.com",
        year_of_study="4th Year",
        degree="B.Tech CSE",
        college="Amrita Vishwa Vidyapeetham",
        skills=["Python"],
        target_roles=["ML Intern"],
        location="Chennai",
        opportunity_type="Internship",
    )
    asyncio.run(profile_repository.create_profile(profile))

    updated = asyncio.run(
        profile_repository.update_profile(
            "profile-2",
            {"location": "Bengaluru", "skills": ["Python", "FastAPI"]},
        )
    )

    assert updated["location"] == "Bengaluru"
    assert updated["skills"] == ["Python", "FastAPI"]
    assert updated["email"] == "demo@example.com"
    assert updated["target_roles"] == ["ML Intern"]


def test_empty_update_returns_current_profile(temp_profile_db):
    profile = StudentProfile(
        profile_id="profile-3",
        name="Demo Student",
        email="demo@example.com",
        skills=["Python"],
        target_roles=["ML Intern"],
    )
    created = asyncio.run(profile_repository.create_profile(profile))

    assert asyncio.run(profile_repository.update_profile("profile-3", {})) == created


def test_missing_profile_returns_none(temp_profile_db):
    assert asyncio.run(profile_repository.get_profile_by_id("missing")) is None
    assert asyncio.run(profile_repository.update_profile("missing", {"name": "Nope"})) is None
