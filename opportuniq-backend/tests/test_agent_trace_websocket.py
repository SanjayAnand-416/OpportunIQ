import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.websocket_manager import connection_manager, emit_trace


def test_agent_trace_websocket_ping_and_event_replay():
    session_id = "ws-session"
    connection_manager.active_connections.clear()
    connection_manager.recent_events.clear()
    asyncio.run(emit_trace(session_id, "profile", "running", "Loading"))

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/agent-trace?session_id={session_id}") as websocket:
            replayed = websocket.receive_json()
            assert replayed["session_id"] == session_id
            assert replayed["agent"] == "profile"
            assert replayed["status"] == "running"
            assert replayed["message"] == "Loading"
            assert replayed["timestamp"]

            websocket.send_text("ping")
            assert websocket.receive_text() == "pong"

    assert session_id not in connection_manager.active_connections
