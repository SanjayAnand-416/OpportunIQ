# OpportunIQ Backend

FastAPI backend foundation for OpportunIQ, including application startup, SQLite initialization, and shared Pydantic schemas for later agent and API work.

## Requirements

Use Python 3.11 or newer.

## Environment Setup

Create a virtual environment and install dependencies:

```bash
cd opportuniq-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in local values. Do not commit `.env`, OAuth credentials, tokens, or database files.

## Run

```bash
uvicorn app.main:app --reload
```

Health check:

```text
http://localhost:8000/health
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

## Deadline Registry

Deadline API routes are available under `/api/deadlines`:

```text
POST /api/deadlines
GET /api/deadlines?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/deadlines/calendar?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/deadlines/upcoming?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/deadlines/today?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/deadlines/overdue?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/deadlines/needs-review?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/deadlines/{deadline_id}
PUT /api/deadlines/{deadline_id}
DELETE /api/deadlines/{deadline_id}
```

Deadline timestamps are normalized to UTC before storage. Naive datetimes are treated as UTC. Active dated deadlines receive reminders 7 days, 3 days, and 1 day before the deadline, plus a same-day reminder at 09:00 in `APP_TIMEZONE`. Past reminder offsets are skipped.

## Reminder Scheduler

Set the local calendar timezone used for same-day reminders:

```text
APP_TIMEZONE=Asia/Kolkata
```

APScheduler runs in UTC and starts with the FastAPI lifespan. Its jobs are process-local and are recreated from active future records in `deadline_registry` after every restart. Completing, cancelling, deleting, or changing a deadline cancels or replaces its jobs.

Reminder execution always creates an idempotent dashboard notification first and then publishes a `notifier` event on the existing agent-trace WebSocket using the public `profile_id` as its session key. Compatible Groq and email services are used when available. Missing or failed optional integrations fall back to deterministic reminder text and do not prevent dashboard delivery.

Useful endpoints:

```text
GET /api/notifications?profile_id=<PUBLIC_PROFILE_UUID>
PATCH /api/notifications/{notification_id}/read
PATCH /api/notifications/read-all?profile_id=<PUBLIC_PROFILE_UUID>
POST /api/notifications/test
GET /api/notifications/scheduler/status
```

`POST /api/notifications/test` accepts `{"deadline_id": "<DEADLINE_UUID>"}` and executes immediately without waiting for APScheduler. Repeated test reminders create separate dashboard notifications.

## Gmail OAuth

Gmail integration uses read-only access:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Create OAuth credentials in Google Cloud, enable the Gmail API, and set this redirect URI:

```text
http://localhost:8000/api/gmail/callback
```

Required local configuration:

```text
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
FRONTEND_URL=http://localhost:5173
```

Local demo sequence:

```text
GET /api/gmail/connect?profile_id=<PUBLIC_PROFILE_UUID>
GET /api/gmail/status?profile_id=<PUBLIC_PROFILE_UUID>
POST /api/gmail/scan
DELETE /api/gmail/disconnect?profile_id=<PUBLIC_PROFILE_UUID>
```

`credentials.json`, OAuth tokens, `.env`, and database files must never be committed. If `app/services/gmail_service.py` or `app/agents/guardian_agent.py` is not available yet, Gmail routes return safe guarded responses such as HTTP 503 instead of breaking backend startup.
