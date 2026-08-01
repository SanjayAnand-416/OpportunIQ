# OpportunIQ

OpportunIQ is an agentic opportunity-intelligence platform for students. It
combines personalized opportunity discovery, profile-aware ranking, application
tracking, deadline extraction, reminders, and skill-gap guidance in one system.

The project contains a FastAPI backend, a React/Vite frontend, SQLite
persistence, WebSocket agent traces, and optional integrations with ResumeAI,
JobSpy, Tavily, Groq, Gmail, Google OAuth, and SMTP.

## Highlights

- Resume upload with a safe manual-onboarding fallback
- Student profile creation, review, and editing
- Job, internship, and hackathon discovery
- Cross-source opportunity normalization, deduplication, and ranking
- Saved-opportunity tracker with application statuses
- Lightweight skill comparison and full Gap Advisor workflows
- Gmail OAuth and deadline extraction through a Guardian agent
- Deadline calendar with upcoming, overdue, and review states
- APScheduler-based reminders with dashboard and optional email delivery
- Real-time agent progress and notification events over WebSockets
- Deterministic offline demo data when external providers are unavailable

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 8, React Router, Axios, FullCalendar, Lucide |
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| Persistence | SQLite with `aiosqlite` |
| Agents and AI | LangGraph, Groq, Instructor, sentence-transformers |
| Discovery | JobSpy, Tavily |
| Scheduling | APScheduler |
| Integrations | Gmail API, Google OAuth, SMTP, ResumeAI |
| Realtime | FastAPI WebSockets |
| Testing | Pytest, FastAPI TestClient, ESLint, Vite production build |

## Architecture

```text
React / Vite frontend
        |
        | HTTP + WebSocket
        v
FastAPI routers
        |
        +-- repositories --> SQLite
        |
        +-- services ------> JobSpy / Tavily / Groq / ResumeAI / Gmail / SMTP
        |
        +-- agents --------> Guardian / Gap Analysis
        |
        +-- scheduler -----> dashboard notifications + optional email
```

The active Python package is `opportuniq-backend/app`. Root-level backend
modules outside `app/` are retained for compatibility and should not be used as
the Uvicorn import target.

## Repository Layout

```text
OpportunIQ/
├── opportuniq-backend/
│   ├── app/
│   │   ├── agents/          # Guardian and Gap Analysis agents
│   │   ├── repositories/    # Async SQLite persistence boundaries
│   │   ├── routers/         # FastAPI endpoints
│   │   ├── services/        # External providers and scheduling
│   │   ├── database.py
│   │   ├── main.py
│   │   └── models.py
│   ├── scripts/             # Demo seed and validation tools
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── opportuniq-frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── utils/
│   └── package.json
├── docs/
└── README.md
```

## Prerequisites

- Git
- Python 3.11 or newer
- Node.js 22 (the frontend includes an `.nvmrc`)
- npm

Optional live integrations require their own API keys or OAuth credentials. You
can run the core application and offline demo without them.

## Clone the Repository

```bash
git clone https://github.com/SanjayAnand-416/OpportunIQ.git
cd OpportunIQ
```

## Quick Start

Run the backend and frontend in separate terminals.

### 1. Configure and Run the Backend

macOS/Linux:

```bash
cd opportuniq-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
cd opportuniq-backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The backend starts at `http://localhost:8000`.

Verify it:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"opportuniq-backend"}
```

Useful backend URLs:

- Health: <http://localhost:8000/health>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>

### 2. Configure and Run the Frontend

In a second terminal:

```bash
cd opportuniq-frontend
nvm use
npm ci
npm run dev
```

Without `nvm`, install Node.js 22 and run `npm ci && npm run dev` directly.
The frontend starts at <http://localhost:5173>.

For a non-default backend or WebSocket host, create
`opportuniq-frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## Environment Configuration

Copy `opportuniq-backend/.env.example` to `.env`. Empty optional values keep
their integrations unavailable without preventing application startup.

### Core Settings

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `opportuniq.db` | SQLite database path |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin |
| `APP_TIMEZONE` | `Asia/Kolkata` | Calendar and same-day reminder timezone |
| `ENABLE_SCHEDULER` | `true` | Start APScheduler with FastAPI |
| `DEMO_MODE` | `false` | Marks deterministic demo operation |
| `EXTERNAL_HTTP_TIMEOUT_SECONDS` | `30` | External HTTP timeout |
| `AGENT_TIMEOUT_SECONDS` | `60` | Agent execution timeout |
| `JOBSPY_TIMEOUT_SECONDS` | `30` | JobSpy search timeout |
| `SMTP_TIMEOUT_SECONDS` | `20` | SMTP timeout |

### Optional Integrations

| Variable | Integration |
|---|---|
| `RESUMEAI_API_URL` | Resume extraction endpoint |
| `RESUMEAI_API_KEY` | ResumeAI bearer token |
| `TAVILY_API_KEY` | Web and hackathon discovery |
| `GROQ_API_KEY` | Extraction, ranking support, and reminder generation |
| `SMTP_FROM_EMAIL` | Reminder sender address |
| `SMTP_APP_PASSWORD` | SMTP application password |
| `GOOGLE_CREDENTIALS_FILE` | Google OAuth client credentials JSON |
| `GOOGLE_TOKEN_FILE` | Legacy/default OAuth token filename |
| `GOOGLE_TOKEN_DIR` | Per-profile OAuth token directory |
| `GOOGLE_REDIRECT_URI` | Gmail OAuth callback URL |
| `OPPORTUNIQ_ENV_FILE` | Optional alternate dotenv file |

Never commit `.env`, API keys, `credentials.json`, OAuth tokens, resumes, or
SQLite databases.

## Gmail OAuth Setup

1. Create a project in Google Cloud Console.
2. Enable the Gmail API.
3. Configure the OAuth consent screen.
4. Create OAuth desktop/web credentials as required by your environment.
5. Add this local redirect URI:

   ```text
   http://localhost:8000/api/gmail/callback
   ```

6. Store the credentials file outside version control and configure
   `GOOGLE_CREDENTIALS_FILE`.

The integration requests read-only Gmail access. Generated tokens must remain
private.

## Offline Demo

Use the deterministic seed when external providers are not configured:

```bash
cd opportuniq-backend
source .venv/bin/activate
export DATABASE_PATH=opportuniq-demo.db
export DEMO_MODE=true
python scripts/seed_demo.py --reset --print-summary
uvicorn app.main:app --reload
```

PowerShell equivalents:

```powershell
$env:DATABASE_PATH = "opportuniq-demo.db"
$env:DEMO_MODE = "true"
python scripts/seed_demo.py --reset --print-summary
uvicorn app.main:app --reload
```

The seed performs no external calls. It creates a demo profile, opportunities,
saved items, deadline states, notifications, settings, and persisted Gap Advisor
results. See [the demo runbook](docs/DEMO_RUNBOOK.md) for the complete demo flow,
reset procedure, and fallback guidance.

## API Overview

| Area | Routes |
|---|---|
| Profiles | `/api/profile/manual`, `/api/profile/upload`, `/api/profile/{profile_id}` |
| Discovery | `/api/opportunities/search`, `/api/opportunities` |
| Saved tracker | `/api/saved` and `/api/saved/{id}` |
| Skill gap | `/api/opportunities/{id}/skill-gap` |
| Gap Advisor | `/api/gap-analysis/run` and `/api/gap-analysis/*` |
| Gmail | `/api/gmail/connect`, `/callback`, `/status`, `/scan`, `/disconnect` |
| Deadlines | `/api/deadlines` and calendar/upcoming/today/overdue views |
| Notifications | `/api/notifications`, read actions, test reminder, scheduler status |
| Settings | `/api/settings/notifications` |
| Realtime | `/ws/agent-trace?session_id=<id>` |

Swagger at `/docs` is the authoritative request/response reference.

## Development and Validation

Backend:

```bash
cd opportuniq-backend
source .venv/bin/activate
python -m compileall app scripts
pytest -q
python scripts/validate_openapi.py
python scripts/validate_frontend_contracts.py
```

Frontend:

```bash
cd opportuniq-frontend
npm ci
npm run lint
npm run build
```

The frontend currently has no configured unit-test or typecheck script.

### Optional Live Smoke Checks

The smoke script makes no external calls by default:

```bash
cd opportuniq-backend
python scripts/smoke_live_integrations.py
```

Enable only integrations you intend to call:

```bash
LIVE_SMOKE_GROQ=true LIVE_SMOKE_TAVILY=true \
  python scripts/smoke_live_integrations.py
```

SMTP requires an explicit recipient:

```bash
LIVE_SMOKE_SMTP=true python scripts/smoke_live_integrations.py \
  --send-email recipient@example.com
```

Do not describe an integration as live until its opt-in smoke check and its
user-facing flow have both succeeded.

## Production-Like Local Run

APScheduler is process-local, so use exactly one backend worker:

```bash
cd opportuniq-backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Build and preview the frontend:

```bash
cd opportuniq-frontend
npm run build
npm run preview
```

For deployment, provide environment variables through the hosting platform,
serve the frontend build through a static host, configure HTTPS/WSS URLs, and
keep scheduler execution single-process unless it is moved to a dedicated job
runner.

## Troubleshooting

### `ModuleNotFoundError: app`

Run Uvicorn from `opportuniq-backend`, not the repository root:

```bash
cd opportuniq-backend
uvicorn app.main:app --reload
```

### Frontend Cannot Reach the API

- Confirm the backend health endpoint returns 200.
- Set `VITE_API_BASE_URL` to the backend origin.
- Make `FRONTEND_URL` exactly match the Vite origin.
- Restart Vite after changing frontend environment variables.

### Resume Upload Returns 503

ResumeAI is optional. Configure a reachable `RESUMEAI_API_URL`, or continue
through manual profile setup. The application must not fabricate extraction
success.

### Gmail Connect or Scan Fails

Confirm the Gmail API is enabled, the redirect URI matches exactly, credentials
exist at `GOOGLE_CREDENTIALS_FILE`, and generated token paths are writable.

### Empty Opportunity Results

Check provider credentials and network access. For a deterministic presentation,
use the offline demo seed rather than presenting fallback ordering as live
semantic ranking.

### Scheduler Does Not Send Reminders

Confirm `ENABLE_SCHEDULER=true`, the deadline is active and in the future, and
only one Uvicorn worker is running. Dashboard notifications remain the primary
fallback when Groq or SMTP is unavailable.

### Sentence-Transformer Model Is Unavailable

The lightweight skill-gap service loads its model lazily. Ensure the model is
already available in the runtime or use seeded Gap Advisor data for offline
demonstrations.

## Security and Data Handling

- Do not commit secrets, OAuth credentials/tokens, databases, or resumes.
- Resume files are validated, bounded to 5 MB, forwarded in memory, and are not
  stored by the profile service.
- Gmail access is read-only.
- External failures return controlled responses without provider stack traces.
- WebSocket session IDs correlate events; they are not authentication tokens.
- Use disposable databases and accounts for demos.

## Additional Documentation

- [Build plan](docs/BUILD_PLAN.md)
- [Work plan](docs/WORK_PLAN.md)
- [Demo runbook](docs/DEMO_RUNBOOK.md)
- [Integration contracts](opportuniq-backend/docs/INTEGRATION_CONTRACTS.md)
- [Final integration report](opportuniq-backend/docs/FINAL_INTEGRATION_REPORT.md)
- [Backend guide](opportuniq-backend/README.md)
- [Frontend guide](opportuniq-frontend/README.md)

## Contributing

1. Create a focused branch from the latest `main`.
2. Keep active backend imports under `opportuniq-backend/app`.
3. Never commit secrets or generated data.
4. Add or update tests for behavior changes.
5. Run backend tests plus frontend lint/build before opening a pull request.
6. Keep commits scoped and use clear Conventional Commit messages.
