"""WebSocket connection management for discovery trace events."""

import logging
import time
from collections import deque
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track trace WebSocket connections by discovery session."""

    def __init__(
        self,
        max_events_per_session: int = 20,
        max_sessions: int = 200,
        session_ttl_seconds: float = 900,
        max_connections_per_session: int = 5,
    ) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}
        self.recent_events: dict[str, deque[dict[str, Any]]] = {}
        self.last_activity: dict[str, float] = {}
        self.max_events_per_session = max_events_per_session
        self.max_sessions = max_sessions
        self.session_ttl_seconds = session_ttl_seconds
        self.max_connections_per_session = max_connections_per_session
        self._lock = RLock()
        self._clock = time.monotonic

    def _cleanup_expired_locked(self) -> int:
        now = self._clock()
        expired = [
            session_id
            for session_id, last_seen in self.last_activity.items()
            if session_id not in self.active_connections
            and now - last_seen >= self.session_ttl_seconds
        ]
        for session_id in expired:
            self.recent_events.pop(session_id, None)
            self.last_activity.pop(session_id, None)
        return len(expired)

    def cleanup_expired_sessions(self) -> int:
        """Discard inactive replay buffers that have exceeded their TTL."""
        with self._lock:
            return self._cleanup_expired_locked()

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a WebSocket and replay recent events for its session."""
        clean_session_id = session_id.strip()
        if not clean_session_id:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        with self._lock:
            self._cleanup_expired_locked()
            connections = self.active_connections.setdefault(clean_session_id, set())
            if len(connections) >= self.max_connections_per_session:
                rejected = True
                replay_events: tuple[dict[str, Any], ...] = ()
            else:
                rejected = False
                connections.add(websocket)
                self.last_activity[clean_session_id] = self._clock()
                replay_events = tuple(self.recent_events.get(clean_session_id, ()))
        if rejected:
            await websocket.close(code=1013)
            return
        for event in replay_events:
            try:
                await websocket.send_json(event)
            except Exception as exc:
                logger.warning("Failed replaying trace event: %s", exc)
                self.disconnect(clean_session_id, websocket)
                break

    def disconnect(
        self,
        session_id: str,
        websocket: WebSocket | None = None,
    ) -> None:
        """Remove one socket or all sockets for a session."""
        clean_session_id = session_id.strip()
        with self._lock:
            connections = self.active_connections.get(clean_session_id)
            if not connections:
                return
            if websocket is None:
                self.active_connections.pop(clean_session_id, None)
            else:
                connections.discard(websocket)
                if not connections:
                    self.active_connections.pop(clean_session_id, None)
            self.last_activity[clean_session_id] = self._clock()

    def _buffer_event(self, session_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            self._cleanup_expired_locked()
            if session_id not in self.recent_events and len(self.recent_events) >= self.max_sessions:
                evictable = (
                    candidate
                    for candidate in self.recent_events
                    if candidate not in self.active_connections
                )
                oldest_session_id = next(evictable, next(iter(self.recent_events)))
                self.recent_events.pop(oldest_session_id, None)
                self.last_activity.pop(oldest_session_id, None)
            events = self.recent_events.setdefault(
                session_id,
                deque(maxlen=self.max_events_per_session),
            )
            events.append(event)
            self.last_activity[session_id] = self._clock()

    async def send_event(
        self,
        session_id: str,
        event: dict[str, Any],
    ) -> bool:
        """Send and buffer an event for one discovery session."""
        clean_session_id = session_id.strip()
        if not clean_session_id:
            return False
        self._buffer_event(clean_session_id, event)

        with self._lock:
            connections = set(self.active_connections.get(clean_session_id, set()))
        if not connections:
            return False

        sent = False
        for websocket in connections:
            try:
                await websocket.send_json(event)
                sent = True
            except Exception as exc:
                logger.warning("Failed sending trace event: %s", exc)
                self.disconnect(clean_session_id, websocket)
        return sent

    async def broadcast_event(self, event: dict[str, Any]) -> int:
        """Broadcast an event to all active trace sockets."""
        sent_count = 0
        with self._lock:
            session_ids = list(self.active_connections)
        for session_id in session_ids:
            if await self.send_event(session_id, event):
                sent_count += 1
        return sent_count


connection_manager = ConnectionManager()


async def emit_trace(
    session_id: str,
    agent: str,
    status: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Build and send a timestamped discovery trace event."""
    clean_session_id = session_id.strip()
    if not clean_session_id:
        return False
    event = {
        "session_id": clean_session_id,
        "agent": agent,
        "status": status,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "metadata": metadata or {},
    }
    return await connection_manager.send_event(clean_session_id, event)
