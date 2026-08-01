"""Credential-isolation and network-boundary tests for the Gmail adapter."""

from types import SimpleNamespace

from google.oauth2.credentials import Credentials

from app.services import gmail_service


def _credentials(access_token: str, refresh_token: str) -> Credentials:
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="test-client",
        client_secret="test-secret",
        scopes=gmail_service.SCOPES,
    )


def test_tokens_are_isolated_by_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_DIR", str(tmp_path / "tokens"))
    monkeypatch.setattr(gmail_service, "revoke_credentials", lambda _profile_id: True)

    gmail_service.save_credentials(_credentials("access-a", "refresh-a"), "profile-a")
    gmail_service.save_credentials(_credentials("access-b", "refresh-b"), "profile-b")

    assert gmail_service.load_credentials("profile-a").refresh_token == "refresh-a"
    assert gmail_service.load_credentials("profile-b").refresh_token == "refresh-b"
    assert gmail_service.delete_credentials("profile-a") is True
    assert gmail_service.credentials_exist("profile-a") is False
    assert gmail_service.credentials_exist("profile-b") is True
    assert gmail_service.load_credentials("profile-b").refresh_token == "refresh-b"


def test_profile_identifier_cannot_escape_token_directory(tmp_path, monkeypatch):
    token_directory = tmp_path / "tokens"
    monkeypatch.setenv("GOOGLE_TOKEN_DIR", str(token_directory))

    gmail_service.save_credentials(
        _credentials("access", "refresh"),
        "../../another-profile",
    )

    token_files = list(token_directory.glob("*.json"))
    assert len(token_files) == 1
    assert token_files[0].parent == token_directory


def test_oauth_exchange_uses_external_timeout(monkeypatch):
    calls = {}

    class FakeFlow:
        credentials = object()

        def fetch_token(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setattr(gmail_service, "get_oauth_flow", lambda state=None: FakeFlow())
    monkeypatch.setattr(gmail_service, "EXTERNAL_HTTP_TIMEOUT_SECONDS", 12.5)

    credentials = gmail_service.exchange_code_for_credentials("code", "state")

    assert credentials is FakeFlow.credentials
    assert calls == {"code": "code", "timeout": 12.5}


def test_oauth_flow_uses_configured_redirect_uri(monkeypatch):
    captured = {}

    def fake_flow_factory(credentials_file, **kwargs):
        captured["credentials_file"] = credentials_file
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setenv("GOOGLE_CREDENTIALS_FILE", "/config/google.json")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "https://api.example.test/api/gmail/callback",
    )
    monkeypatch.setattr(
        gmail_service.Flow,
        "from_client_secrets_file",
        fake_flow_factory,
    )

    gmail_service.get_oauth_flow(state="profile-bound-state")

    assert captured["credentials_file"] == "/config/google.json"
    assert captured["redirect_uri"] == "https://api.example.test/api/gmail/callback"
    assert captured["state"] == "profile-bound-state"


def test_gmail_client_transport_uses_external_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_DIR", str(tmp_path / "tokens"))
    monkeypatch.setattr(gmail_service, "EXTERNAL_HTTP_TIMEOUT_SECONDS", 7.5)
    gmail_service.save_credentials(_credentials("access", "refresh"), "profile-a")
    captured = {}
    transport = object()
    authorized_transport = object()

    def fake_http(*, timeout):
        captured["timeout"] = timeout
        return transport

    def fake_authorized_http(credentials, *, http):
        captured["credentials"] = credentials
        captured["transport"] = http
        return authorized_transport

    def fake_build(api, version, **kwargs):
        captured["build"] = (api, version, kwargs)
        return "gmail-client"

    monkeypatch.setattr(gmail_service.httplib2, "Http", fake_http)
    monkeypatch.setattr(
        gmail_service.google_auth_httplib2,
        "AuthorizedHttp",
        fake_authorized_http,
    )
    monkeypatch.setattr(gmail_service, "build", fake_build)

    client = gmail_service.get_gmail_service(profile_id="profile-a")

    assert client == "gmail-client"
    assert captured["timeout"] == 7.5
    assert captured["transport"] is transport
    assert captured["build"] == (
        "gmail",
        "v1",
        {"http": authorized_transport, "cache_discovery": False},
    )


def test_remote_revoke_uses_refresh_token_and_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_DIR", str(tmp_path / "tokens"))
    monkeypatch.setattr(gmail_service, "EXTERNAL_HTTP_TIMEOUT_SECONDS", 9.0)
    gmail_service.save_credentials(_credentials("access", "refresh"), "profile-a")
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(gmail_service, "urlopen", fake_urlopen)

    assert gmail_service.revoke_credentials("profile-a") is True
    assert captured == {
        "url": gmail_service.GOOGLE_REVOCATION_URL,
        "body": b"token=refresh",
        "timeout": 9.0,
    }


def test_local_disconnect_completes_when_remote_revoke_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_DIR", str(tmp_path / "tokens"))
    gmail_service.save_credentials(_credentials("access", "refresh"), "profile-a")

    def fail_revoke(_profile_id):
        raise OSError("network unavailable")

    monkeypatch.setattr(gmail_service, "revoke_credentials", fail_revoke)

    assert gmail_service.delete_credentials("profile-a") is True
    assert gmail_service.credentials_exist("profile-a") is False
