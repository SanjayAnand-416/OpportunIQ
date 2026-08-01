"""Gmail OAuth, token, and three-pass message-fetch service."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

import google_auth_httplib2
import httplib2
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import EXTERNAL_HTTP_TIMEOUT_SECONDS


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_CREDENTIALS_FILE = "credentials.json"
DEFAULT_TOKEN_FILE = "token.json"
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/gmail/callback"
GOOGLE_REVOCATION_URL = "https://oauth2.googleapis.com/revoke"

logger = logging.getLogger(__name__)

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
    flow.fetch_token(code=code, timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS)
    return flow.credentials


def save_credentials(credentials: Credentials, profile_id: str) -> None:
    """Persist credentials in the token file owned by exactly one profile."""
    token_path = _token_path(profile_id)
    token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    token_path.chmod(0o600)


def load_credentials(profile_id: str) -> Credentials:
    """Load authorized-user credentials for one profile only."""
    return Credentials.from_authorized_user_file(str(_token_path(profile_id)), SCOPES)


def credentials_exist(profile_id: str) -> bool:
    """Return whether this profile has its own OAuth token."""
    return _token_path(profile_id).is_file()


def delete_credentials(profile_id: str, revoke: bool = True) -> bool:
    """Revoke and delete only the token owned by ``profile_id``."""
    token_path = _token_path(profile_id)
    if not token_path.is_file():
        return False
    if revoke:
        try:
            revoke_credentials(profile_id)
        except (OSError, ValueError, HTTPError, URLError) as exc:
            # Local disconnect must still complete when Google is unreachable or
            # has already invalidated the credential.
            logger.warning(
                "Remote Gmail token revocation failed safely: %s",
                type(exc).__name__,
            )
    token_path.unlink()
    return True


def revoke_credentials(profile_id: str) -> bool:
    """Ask Google to revoke this profile's refresh/access token, if available."""
    credentials = load_credentials(profile_id)
    token = credentials.refresh_token or credentials.token
    if not token:
        return False
    request = UrlRequest(
        GOOGLE_REVOCATION_URL,
        data=urlencode({"token": token}).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS) as response:
        return 200 <= response.status < 300


def get_gmail_service(
    token_path: str | None = None,
    profile_id: str | None = None,
) -> Any:
    """Build the Gmail API client from authorized-user credentials."""
    if token_path is None:
        if profile_id is None:
            raise ValueError("profile_id is required for profile-isolated Gmail credentials")
        credentials = load_credentials(profile_id)
    else:
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
    authorized_http = google_auth_httplib2.AuthorizedHttp(
        credentials,
        http=httplib2.Http(timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS),
    )
    return build("gmail", "v1", http=authorized_http, cache_discovery=False)


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


def _token_path(profile_id: str) -> Path:
    """Resolve a traversal-safe, stable token path unique to one profile."""
    clean_profile_id = profile_id.strip()
    if not clean_profile_id:
        raise ValueError("profile_id is required for Gmail credentials")

    configured_directory = os.getenv("GOOGLE_TOKEN_DIR", "").strip()
    if configured_directory:
        token_directory = Path(configured_directory)
    else:
        legacy_path = Path(os.getenv("GOOGLE_TOKEN_FILE", DEFAULT_TOKEN_FILE))
        token_directory = legacy_path.parent / f"{legacy_path.stem}s"

    profile_key = hashlib.sha256(clean_profile_id.encode("utf-8")).hexdigest()
    return token_directory / f"{profile_key}.json"
