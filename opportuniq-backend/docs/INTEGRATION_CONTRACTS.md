# OpportunIQ Integration Contracts

This document records the active integration contracts as of 2026-08-01. The
active backend package is `opportuniq-backend/app`; similarly named root-level
modules are legacy or teammate-owned and are not imported by production routes
unless an explicit active-package adapter is added.

## Public IDs

All cross-boundary identifiers are nonblank UUID strings: `profile_id`,
`opportunity_id`, `saved_id`, `deadline_id`, `notification_id`, `analysis_id`,
and `session_id`. SQLite integer keys are internal and must not appear in URLs,
frontend storage, WebSocket payloads, or API responses. WebSocket session IDs
correlate events; they are not authorization tokens.

## Backend Base URL

The frontend reads `VITE_API_BASE_URL`, defaulting to
`http://localhost:8000`. Backend CORS reads `FRONTEND_URL`, defaulting to
`http://localhost:5173`.

## WebSocket URL

The frontend reads `VITE_WS_BASE_URL`, defaulting to `ws://localhost:8000`, and
connects to `/ws/agent-trace?session_id=<PUBLIC_SESSION_ID>`. The server replays
buffered events, accepts `ping`, and responds with `pong`.

## Profile Contract

- Manual create: `POST /api/profile/manual` with the profile model; returns the
  persisted profile including `profile_id`.
- Retrieve/update: `GET` and `PATCH /api/profile/{profile_id}`.
- Resume upload: `POST /api/profile/upload`, multipart field **`file`**.
- Persistence boundary: `app.repositories.profile_repository`; asynchronous.
- Missing profiles return 404. Invalid uploads/results return controlled 4xx
  responses. Raw uploaded bytes are neither logged nor persisted.

## Discovery Contract

- Start: `POST /api/opportunities/search` with `profile_id` and optional
  `force_refresh`; returns `session_id`, status, and result metadata.
- Results: `GET /api/opportunities` with exactly one of `profile_id` or
  `session_id`; response contains `opportunities`.
- Pipeline: active router calls JobSpy and optional active-package Tavily,
  extraction, and ranking adapters. Provider failures permit partial success and
  are represented in safe trace/error metadata.

## Opportunity Contract

- Detail: `GET /api/opportunities/{opportunity_id}`.
- Lightweight gap: `GET /api/opportunities/{opportunity_id}/skill-gap` with
  `profile_id`.
- Saved tracker: `POST /api/saved/{opportunity_id}`, `GET /api/saved`, and
  `PATCH`/`DELETE /api/saved/{saved_id}`. Save/list require `profile_id`.
- Public opportunity IDs are strings; match scores are numeric and no fallback
  ordering may be described as semantic ranking.

## ResumeAI Contract

| Item | Contract |
|---|---|
| Active module | `app.services.resume_service` |
| Callables | `async forward_to_resumeai(file_bytes: bytes, filename: str, content_type: str) -> dict`; `map_resumeai_to_profile(resumeai_data: dict, profile_id: str | None = None) -> dict | StudentProfile` |
| Keywords | `file_bytes`, `filename`, `content_type`; then `resumeai_data`, optional `profile_id` |
| Exceptions | configuration -> unavailable; timeout -> timeout; malformed response -> upstream/contract error |
| Timeout | `EXTERNAL_HTTP_TIMEOUT_SECONDS` |
| Fallback | manual profile creation; upload never returns fake extraction success |
| Status | **guarded missing**. A root `services.resume_service` has an incompatible `UploadFile` signature and legacy model imports; no active adapter exists. |

## Tavily Contract

| Item | Contract |
|---|---|
| Active module | `app.services.tavily_service` |
| Callable | `async search_hackathons_and_portals(*, role: str, skills: list[str], location: str | None = None, limit: int = 10) -> list[dict]` |
| Exceptions | unavailable, timeout, or malformed response; partial discovery continues |
| Timeout | `EXTERNAL_HTTP_TIMEOUT_SECONDS` |
| Fallback | JobSpy-only results plus safe provider error metadata |
| Status | **guarded missing** |

## Opportunity Groq Contract

| Item | Contract |
|---|---|
| Active module | `app.services.groq_service` |
| Callable | `async extract_opportunity(*, raw_result: dict) -> Opportunity | dict` |
| Exceptions | unavailable, timeout, invalid external result |
| Timeout | `AGENT_TIMEOUT_SECONDS` |
| Fallback | malformed/unstructured item is skipped; no invented fields |
| Status | **adapter only** for reminders; discovery extraction is guarded missing. Root teammate implementation is not active. |

## Ranker Contract

| Item | Contract |
|---|---|
| Active module | `app.services.ranker_service` |
| Callable | `async deduplicate_and_rank(*, opportunities: list[dict], profile: dict) -> list[dict]` (sync implementations may be wrapped with `asyncio.to_thread`) |
| Exceptions | malformed results are rejected; partial discovery may use conservative ordering |
| Timeout | `AGENT_TIMEOUT_SECONDS` |
| Fallback | deterministic non-semantic ordering, clearly identified as fallback |
| Status | **guarded missing**. Root teammate ranker is not an active-package adapter. |

## Gmail OAuth Contract

| Item | Contract |
|---|---|
| Active module | `app.services.gmail_service` |
| Callables | authorization URL; code exchange; credential save/load/delete/existence; connected email; message fetch |
| Router | `/api/gmail/connect`, `/callback`, `/status`, `/scan`, `/disconnect` |
| Exceptions | disconnected -> 409; unavailable -> 503; timeout -> 504; malformed upstream -> 502 |
| Timeout | `EXTERNAL_HTTP_TIMEOUT_SECONDS` |
| Security | Gmail readonly scope; token material never enters API responses or logs |
| Fallback | disconnected UI and seeded demo deadlines |
| Status | **guarded missing** |

## Guardian Agent Contract

| Item | Contract |
|---|---|
| Active module | `app.agents.guardian_agent` |
| Callable | `async run_guardian_agent(*, profile_id: str, session_id: str | None = None) -> dict` |
| Return | `emails_scanned`, `deadlines_found`, `needs_review`, `errors`, `deadlines` |
| Persistence | every extracted deadline calls `app.services.deadline_service.create_gmail_deadline`; no raw SQL |
| Timeout | `AGENT_TIMEOUT_SECONDS` |
| Fallback | controlled unavailable response and seeded demo deadline |
| Status | **guarded missing** |

## Deadline Creation Contract

- Router: `POST /api/deadlines`; service:
  `app.services.deadline_service.create_deadline` / `create_gmail_deadline`.
- Input includes public `profile_id`, title, source, optional opportunity/Gmail
  metadata, and an aware or normalizable deadline datetime.
- The service owns duplicate protection, UTC normalization, persistence,
  preference filtering, and scheduler coordination. Agents must not write
  deadline rows directly.

## Reminder Groq Contract

| Item | Contract |
|---|---|
| Active module | `app.services.groq_service` |
| Callable | `async generate_reminder(**deadline_context) -> str | model` |
| Timeout | `AGENT_TIMEOUT_SECONDS` (scheduler also applies a bounded call timeout) |
| Exceptions | swallowed at scheduler boundary after safe logging |
| Fallback | deterministic reminder text; dashboard delivery continues |
| Status | **adapter only**, mock verified; not live verified |

## Email Contract

| Item | Contract |
|---|---|
| Active module | `app.services.email_service` |
| Callable | `async send_reminder_email(*, to_email: str, subject: str, body: str) -> bool` |
| Execution | blocking SMTP is offloaded with `asyncio.to_thread` |
| Timeout | `SMTP_TIMEOUT_SECONDS` |
| Exceptions | safe failure result/logging; no credentials or body logged |
| Fallback | dashboard notification remains successful |
| Status | **adapter only**, mock verified; not live verified |

## Gap Analysis Agent Contract

| Item | Contract |
|---|---|
| Active module | `app.agents.gap_analysis_agent` or `app.services.gap_analysis_service` |
| Callable | `async run(*, profile_id: str, target_role: str | None = None, job_description: str | None = None, opportunity_id: str | None = None, session_id: str | None = None) -> GapAnalysisResult` |
| Persistence | router/repository owns role and opportunity persistence; JD mode is ephemeral |
| Timeout | `AGENT_TIMEOUT_SECONDS` |
| Exceptions | unavailable -> 503; timeout -> 504; invalid result -> 422/502 |
| Fallback | retrieve seeded persisted analyses; no fake run success |
| Status | **guarded missing**. Root teammate agent uses direct SQLite, legacy imports, and import-time embedding initialization, so it is not safely activated. |

## Error Response Contract

Existing FastAPI `detail` compatibility is retained. Integration errors use a
detail object shaped as:

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Gap analysis service is not available.",
    "service": "gap-analysis",
    "fallback": "manual"
  }
}
```

Status policy: 503 unavailable, 504 timeout, 502 malformed upstream response,
422 invalid external result, and 409 disconnected/ineligible state. Responses
must not contain stack traces, credentials, resume bytes, email bodies, or full
job descriptions.

## Demo Fallback Contract

`DEMO_MODE=true` may improve fallback guidance and enable explicit seed tooling;
it does not bypass validation or change a failed live call into success. Seeded
records are deterministic and marked as demo data. Full live, mixed, and offline
demo modes retain the same public API shapes.

## Frontend API Usage Matrix

| Frontend feature | Frontend request | Backend route | Status | Mismatch |
|---|---|---|---|---|
| Manual profile | `POST /api/profile/manual` | Same | ALIGNED | Reuses existing profile form and stores public profile ID |
| Resume upload | multipart `file` | `POST /api/profile/upload`, field `file` | ALIGNED | Live ResumeAI remains guarded missing |
| Profile retrieve/edit | `GET/PATCH /api/profile/{profile_id}` | Same | ALIGNED | Public ID stored as `opportuniq:profileId` |
| Opportunity search | `POST /api/opportunities/search` | Same | ALIGNED | Controlled provider fallback still needed in UI |
| Opportunity results | `GET /api/opportunities` by profile/session | Same | ALIGNED | None |
| Agent trace | `/ws/agent-trace?session_id=...` | Same | ALIGNED | Frontend deduplication/reconnect needs tests |
| Save opportunity | `POST /api/saved/{opportunity_id}` | Same | ALIGNED | Uses public profile query parameter |
| Tracker status | `PATCH /api/saved/{saved_id}` | Same | ALIGNED | Canonical status values aligned |
| Remove saved | `DELETE /api/saved/{saved_id}` | Same | ALIGNED | Uses public saved ID |
| Lightweight skill gap | No API helper | `GET /api/opportunities/{id}/skill-gap` | FRONTEND_MISSING | UI has no integration |
| Gap Advisor | No page/helper | `/api/gap-analysis/*` | FRONTEND_MISSING | BLOCKED_BY_TEAMMATE for live run |
| Gmail connect | configurable API base + profile query | `GET /api/gmail/connect` | ALIGNED | Live service guarded missing |
| Gmail status/scan/disconnect | Canonical routes | Same | ALIGNED | Live service guarded missing |
| Deadline list/CRUD | Canonical routes | Same | ALIGNED | Calendar-specific route is unused but not required |
| Notifications | list/read/read-all | Same | ALIGNED | Sends redundant `unread` query parameter |
| Reminder settings | `GET/PUT /api/settings/notifications` | Same | ALIGNED | Four scheduler offsets are API-backed |
| Scheduler diagnostics/test | No UI helper | notification status/test routes | FRONTEND_MISSING | Optional demo control |

## Current Integration Status Summary

- **Live code, locally tested:** FastAPI/SQLite, JobSpy adapter logic.
- **Mock verified:** active routers, repositories, scheduler, WebSocket,
  reminder Groq/SMTP boundaries.
- **Adapter only:** reminder Groq and SMTP.
- **Guarded missing:** ResumeAI, Tavily, discovery extraction/ranking, Gmail,
  Guardian, and canonical Gap Analysis execution.
- **Not performed:** live external API, OAuth, model download, or email checks.
- **Frontend validation:** npm lockfile synchronized; ESLint and production
  build pass. No frontend unit-test or typecheck script is configured.
