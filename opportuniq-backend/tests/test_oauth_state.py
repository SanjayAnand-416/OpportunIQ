from datetime import UTC, datetime, timedelta

from app.oauth_state import OAuthState, OAuthStateManager


def test_create_state_returns_non_empty_secure_state():
    manager = OAuthStateManager()

    state = manager.create_state("profile-1")

    assert isinstance(state, str)
    assert len(state) >= 32


def test_state_maps_to_correct_public_profile_id():
    manager = OAuthStateManager()
    state = manager.create_state("profile-1")

    assert manager.consume_state(state) == "profile-1"


def test_consume_state_is_one_time_use():
    manager = OAuthStateManager()
    state = manager.create_state("profile-1")

    assert manager.consume_state(state) == "profile-1"
    assert manager.consume_state(state) is None


def test_unknown_state_returns_none():
    assert OAuthStateManager().consume_state("missing") is None


def test_expired_state_returns_none():
    manager = OAuthStateManager()
    manager._states["expired"] = OAuthState(
        profile_id="profile-1",
        created_at=datetime.now(UTC) - timedelta(minutes=11),
    )

    assert manager.consume_state("expired") is None


def test_cleanup_removes_expired_states():
    manager = OAuthStateManager()
    manager._states["expired"] = OAuthState(
        profile_id="profile-1",
        created_at=datetime.now(UTC) - timedelta(minutes=11),
    )
    manager._states["fresh"] = OAuthState(
        profile_id="profile-2",
        created_at=datetime.now(UTC),
    )

    assert manager.cleanup_expired() == 1
    assert "expired" not in manager._states
    assert "fresh" in manager._states


def test_multiple_profile_states_remain_independent():
    manager = OAuthStateManager()
    first = manager.create_state("profile-1")
    second = manager.create_state("profile-2")

    assert manager.consume_state(second) == "profile-2"
    assert manager.consume_state(first) == "profile-1"


def test_state_repr_does_not_expose_state_value():
    state = OAuthState(profile_id="profile-1", created_at=datetime.now(UTC))

    assert "secret-state" not in repr(state)
