"""WebSocket connection management for discovery trace events."""

import logging
from collections import deque
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track trace WebSocket connections by discovery session."""

    def __init__(self, max_events_per_session: int = 20, max_sessions: int = 200) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}
        self.recent_events: dict[str, deque[dict[str, Any]]] = {}
        self.max_events_per_session = max_events_per_session
        self.max_sessions = max_sessions

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a WebSocket and replay recent events for its session."""
        clean_session_id = session_id.strip()
        if not clean_session_id:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        self.active_connections.setdefault(clean_session_id, set()).add(websocket)
        for event in self.recent_events.get(clean_session_id, ()):
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
        connections = self.active_connections.get(clean_session_id)
        if not connections:
            return
        if websocket is None:
            self.active_connections.pop(clean_session_id, None)
            return
        connections.discard(websocket)
        if not connections:
            self.active_connections.pop(clean_session_id, None)

    def _buffer_event(self, session_id: str, event: dict[str, Any]) -> None:
        if session_id not in self.recent_events and len(self.recent_events) >= self.max_sessions:
            oldest_session_id = next(iter(self.recent_events))
            self.recent_events.pop(oldest_session_id, None)
        events = self.recent_events.setdefault(
            session_id,
            deque(maxlen=self.max_events_per_session),
        )
        events.append(event)

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
        for session_id in list(self.active_connections):
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
