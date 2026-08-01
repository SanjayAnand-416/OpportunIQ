import asyncio
import inspect
from app.services import email_service, groq_service, scheduler_service

def test_canonical_signatures_and_types(monkeypatch):
    assert inspect.iscoroutinefunction(groq_service.generate_reminder)
    assert inspect.iscoroutinefunction(email_service.send_reminder_email)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    try: asyncio.run(groq_service.generate_reminder(profile_name="A", skills=[], deadline_title="D", deadline_datetime="x", days_left=1))
    except RuntimeError: pass

def test_email_failure_returns_false_without_secret_log(monkeypatch, caplog):
    monkeypatch.setenv("SMTP_APP_PASSWORD", "super-secret")
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)
    assert asyncio.run(email_service.send_reminder_email(to_email="a@b.com", subject="s", body="b")) is False
    assert "super-secret" not in caplog.text

def test_scheduler_fallback_on_groq_failure(monkeypatch):
    async def fail(**kwargs): raise RuntimeError("down")
    monkeypatch.setattr(scheduler_service, "generate_reminder", fail)
    subject, body = asyncio.run(scheduler_service._generate_reminder_content({}, {"title":"Demo"}, 1))
    assert subject == "Deadline reminder: Demo" and "in 1 day" in body
