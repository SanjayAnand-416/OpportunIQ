"""Gmail OAuth, token, and three-pass message-fetch service."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_CREDENTIALS_FILE = "credentials.json"
DEFAULT_TOKEN_FILE = "token.json"
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/gmail/callback"

THREE_PASS_QUERIES = [
    "subject:(interview OR shortlisted OR application OR offer OR submission OR test OR "
    "round OR accept OR congratulations OR selected OR rejected OR deadline OR schedule OR "
    "assessment) newer_than:60d",
    "from:(noreply@linkedin.com OR naukri.com OR unstop.com OR hackerearth.com OR "
    "internshala.com OR hr OR recruit OR talent OR careers) newer_than:60d",
    '("last date" OR "closes on" OR "submit by" OR "offer letter" OR "joining date") '
    "newer_than:60d",
]


def get_oauth_flow(state: str | None = None) -> Flow:
    """Create Person C's read-only Gmail OAuth flow."""
    return Flow.from_client_secrets_file(
        os.getenv("GOOGLE_CREDENTIALS_FILE", DEFAULT_CREDENTIALS_FILE),
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        state=state,
    )


def get_authorization_url(profile_id: str, state: str) -> str:
    """Return the consent URL expected by the active Gmail router."""
    del profile_id  # OAuth state is bound to the profile by the active router.
    flow = get_oauth_flow(state=state)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return authorization_url


def exchange_code_for_credentials(code: str, state: str | None = None) -> Credentials:
    """Exchange an OAuth callback code through Google's flow implementation."""
    flow = get_oauth_flow(state=state)
    flow.fetch_token(code=code)
    return flow.credentials


def save_credentials(credentials: Credentials, profile_id: str) -> None:
    """Persist the OAuth credentials using Person C's token-file model."""
    del profile_id
    token_path = _token_path()
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    token_path.chmod(0o600)


def load_credentials(profile_id: str | None = None) -> Credentials:
    """Load authorized-user credentials from the configured token file."""
    del profile_id
    return Credentials.from_authorized_user_file(str(_token_path()), SCOPES)


def credentials_exist(profile_id: str) -> bool:
    """Return whether the configured OAuth token exists for the active account."""
    del profile_id
    return _token_path().is_file()


def delete_credentials(profile_id: str) -> bool:
    """Delete the configured OAuth token, returning whether it existed."""
    del profile_id
    token_path = _token_path()
    if not token_path.is_file():
        return False
    token_path.unlink()
    return True


def get_gmail_service(
    token_path: str | None = None,
    profile_id: str | None = None,
) -> Any:
    """Build the Gmail API client from authorized-user credentials."""
    if token_path is None:
        credentials = load_credentials(profile_id)
    else:
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build("gmail", "v1", credentials=credentials)


def get_connected_email(profile_id: str) -> str | None:
    """Return the email address exposed by the connected Gmail profile."""
    service = get_gmail_service(profile_id=profile_id)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress")
    return str(email) if email else None


def fetch_emails_3pass(service: Any) -> list[dict[str, Any]]:
    """Run Person C's three Gmail searches and fetch each unique message once."""
    seen_ids: set[str] = set()
    emails: list[dict[str, Any]] = []
    for query in THREE_PASS_QUERIES:
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=50)
            .execute()
        )
        for message_reference in result.get("messages", []):
            message_id = message_reference["id"]
            if message_id in seen_ids:
                continue
            seen_ids.add(message_id)
            message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            emails.append(
                {
                    "id": message_id,
                    "body": extract_body(message),
                    "snippet": message.get("snippet", ""),
                }
            )
    return emails


def extract_body(message: dict[str, Any]) -> str:
    """Extract Person C's preferred plain-text body, falling back to snippet."""
    payload = message.get("payload", {})
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part["body"].get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return str(message.get("snippet", ""))


def _token_path() -> Path:
    """Resolve the configured Person C token-file location."""
    return Path(os.getenv("GOOGLE_TOKEN_FILE", DEFAULT_TOKEN_FILE))

