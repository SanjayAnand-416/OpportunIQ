"""Production-boundary tests for the active Guardian adapter."""

import asyncio
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.agents import guardian_agent


def _extraction(**overrides):
    values = {
        "has_deadline": True,
        "deadline_date": date(2026, 8, 20),
        "deadline_time": "17:30",
        "timezone": "IST",
        "raw_deadline_text": "by 5:30 PM IST on August 20",
        "is_relative": False,
        "confidence": 0.92,
        "organization": "Acme Labs",
        "event_type": "test",
        "action_required": "Complete the coding assessment",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _install_mailbox(monkeypatch, emails):
    monkeypatch.setattr(
        guardian_agent.gmail_service,
        "get_gmail_service",
        lambda profile_id: object(),
    )
    monkeypatch.setattr(
        guardian_agent.gmail_service,
        "fetch_emails_3pass",
        lambda _service: emails,
    )


def test_rich_person_c_metadata_and_timezone_are_persisted(monkeypatch):
    _install_mailbox(
        monkeypatch,
        [{"id": "message-1", "body": "Assessment details"}],
    )
    monkeypatch.setattr(
        guardian_agent.groq_service,
        "extract_deadline",
        lambda _text: _extraction(),
    )
    persisted = []

    async def fake_create(**kwargs):
        persisted.append(kwargs)
        return {"deadline": {**kwargs, "deadline_id": "deadline-1"}}

    monkeypatch.setattr(
        guardian_agent.deadline_service,
        "create_gmail_deadline",
        fake_create,
    )

    result = asyncio.run(guardian_agent.run_guardian_agent(profile_id="profile-1"))

    assert result["deadlines_found"] == 1
    assert persisted[0]["organization"] == "Acme Labs"
    assert persisted[0]["event_type"] == "assessment"
    assert persisted[0]["action_required"] == "Complete the coding assessment"
    assert persisted[0]["title"] == "Complete the coding assessment"
    assert persisted[0]["deadline_datetime"].utcoffset() == timedelta(hours=5, minutes=30)
    assert "Extracted timezone: IST." in persisted[0]["notes"]


def test_explicit_title_and_iana_timezone_are_preserved(monkeypatch):
    _install_mailbox(monkeypatch, [{"id": "message-1", "body": "Interview"}])
    extraction = _extraction(
        title="Backend internship interview",
        timezone="America/New_York",
        event_type="interview",
        action_required=None,
    )
    monkeypatch.setattr(
        guardian_agent.groq_service,
        "extract_deadline",
        lambda _text: extraction,
    )
    persisted = []

    async def fake_create(**kwargs):
        persisted.append(kwargs)
        return {"deadline": {**kwargs, "deadline_id": "deadline-1"}}

    monkeypatch.setattr(
        guardian_agent.deadline_service,
        "create_gmail_deadline",
        fake_create,
    )

    asyncio.run(guardian_agent.run_guardian_agent(profile_id="profile-1"))

    assert persisted[0]["title"] == "Backend internship interview"
    assert persisted[0]["deadline_datetime"].tzinfo.key == "America/New_York"


def test_groq_extractions_run_concurrently(monkeypatch):
    _install_mailbox(
        monkeypatch,
        [{"id": f"message-{index}", "body": f"Email {index}"} for index in range(4)],
    )
    active = 0
    peak_active = 0

    async def fake_extract(_text):
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        await asyncio.sleep(0.02)
        active -= 1
        return _extraction(has_deadline=False)

    monkeypatch.setattr(
        guardian_agent.groq_service,
        "extract_deadline",
        fake_extract,
    )

    result = asyncio.run(guardian_agent.run_guardian_agent(profile_id="profile-1"))

    assert peak_active > 1
    assert result["emails_scanned"] == 4
    assert result["deadlines_found"] == 0


def test_overall_execution_timeout_bounds_groq_work(monkeypatch):
    _install_mailbox(monkeypatch, [{"id": "message-1", "body": "Deadline"}])
    monkeypatch.setattr(guardian_agent.config, "AGENT_TIMEOUT_SECONDS", 0.01)

    async def slow_extract(_text):
        await asyncio.sleep(1)
        return _extraction()

    monkeypatch.setattr(
        guardian_agent.groq_service,
        "extract_deadline",
        slow_extract,
    )

    with pytest.raises(TimeoutError):
        asyncio.run(guardian_agent.run_guardian_agent(profile_id="profile-1"))


def test_timezone_without_extracted_value_uses_app_timezone(monkeypatch):
    fallback_timezone = guardian_agent.ZoneInfo("Europe/London")
    monkeypatch.setattr(guardian_agent.config, "APP_TIMEZONE", fallback_timezone)

    resolved = guardian_agent._deadline_datetime(_extraction(timezone=None))

    assert resolved is not None
    assert resolved.tzinfo is fallback_timezone
