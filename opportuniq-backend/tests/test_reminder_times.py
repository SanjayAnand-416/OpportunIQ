"""Tests for pure reminder-time and timezone configuration helpers."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app import config
from app.services.scheduler_service import build_job_id, calculate_reminder_times


def test_distant_deadline_has_all_offsets():
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    result = calculate_reminder_times("2026-08-20T18:00:00Z", now=now)
    assert set(result) == {"7d", "3d", "1d", "0d"}


def test_near_deadline_skips_elapsed_offsets():
    now = datetime(2026, 8, 6, 12, tzinfo=timezone.utc)
    result = calculate_reminder_times("2026-08-08T18:00:00Z", now=now)
    assert set(result) == {"1d", "0d"}


def test_past_deadline_has_no_reminders():
    now = datetime(2026, 8, 10, tzinfo=timezone.utc)
    assert calculate_reminder_times("2026-08-08T18:00:00Z", now=now) == {}


def test_same_day_reminder_is_nine_in_application_timezone():
    zone = ZoneInfo("Asia/Kolkata")
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    result = calculate_reminder_times(
        "2026-08-08T23:59:00+05:30", now=now, app_timezone=zone
    )
    assert result["0d"].astimezone(zone).hour == 9
    assert result["0d"] == datetime(2026, 8, 8, 3, 30, tzinfo=timezone.utc)


def test_naive_datetime_is_treated_as_utc():
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    result = calculate_reminder_times(datetime(2026, 8, 10, 12), now=now)
    assert result["7d"] == datetime(2026, 8, 3, 12, tzinfo=timezone.utc)


def test_malformed_datetime_returns_empty():
    assert calculate_reminder_times("not-a-date") == {}


def test_job_id_format():
    assert build_job_id("deadline-1", "3d") == "reminder:deadline-1:3d"


def test_invalid_timezone_falls_back(monkeypatch):
    monkeypatch.setenv("APP_TIMEZONE", "Mars/Olympus")
    assert config.get_app_timezone().key == "Asia/Kolkata"
