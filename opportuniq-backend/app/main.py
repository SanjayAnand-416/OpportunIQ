import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers.deadlines import router as deadlines_router
from app.routers.gmail import router as gmail_router
from app.routers.notifications import router as notifications_router
from app.routers.opportunities import router as opportunities_router
from app.routers.profile import router as profile_router
from app.routers.saved import router as saved_router
from app.services.scheduler_service import (
    restore_scheduled_reminders,
    shutdown_scheduler,
    start_scheduler,
)
from app.websocket_manager import connection_manager


load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing OpportunIQ database")
    await init_db()
    start_scheduler()
    try:
        await restore_scheduled_reminders()
    except Exception:
        logger.exception("Reminder restoration failed; startup will continue")
    try:
        yield
    finally:
        shutdown_scheduler(wait=False)


app = FastAPI(
    title="OpportunIQ API",
    version="0.1.0",
    lifespan=lifespan,
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_router)
app.include_router(opportunities_router)
app.include_router(gmail_router)
app.include_router(deadlines_router)
app.include_router(notifications_router)
app.include_router(saved_router)


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "service": "opportuniq-backend",
    }


@app.websocket("/ws/agent-trace")
async def agent_trace_websocket(websocket: WebSocket, session_id: str) -> None:
    """Stream discovery trace events for one session."""
    clean_session_id = session_id.strip()
    if not clean_session_id:
        await websocket.close(code=1008)
        return

    await connection_manager.connect(websocket, clean_session_id)
    try:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Agent trace WebSocket closed unexpectedly: %s", exc)
    finally:
        connection_manager.disconnect(clean_session_id, websocket)
