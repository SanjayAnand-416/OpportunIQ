import asyncio

from app.websocket_manager import ConnectionManager, emit_trace


class FakeWebSocket:
    def __init__(self, fail_send=False):
        self.accepted = False
        self.sent = []
        self.fail_send = fail_send

    async def accept(self):
        self.accepted = True

    async def send_json(self, event):
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent.append(event)

    async def close(self, code=1000):
        self.closed_code = code


def test_connect_stores_socket():
    manager = ConnectionManager()
    socket = FakeWebSocket()

    asyncio.run(manager.connect(socket, "session-1"))

    assert socket.accepted is True
    assert socket in manager.active_connections["session-1"]


def test_multiple_sockets_can_join_one_session():
    manager = ConnectionManager()
    first = FakeWebSocket()
    second = FakeWebSocket()

    asyncio.run(manager.connect(first, "session-1"))
    asyncio.run(manager.connect(second, "session-1"))

    assert manager.active_connections["session-1"] == {first, second}


def test_concurrent_connects_and_disconnect_are_consistent():
    manager = ConnectionManager()
    sockets = [FakeWebSocket() for _ in range(4)]

    async def scenario():
        await asyncio.gather(
            *(manager.connect(socket, "session-1") for socket in sockets)
        )
        await asyncio.gather(
            *(manager.send_event("session-1", {"sequence": index}) for index in range(4))
        )

    asyncio.run(scenario())
    manager.disconnect("session-1", sockets[0])

    assert manager.active_connections["session-1"] == set(sockets[1:])
    assert all(len(socket.sent) == 4 for socket in sockets)


def test_disconnect_removes_only_intended_socket():
    manager = ConnectionManager()
    first = FakeWebSocket()
    second = FakeWebSocket()
    asyncio.run(manager.connect(first, "session-1"))
    asyncio.run(manager.connect(second, "session-1"))

    manager.disconnect("session-1", first)

    assert manager.active_connections["session-1"] == {second}


def test_send_event_reaches_connected_socket():
    manager = ConnectionManager()
    socket = FakeWebSocket()
    asyncio.run(manager.connect(socket, "session-1"))

    sent = asyncio.run(manager.send_event("session-1", {"message": "hello"}))

    assert sent is True
    assert socket.sent == [{"message": "hello"}]


def test_failed_socket_is_removed():
    manager = ConnectionManager()
    socket = FakeWebSocket(fail_send=True)
    asyncio.run(manager.connect(socket, "session-1"))

    sent = asyncio.run(manager.send_event("session-1", {"message": "hello"}))

    assert sent is False
    assert "session-1" not in manager.active_connections


def test_unknown_session_returns_false():
    manager = ConnectionManager()

    assert asyncio.run(manager.send_event("missing", {"message": "hello"})) is False


def test_emit_trace_contains_timestamp_and_session(monkeypatch):
    manager = ConnectionManager()
    socket = FakeWebSocket()
    asyncio.run(manager.connect(socket, "session-1"))
    monkeypatch.setattr("app.websocket_manager.connection_manager", manager)

    asyncio.run(emit_trace("session-1", "ranker", "complete", "Done"))

    event = socket.sent[0]
    assert event["session_id"] == "session-1"
    assert event["agent"] == "ranker"
    assert event["status"] == "complete"
    assert event["message"] == "Done"
    assert event["timestamp"]


def test_buffered_events_replay_on_connect():
    manager = ConnectionManager()
    asyncio.run(manager.send_event("session-1", {"message": "already happened"}))
    socket = FakeWebSocket()

    asyncio.run(manager.connect(socket, "session-1"))

    assert socket.sent == [{"message": "already happened"}]


def test_event_and_session_buffers_are_bounded():
    manager = ConnectionManager(max_events_per_session=2, max_sessions=2)
    asyncio.run(manager.send_event("one", {"sequence": 1}))
    asyncio.run(manager.send_event("one", {"sequence": 2}))
    asyncio.run(manager.send_event("one", {"sequence": 3}))
    asyncio.run(manager.send_event("two", {"sequence": 1}))
    asyncio.run(manager.send_event("three", {"sequence": 1}))

    if "one" in manager.recent_events:
        assert list(manager.recent_events["one"]) == [
            {"sequence": 2},
            {"sequence": 3},
        ]
    assert len(manager.recent_events) == 2


def test_inactive_buffer_expires_after_ttl():
    manager = ConnectionManager(session_ttl_seconds=10)
    now = [0.0]
    manager._clock = lambda: now[0]
    asyncio.run(manager.send_event("session-1", {"message": "old"}))

    now[0] = 11.0

    assert manager.cleanup_expired_sessions() == 1
    assert "session-1" not in manager.recent_events


def test_connection_limit_rejects_extra_socket():
    manager = ConnectionManager(max_connections_per_session=1)
    first = FakeWebSocket()
    second = FakeWebSocket()
    asyncio.run(manager.connect(first, "session-1"))

    asyncio.run(manager.connect(second, "session-1"))

    assert manager.active_connections["session-1"] == {first}
    assert second.closed_code == 1013
