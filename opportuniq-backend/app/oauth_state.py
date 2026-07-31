"""In-memory OAuth state management for Gmail authorization.

For hackathon-local development this keeps state in process memory. A
multi-instance deployment should replace this with shared storage.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class OAuthState:
    profile_id: str
    created_at: datetime


class OAuthStateManager:
    """Create, validate, and consume short-lived OAuth state values."""

    def __init__(self, ttl_minutes: int = 10, max_states: int = 500) -> None:
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_states = max_states
        self._states: dict[str, OAuthState] = {}

    def create_state(self, profile_id: str) -> str:
        """Create a secure state string mapped to a public profile ID."""
        self.cleanup_expired()
        if len(self._states) >= self.max_states:
            oldest_state = min(self._states, key=lambda key: self._states[key].created_at)
            self._states.pop(oldest_state, None)
        state = secrets.token_urlsafe(32)
        self._states[state] = OAuthState(
            profile_id=profile_id,
            created_at=datetime.now(UTC),
        )
        return state

    def consume_state(self, state: str) -> str | None:
        """Consume one OAuth state value and return its profile ID if valid."""
        record = self._states.pop(state, None)
        if record is None:
            return None
        if datetime.now(UTC) - record.created_at > self.ttl:
            return None
        return record.profile_id

    def cleanup_expired(self) -> int:
        """Remove expired OAuth states and return how many were removed."""
        now = datetime.now(UTC)
        expired_states = [
            state
            for state, record in self._states.items()
            if now - record.created_at > self.ttl
        ]
        for state in expired_states:
            self._states.pop(state, None)
        return len(expired_states)


oauth_state_manager = OAuthStateManager()
