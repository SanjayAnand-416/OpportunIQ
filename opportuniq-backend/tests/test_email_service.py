"""Tests for services/email_service.py (root package)."""

import asyncio
import smtplib

import pytest

import services.email_service as email_service


class FakeSMTP:
    """Stand-in for smtplib.SMTP used as a context manager."""

    behavior = "ok"
    calls = 0

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        FakeSMTP.calls += 1

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def ehlo(self):
        pass

    def starttls(self, context=None):
        pass

    def login(self, user, password):
        if FakeSMTP.behavior == "auth_fail":
            raise smtplib.SMTPAuthenticationError(535, b"bad creds")

    def send_message(self, message):
        if FakeSMTP.behavior == "recipients_refused":
            raise smtplib.SMTPRecipientsRefused({"x@x.com": (550, b"no such user")})
        if FakeSMTP.behavior == "disconnect_then_ok" and FakeSMTP.calls < 2:
            raise smtplib.SMTPServerDisconnected("connection lost")
        if FakeSMTP.behavior == "always_disconnect":
            raise smtplib.SMTPServerDisconnected("connection lost")


@pytest.fixture(autouse=True)
def _configure_credentials(monkeypatch):
    monkeypatch.setenv("SMTP_FROM_EMAIL", "bot@example.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "app-pass")


@pytest.fixture(autouse=True)
def _patch_smtp(monkeypatch):
    FakeSMTP.behavior = "ok"
    FakeSMTP.calls = 0
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service, "RETRY_BACKOFF_SECONDS", 0.01)


def send(**kwargs):
    return asyncio.run(email_service.send_reminder_email(**kwargs))


def test_happy_path_sends_on_first_attempt():
    result = send(to_email="student@x.com", subject="Deadline in 3 days", body="Apply now.")
    assert result.success is True
    assert result.attempts == 1
    assert result.message_id


def test_html_alternative_is_accepted():
    result = send(to_email="student@x.com", subject="s", body="b", html_body="<p>b</p>")
    assert result.success is True


def test_auth_failure_fails_fast_without_retry():
    FakeSMTP.behavior = "auth_fail"
    result = send(to_email="student@x.com", subject="s", body="b")
    assert result.success is False
    assert result.attempts == 1
    assert "authentication" in result.error.lower()


def test_recipients_refused_fails_fast_without_retry():
    FakeSMTP.behavior = "recipients_refused"
    result = send(to_email="bad@x.com", subject="s", body="b")
    assert result.success is False
    assert result.attempts == 1
    assert "refused" in result.error.lower()


def test_transient_disconnect_recovers_on_retry():
    FakeSMTP.behavior = "disconnect_then_ok"
    result = send(to_email="student@x.com", subject="s", body="b")
    assert result.success is True
    assert result.attempts == 2


def test_persistent_disconnect_exhausts_retries():
    FakeSMTP.behavior = "always_disconnect"
    result = send(to_email="student@x.com", subject="s", body="b")
    assert result.success is False
    assert result.attempts == email_service.MAX_ATTEMPTS
    assert str(email_service.MAX_ATTEMPTS) in result.error


@pytest.mark.parametrize(
    "kwargs",
    [
        {"to_email": "", "subject": "s", "body": "b"},
        {"to_email": "a@b.com", "subject": "", "body": "b"},
        {"to_email": "a@b.com", "subject": "s", "body": ""},
    ],
)
def test_blank_fields_raise_value_error(kwargs):
    with pytest.raises(ValueError):
        send(**kwargs)


def test_missing_from_email_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)
    with pytest.raises(email_service.EmailConfigurationError):
        send(to_email="a@b.com", subject="s", body="b")


def test_missing_app_password_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("SMTP_APP_PASSWORD", raising=False)
    with pytest.raises(email_service.EmailConfigurationError):
        send(to_email="a@b.com", subject="s", body="b")


def test_default_host_and_port_used_when_unset(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    captured = {}
    original_init = FakeSMTP.__init__

    def capturing_init(self, host, port, timeout=None):
        captured["host"], captured["port"] = host, port
        original_init(self, host, port, timeout)

    monkeypatch.setattr(FakeSMTP, "__init__", capturing_init)
    send(to_email="a@b.com", subject="s", body="b")
    assert captured == {
        "host": email_service.DEFAULT_SMTP_HOST,
        "port": email_service.DEFAULT_SMTP_PORT,
    }


def test_custom_host_and_port_from_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("SMTP_PORT", "2525")
    captured = {}
    original_init = FakeSMTP.__init__

    def capturing_init(self, host, port, timeout=None):
        captured["host"], captured["port"] = host, port
        original_init(self, host, port, timeout)

    monkeypatch.setattr(FakeSMTP, "__init__", capturing_init)
    send(to_email="a@b.com", subject="s", body="b")
    assert captured == {"host": "smtp.example.org", "port": 2525}
