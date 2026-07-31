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
