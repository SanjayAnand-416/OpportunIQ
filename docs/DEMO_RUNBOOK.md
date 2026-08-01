# OpportunIQ Demo Runbook

## Prerequisites

- Python 3.11 or newer and Node.js compatible with Vite 8.
- One terminal for FastAPI and one for Vite.
- External credentials only for integrations intentionally demonstrated live.
- Run a single Uvicorn worker while process-local APScheduler is enabled.

## Environment Variables

Copy `opportuniq-backend/.env.example` to `opportuniq-backend/.env` and set
only locally required values. Never commit `.env`, Gmail credentials/tokens,
SMTP credentials, or SQLite files.

Core variables are `DATABASE_PATH`, `FRONTEND_URL`, `APP_TIMEZONE`,
`ENABLE_SCHEDULER`, and `DEMO_MODE`. Optional integrations use
`RESUMEAI_API_URL`, `RESUMEAI_API_KEY`, `TAVILY_API_KEY`, `GROQ_API_KEY`,
`GOOGLE_CREDENTIALS_FILE`, `GOOGLE_TOKEN_FILE`, `SMTP_FROM_EMAIL`, and
`SMTP_APP_PASSWORD`. Frontend overrides are `VITE_API_BASE_URL` and
`VITE_WS_BASE_URL`.

## Backend Setup

```bash
cd opportuniq-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health and API documentation:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

## Frontend Setup

```bash
cd opportuniq-frontend
npm ci
npm run dev
```

The frontend defaults to `http://localhost:5173` and the backend to
`http://localhost:8000`.

## Demo Database Setup

Use a dedicated local database, not a development or teammate database:

```bash
cd opportuniq-backend
source .venv/bin/activate
export DATABASE_PATH=opportuniq-demo.db
python scripts/seed_demo.py --reset --print-summary
```

The fixed demo profile ID is
`10000000-0000-4000-8000-000000000001`. The seed command safely replaces only
records owned by that profile and creates 10 opportunities, 3 saved tracker
items, 4 deadline states, dashboard notifications, settings, and 2 persisted
Gap Analyses. It performs no external calls.

To create process-local reminder jobs during seeding:

```bash
python scripts/seed_demo.py --reset --with-scheduler --print-summary
```

## Full Live Mode

Use `DEMO_MODE=false`, `ENABLE_SCHEDULER=true`, and valid credentials. Run the
optional smoke tool before presenting any integration as live:

```bash
LIVE_SMOKE_GROQ=true LIVE_SMOKE_TAVILY=true \
  python scripts/smoke_live_integrations.py
```

SMTP delivery additionally requires explicit confirmation:

```bash
LIVE_SMOKE_SMTP=true python scripts/smoke_live_integrations.py \
  --send-email recipient@example.com
```

At the time of this runbook, active-package ResumeAI, Tavily, Gmail, Guardian,
discovery extraction/ranking, and full Gap Agent implementations remain guarded
or teammate-blocked. Do not label this mode live until each enabled check passes.

## Mixed Mode

Use live integrations that have been verified and retain controlled errors for
the rest. Recommended demo choices:

- ResumeAI unavailable: create the profile manually.
- Tavily/Groq/ranker unavailable: show seeded opportunities; do not describe
  their ordering as live semantic ranking.
- Gmail/Guardian unavailable: show the seeded Gmail-labelled deadline and state
  clearly that it is demo data.
- SMTP unavailable: fire a test reminder and show dashboard delivery.
- Gap Agent unavailable: show persisted seeded role/opportunity analyses.

## Offline Demo Mode

```bash
cd opportuniq-backend
source .venv/bin/activate
export DATABASE_PATH=opportuniq-demo.db
export DEMO_MODE=true
export ENABLE_SCHEDULER=true
python scripts/seed_demo.py --reset --print-summary
uvicorn app.main:app --reload
```

Seeded data is visibly described as demo content. `DEMO_MODE` never bypasses
validation and never converts an unavailable external service into fake success.

## Six-Minute Demo Script

1. Open the frontend and create a profile through manual onboarding.
2. Open Dashboard and show the seeded or mock-verified ranked opportunities.
3. Start discovery only when providers are verified; show agent trace events.
4. Open an opportunity, save it, and update its application status.
5. Show the lightweight skill gap only if its local model is already available.
6. Open the persisted Gap Analysis and label it seeded when the agent is absent.
7. Show Gmail status; use the documented fallback if OAuth/Guardian is absent.
8. Open Deadlines and point out future, due-soon, overdue, and review states.
9. Fire `POST /api/notifications/test` for a seeded deadline.
10. Show the dashboard notification and scheduler status.

## External Integration Checks

```bash
python scripts/smoke_live_integrations.py
```

Default output is `SKIP` and makes no live call. Enable services individually
with `LIVE_SMOKE_<SERVICE>=true`. The script prints only PASS/SKIP/FAIL and
exception class names; it never prints secrets, resume content, or email bodies.

## Expected API Responses

- `GET /health`: `{"status":"ok","service":"opportuniq-backend"}`.
- `GET /api/opportunities?profile_id=<DEMO_ID>`: count 10 after seed.
- `GET /api/saved?profile_id=<DEMO_ID>`: count 3 after seed.
- `GET /api/notifications?profile_id=<DEMO_ID>`: count 4 before test reminders.
- `GET /api/settings/notifications?profile_id=<DEMO_ID>`: four boolean offsets.
- `GET /api/gap-analysis/<DEMO_ID>`: persisted `profile_vs_role` result.
- Missing optional integrations: controlled 503/504/502 response, never a stack
  trace or fabricated live result.

## Troubleshooting

- CORS error: make `FRONTEND_URL` exactly match the Vite origin.
- Wrong backend target: set `VITE_API_BASE_URL` and `VITE_WS_BASE_URL`, then
  restart Vite.
- `npm ci` failure: do not upgrade packages; verify `package.json` and
  `package-lock.json` are from the same commit.
- Empty dashboard: verify the browser stores the seeded public profile ID or
  complete manual onboarding.
- Scheduler reports stopped: check `ENABLE_SCHEDULER=true` and use one worker.
- Missing model: use seeded data; do not download models during the demo.
- Integration 503: use the matching mixed/offline fallback above.

## Reset Procedure

```bash
cd opportuniq-backend
source .venv/bin/activate
export DATABASE_PATH=opportuniq-demo.db
python scripts/seed_demo.py --reset --print-summary
```

This replaces only known demo-profile records. It does not delete user-created
profiles or unrelated rows.

## Known Limitations

- Canonical active-package ResumeAI, Tavily, discovery Groq/ranker, Gmail,
  Guardian, and full Gap Analysis Agent integrations are not live verified.
- The lightweight skill-gap embedding model must already be available locally.
- APScheduler state is process-local and reconstructed from SQLite at startup.
- Frontend has lint/build scripts but no configured unit-test or typecheck script.
- Legacy root-level backend modules remain for teammate compatibility.

## Security Notes

- Gmail scope must remain readonly.
- WebSocket session IDs correlate traces and are not authorization tokens.
- Never display or log credentials, OAuth tokens, resume bytes, email bodies, or
  full pasted job descriptions.
- Use a disposable demo database and clearly label seeded output.

## Single-Worker Scheduler Requirement

Run exactly one Uvicorn worker while using process-local APScheduler. Autoreload
is suitable for local development, but production-like demo startup should omit
`--reload`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

## Final Checklist

- `python -m compileall app scripts` passes.
- `pytest -q` passes.
- `python scripts/validate_openapi.py` passes.
- Seed summary has expected counts and no external-call output.
- `npm run lint` and `npm run build` pass.
- Backend `/health` returns 200 and frontend has no CORS errors.
- Every claimed live integration has an observed PASS result.
- The demo database, `.env`, credentials, tokens, caches, and build output are
  untracked.
