# OpportunIQ Person A Backend Audit

## 1. Executive Summary

Person A's active FastAPI backend is internally coherent, extensively unit/API tested, and substantially ahead of the original package and scheduler examples in the Build Plan. The active implementation is `opportuniq-backend/app/`; legacy root-level Python modules are not used as the application entry point.

Person A's planned backend scope is approximately **88-92% complete**, with most remaining work belonging to Step 9 final hardening or blocked on Person C service/agent modules. The entire backend product is approximately **68-76% complete** because ResumeAI, Tavily, discovery extraction/ranking, Gmail/Guardian, and the Gap Analysis Agent are not live in the active package. The full product is approximately **62-72% complete**; Person B and Person C work is explicitly ongoing, and this audit did not validate frontend workflows.

The backend is demo-ready for local profile CRUD, persisted opportunities, deadlines, scheduler behavior, dashboard notifications, saved tracking, reminder settings, lightweight skill gaps, and mocked Gap Analysis contracts. It is **not yet reliably demo-ready for the complete advertised flow** because live discovery enrichment, Gmail/Guardian, ResumeAI, Gap Analysis execution, and SMTP delivery require teammate services or credentials and have not been end-to-end verified.

## 2. Audit Scope and Method

- Compared the repository against the complete `docs/BUILD_PLAN.md` (2,350 lines).
- The requested path `opportuniq-backend/docs/Build_Plan.md` does not exist; the repository plan is `docs/BUILD_PLAN.md`.
- The plan header says Version 2.0; v2.1 Gap Analysis additions are identified in the body and footer.
- Inspected all active modules under `app/`, all backend tests, dependency/environment documentation, ignore rules, and relevant Git history.
- Generated OpenAPI from `app.main:app` without starting external integrations.
- Initialized an isolated temporary SQLite database twice and inspected tables, columns, and indexes.
- Ran compilation and the complete automated suite.
- Per audit constraints, no live external API, Gmail OAuth, SMTP, or model-download operation was performed.

## 3. Repository and Branch Status

- Repository: `/Users/ananthugs/ananthu/Hackathons/NIT-Hack/OpportunIQ`
- Branch: `main`
- Initial `git status --short`: clean.
- Active startup: `uvicorn app.main:app --reload` from `opportuniq-backend/`.
- Existing ignored local artifacts include `.env`, `opportuniq.db`, virtual environments, and caches; none are tracked by Git.
- Person B and Person C commits are present in shared history. No teammate or frontend file was modified by this audit.

## 4. Person A Responsibility Matrix

| Responsibility | Ownership | Status | Evidence |
|---|---|---|---|
| FastAPI bootstrap/lifecycle/CORS/health | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | `app/main.py`; lifespan initializes DB, restores scheduler, and shuts down safely |
| Database initialization boundary | SHARED | COMPLETE_WITH_IMPROVEMENT | `app/database.py`; additive migrations and indexes |
| Profile APIs/repository | PERSON_A_OWNED | COMPLETE | `routers/profile.py`, `repositories/profile_repository.py` |
| ResumeAI implementation | PERSON_C_OWNED | BLOCKED_BY_TEAMMATE | Guarded resolver in `routers/profile.py`; active service absent |
| Discovery orchestration/JobSpy | PERSON_A_OWNED | COMPLETE | `routers/opportunities.py`, `services/jobspy_service.py` |
| Tavily/discovery Groq/ranker internals | PERSON_C_OWNED/SHARED | BLOCKED_BY_TEAMMATE | Guarded service lookup; active modules absent except canonical reminder Groq adapter |
| Opportunity persistence/cache | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | `repositories/opportunity_repository.py` |
| WebSocket trace manager | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | `websocket_manager.py`, buffered replay; `/ws/agent-trace` |
| Gmail route/metadata boundary | PERSON_A_OWNED | COMPLETE | `routers/gmail.py`, `repositories/gmail_repository.py`, `oauth_state.py` |
| Gmail fetch/Guardian | PERSON_C_OWNED | BLOCKED_BY_TEAMMATE | Guarded imports; active modules absent |
| Deadline registry/business service | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | deadline repository/router/service and calendar/filter APIs |
| APScheduler/reminders | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | UTC-aware `AsyncIOScheduler`, restoration, preferences, diagnostics |
| Notifications | SHARED | COMPLETE_WITH_IMPROVEMENT | active persistence/API and WebSocket event delivery |
| Saved tracker | PERSON_A_OWNED | COMPLETE | joined repository and CRUD router |
| Lightweight skill gap | PERSON_A_OWNED | COMPLETE | `skill_gap_service.py`, opportunity route |
| Reminder settings | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | settings repository/router and scheduler filtering |
| Gap Analysis persistence/API boundary | PERSON_A_OWNED | COMPLETE | schema, models, repository, guarded router, traces |
| Gap deterministic agent/taxonomy | PERSON_C_OWNED | BLOCKED_BY_TEAMMATE | expected modules/files absent |
| Automated backend tests/docs | PERSON_A_OWNED | COMPLETE_WITH_IMPROVEMENT | 194 passing tests; backend README |
| Final hardening | PERSON_A_OWNED | NOT_STARTED | This audit defines the next-phase backlog; no hardening was performed |

## 5. Build Plan Traceability Matrix

| Build Plan Requirement | Planned Owner | Actual Files | Status | Tests | Notes |
|---|---|---|---|---|---|
| 1. Backend package bootstrap | A | `app/__init__.py`, `app/main.py` | COMPLETE_WITH_IMPROVEMENT | import/full suite | Package-safe layout supersedes root examples |
| 2. FastAPI lifespan | A | `app/main.py` | COMPLETE_WITH_IMPROVEMENT | API/scheduler tests | DB + scheduler restoration + shutdown |
| 3. CORS | A | `app/main.py` | COMPLETE | import/API tests | Single configurable frontend origin |
| 4. Health endpoint | A | `app/main.py` | COMPLETE | app tests/live prior phase | Stable response contract |
| 5. SQLite initialization | Shared | `app/database.py` | COMPLETE_WITH_IMPROVEMENT | all repository/API tests | 11 tables including compatibility tables |
| 6. Pydantic models | Shared | `app/models.py` | COMPLETE_WITH_IMPROVEMENT | model/API tests | Pydantic v2 validation and public UUIDs |
| 7. Environment template | A | `.env.example`, `app/config.py` | COMPLETE_WITH_IMPROVEMENT | config tests | Adds `APP_TIMEZONE` |
| 8. Profile manual creation | A | profile router/repository | COMPLETE | profile API/repository | UUID response |
| 9. Profile retrieval | A | profile router/repository | COMPLETE | profile tests | Public ID lookup |
| 10. Profile update | A | profile router/repository | COMPLETE | profile tests | Allowlisted partial update |
| 11. Resume upload boundary | A | `routers/profile.py` | COMPLETE | profile API tests | Size/type validation and guarded forwarding |
| 12. ResumeAI dependency | C | expected active service absent | BLOCKED_BY_TEAMMATE | mock boundary only | No live smoke test |
| 13. JobSpy service | A | `services/jobspy_service.py` | COMPLETE_WITH_IMPROVEMENT | `test_jobspy_service.py` | Async offload, timeout, normalization |
| 14. Tavily integration | A/C | guarded lookup in opportunity router | BLOCKED_BY_TEAMMATE | unavailable-path tests | Active service absent |
| 15. Groq opportunity extraction | B/C | guarded lookup in opportunity router | BLOCKED_BY_TEAMMATE | mocked orchestration | Active canonical Groq file only generates reminders |
| 16. Opportunity persistence | A | opportunity repository/database | COMPLETE_WITH_IMPROVEMENT | repository/API tests | Public IDs, JSON serialization, dedup fields |
| 17. Discovery cache | A | opportunity repository | COMPLETE | opportunity tests | 30-minute configurable lookup |
| 18. Discovery API | A | opportunity router | PARTIAL | API tests | Orchestration complete; enrichment dependencies missing |
| 19. Agent trace WebSocket | A | main/websocket manager | COMPLETE | websocket tests | Session validation |
| 20. WebSocket buffering | A | `websocket_manager.py` | COMPLETE_WITH_IMPROVEMENT | websocket tests | Plan only showed direct live sends |
| 21. Ranker integration | C | guarded lookup | BLOCKED_BY_TEAMMATE | mocked/fallback path | Root legacy implementation is not active-package contract |
| 22. Gmail connect | C/A boundary | Gmail router | PARTIAL | Gmail API tests | Controlled 503 without service |
| 23. Gmail callback | C/A boundary | Gmail router | PARTIAL | Gmail API tests | Metadata/state boundary complete; live OAuth untested |
| 24. Gmail status | A | Gmail router/repository | COMPLETE | Gmail tests | Public profile metadata |
| 25. Gmail scan | C/A boundary | Gmail router | BLOCKED_BY_TEAMMATE | guarded tests | Guardian absent |
| 26. Gmail disconnect | A | Gmail router | COMPLETE | Gmail tests | Guarded credential deletion |
| 27. Gmail service dependency | C | expected `app/services/gmail_service.py` | BLOCKED_BY_TEAMMATE | mocked | Active module absent |
| 28. Guardian dependency | C | expected `app/agents/guardian_agent.py` | BLOCKED_BY_TEAMMATE | guarded tests | Active module absent |
| 29. Deadline schema | A | database/deadline repository | COMPLETE_WITH_IMPROVEMENT | deadline tests | richer registry + review/completion state |
| 30. Deadline CRUD | A | deadline router/service/repository | COMPLETE | API/repository tests | Full public UUID CRUD |
| 31. Deadline calendar feed | A/B contract | deadlines router | COMPLETE_WITH_IMPROVEMENT | deadline API tests | Extra projection endpoint |
| 32. Deadline filters | A | deadlines router/repository | COMPLETE_WITH_IMPROVEMENT | deadline tests | upcoming/today/overdue/review |
| 33. Scheduler lifecycle | A | scheduler service/main | COMPLETE_WITH_IMPROVEMENT | scheduler tests | Async UTC scheduler; loop isolation |
| 34. Reminder-time calculation | A | scheduler service | COMPLETE_WITH_IMPROVEMENT | reminder-time tests | local 09:00 converted to UTC |
| 35. Reminder restoration | A | scheduler service/deadline repository | COMPLETE_WITH_IMPROVEMENT | scheduler/API tests | Rebuilt from durable deadlines |
| 36. Deadline-scheduler synchronization | A | deadline service/router | COMPLETE | scheduler API tests | create/update/delete synchronization |
| 37. Dashboard notification persistence | A/shared | notification repository/schema | COMPLETE_WITH_IMPROVEMENT | notification tests | channel/status/idempotency metadata |
| 38. Test reminder endpoint | A | notifications router | COMPLETE | API tests | Repeatable immediate execution |
| 39. Notification list/read APIs | C/A | notifications router/repository | COMPLETE | API/repository tests | Includes mark-all |
| 40. SMTP adapter | C/A adapter | `app/services/email_service.py` | ACTIVE_ADAPTER_ONLY | adapter + legacy email tests | No live credential delivery test |
| 41. Groq reminder adapter | B/C/A adapter | `app/services/groq_service.py` | ACTIVE_ADAPTER_ONLY | adapter/fallback tests | No live Groq test |
| 42. Saved persistence | A | saved repository/schema | COMPLETE | saved repository tests | Unique profile/opportunity |
| 43. Saved APIs | A | saved router | COMPLETE | saved API tests | Joined details and idempotent save |
| 44. Application statuses | A | saved repository | COMPLETE_WITH_IMPROVEMENT | saved tests | Alias normalization and 422 |
| 45. Lightweight skill gap | A | skill-gap service/opportunity router | COMPLETE | skill-gap tests | weighted exact/partial/missing response |
| 46. Reminder settings | A | settings repository/router/schema | COMPLETE_WITH_IMPROVEMENT | settings tests | Plan API implemented with defaults |
| 47. Preference filtering | A | scheduler/deadline service | COMPLETE_WITH_IMPROVEMENT | settings/scheduler tests | Applies at create/update/restoration |
| 48. Gap Analysis schema | A boundary | database | COMPLETE_WITH_IMPROVEMENT | repository tests/temp schema | partial unique upserts; JD snippet only |
| 49. Gap Analysis repository | A | gap repository | COMPLETE | repository tests | dynamic stale calculation |
| 50. Gap Analysis run | A/C | gap router | BLOCKED_BY_TEAMMATE | mocked API tests | Correct 503 without agent |
| 51. Latest role analysis | A | gap router/repository | COMPLETE | gap tests | no agent dependency |
| 52. Opportunity analysis | A | gap router/repository | COMPLETE | gap tests | pair isolation |
| 53. JD persistence policy | A | gap router/repository | COMPLETE_WITH_IMPROVEMENT | repository/API tests | Explicitly ephemeral, unlike conflicting plan sample |
| 54. Gap Analysis traces | A | gap router/WebSocket manager | COMPLETE | trace/API tests | running/complete/error metadata |
| 55. Gap Analysis Agent | C | expected agent absent | BLOCKED_BY_TEAMMATE | mock contract | Production POST unavailable |
| 56. Skills taxonomy | C | expected data file absent | BLOCKED_BY_TEAMMATE | none | No deterministic full analysis |
| 57. Full test suite | A/shared | `tests/` | COMPLETE_WITH_IMPROVEMENT | 194 passed | Strong unit/API/mock coverage |
| 58. Backend README | A | `README.md` | COMPLETE_WITH_IMPROVEMENT | manual review | Active package commands documented |
| 59. OpenAPI | A/framework | `app/main.py`, routers | COMPLETE | generated in audit | 38 operations, 32 paths |
| 60. Final hardening | A | cross-cutting | NOT_STARTED | audit only | Explicit next-phase boundary |

## 6. Actual Backend Architecture

```text
app.main:app
  routers: profile, opportunities, gmail, deadlines, notifications,
           saved, settings, gap-analysis
  websocket: /ws/agent-trace
  repositories: profile, opportunity, gmail, deadline, notification,
                saved, settings, gap-analysis
  services: JobSpy, deadline coordination, scheduler, skill-gap,
            canonical reminder Groq and SMTP adapters
  guarded teammate modules: ResumeAI, Tavily, discovery extraction/ranker,
                            Gmail service, Guardian, Gap Analysis Agent/service
  SQLite: additive startup initialization
```

Architectural improvements over the plan include package-safe imports, public UUID boundaries, buffered WebSocket traces, `AsyncIOScheduler` in UTC, restart restoration instead of persistent APScheduler jobs, application-timezone handling, idempotent dashboard notifications, reminder preferences, and explicit JD privacy policy.

## 7. API Route Comparison

OpenAPI contains **38 HTTP operations across 32 paths**, plus `/ws/agent-trace`. Framework documentation routes are additional and not counted.

| Area | Actual operations | Classification |
|---|---:|---|
| Profile | 4 | EXACT_MATCH/FUNCTIONALLY_EQUIVALENT |
| Opportunities | 4 | IMPROVED: adds lightweight skill-gap |
| Gmail | 5 | EXACT_MATCH boundary; live services guarded |
| Deadlines | 10 | IMPROVED: calendar and four filter routes |
| Notifications | 5 | IMPROVED: scheduler diagnostics and repeatable test route |
| Saved | 4 | FUNCTIONALLY_EQUIVALENT; profile ID is explicit query input |
| Settings | 2 | EXACT_MATCH |
| Gap Analysis | 3 | EXACT_MATCH boundary; run blocked by agent |
| System | 1 health + 1 WebSocket | IMPROVED buffering/metadata |

Static routes (`/run`, `/calendar`, `/upcoming`, `/today`, `/overdue`, `/needs-review`, `/read-all`, `/scheduler/status`, `/test`) are declared or represented distinctly from dynamic IDs and are exercised through TestClient/OpenAPI. Query parameters omitted in the plan are necessary for stateless public `profile_id` scoping.

## 8. Database Schema Comparison

Temporary initialization was run twice successfully. **11 non-system tables** were audited:

| Table | Classification | Key observations |
|---|---|---|
| `student_profiles` | planned + compatibility | integer internal key plus unique public UUID; JSON TEXT lists; legacy raw resume columns remain |
| `opportunities` | planned + improved | public UUID, session/profile indexes, JSON skills/sources, scores/cache fields |
| `gmail_connections` | implementation improvement | metadata only; no OAuth token content |
| `deadline_registry` | planned + improved | public UUID, Gmail partial unique index, review/completion/cancellation fields |
| `notifications` | planned + improved | delivery status/channel/read state; partial unique deadline-offset-channel index |
| `notification_settings` | later API requirement | public profile primary key and four flags |
| `saved_opportunities` | planned | public UUID; unique profile/opportunity pair |
| `gap_analyses` | v2.1 | public UUID; JSON TEXT; role/opportunity partial unique indexes; 300-char JD policy in repository |
| `deadlines` | LEGACY | old integer-key compatibility table, not active registry |
| `reminders` | LEGACY | old persisted reminder table; active APScheduler reconstructs from registry |
| `emails` | LEGACY/FUTURE | raw email table remains; Guardian active implementation absent |

The plan's “5 tables” statement is outdated. Additive `ALTER TABLE` loops preserve older databases, but there is no formal migration version table. Existing-old-database migration and uniqueness-index creation with dirty legacy duplicates require hardening tests.

## 9. External and Teammate Integration Status

| Integration | Active module/boundary | Expected contract | Status | Fallback |
|---|---|---|---|---|
| ResumeAI | profile router guarded resolver | multipart extract + mapping | GUARDED_MISSING/MOCKED | controlled service error/manual profile |
| JobSpy | `app/services/jobspy_service.py` | job records | LIVE CODE, UNIT TESTED | empty results + safe errors |
| Tavily | opportunity router resolver | portal search list | GUARDED_MISSING | JobSpy-only/error list |
| Groq opportunity extraction | opportunity resolver | structured opportunity | GUARDED_MISSING | raw result may be skipped |
| Ranker | opportunity resolver | deduplicate/score | GUARDED_MISSING/LEGACY_ONLY | local conservative ordering/failure handling |
| Gmail OAuth service | Gmail router guarded loader | OAuth/credential operations | GUARDED_MISSING | 503/status metadata |
| Guardian Agent | Gmail router guarded loader | scan + deadlines | GUARDED_MISSING | controlled unavailable response |
| Groq reminders | active canonical adapter | async `generate_reminder` | ACTIVE_ADAPTER_ONLY | deterministic scheduler text |
| SMTP | active canonical adapter | async bool send | ACTIVE_ADAPTER_ONLY | dashboard succeeds, email false |
| Gap Analysis Agent | guarded agent/service loader | sync/async `run(...)` | GUARDED_MISSING/MOCKED | POST 503; GET still works |
| Deterministic gap service | expected service absent | evidence/taxonomy pipeline | GUARDED_MISSING | none; no fake production analysis |
| Skills taxonomy | expected JSON absent | role/skill mapping | GUARDED_MISSING | none |

No live external integration was tested in this audit.

## 10. Scheduler and Background Processing Audit

| Reliability item | Assessment |
|---|---|
| One process-local scheduler; no import-time start | VERIFIED + UNIT_COVERED |
| Idempotent start and safe shutdown | VERIFIED + UNIT_COVERED |
| Reload/event-loop isolation | UNIT_COVERED; NEEDS live reload soak |
| UTC scheduler and aware calculations | VERIFIED |
| `APP_TIMEZONE` same-day 09:00 conversion | UNIT_COVERED |
| Deterministic job IDs and `replace_existing` | VERIFIED + UNIT_COVERED |
| Cancel/reschedule/create/delete synchronization | API_COVERED |
| Startup restoration and active-state exclusion | API/UNIT_COVERED |
| Reminder preference filtering | UNIT/API_COVERED |
| Notification idempotency | repository/service covered |
| SMTP and WebSocket failure isolation | UNIT_COVERED |

The plan's `BackgroundScheduler`, naive `datetime.now()`, underscore job IDs, and “5 jobs” hardening text are outdated. Actual policy is four jobs and is safer for FastAPI async operation. Multi-worker deployment remains unsafe without leader election or a shared job store and is a hardening item.

## 11. Security and Privacy Audit

- **Secrets:** no tracked `.env`, credential JSON, OAuth token, database, or model-cache file found. Secret-name references occur in code/tests/docs, not committed values.
- **Ignore rules:** cover `.env*`, credentials, tokens, SQLite, caches, virtual environments, and frontend artifacts.
- **OAuth:** Gmail read-only scope is planned/tested at boundary; token file operations are teammate-service dependent.
- **SMTP:** password is read from environment; active adapter logs exception type only. Scheduler may log safe exception text from adapter boundaries and should be standardized during hardening.
- **Uploads:** profile route enforces supported extensions and 5 MB limit before forwarding.
- **Raw resume:** schema still contains `raw_resume_text`; active repository columns do not expose/store it. Retention policy should be explicit.
- **JD privacy:** full pasted JD is passed transiently to the agent boundary; persistence stores/returns at most 300 characters and JD mode is ephemeral.
- **SQL:** values are parameterized. Dynamic clauses/columns are assembled from hardcoded allowlists/constants. No direct user-supplied SQL identifier was found.
- **CORS:** restricted to configured `FRONTEND_URL`; credentials enabled. Production origin validation remains.
- **Errors:** most routes expose controlled HTTP details; broad `logger.exception` calls can retain stack context locally but no API stack trace was observed.
- **WebSocket:** nonblank session validation exists; no authentication/authorization or connection-count cap exists.
- **Memory:** buffered trace state is process-local and bounded per session, but session-map lifecycle/concurrency requires hardening review.
- **PII logs:** no direct profile/email body logging identified in active code; integration errors should be scrubbed consistently.

## 12. Automated Test Audit

- Test files: 28.
- Result: **194 passed, 0 failed, 0 skipped, 68 warnings in 9.13 seconds**.
- Compilation: passed.
- Coverage types: repository unit tests, API TestClient tests, mocked integration boundaries, scheduler lifecycle/calculation tests, WebSocket manager/trace tests.
- Warnings: Starlette TestClient/httpx deprecation, legacy `datetime.utcnow()`, and deprecated FastAPI/Starlette status constants.

Coverage classification:

- `UNIT_COVERED`: repositories, mapping/normalization, reminder times, scheduler primitives, adapters, skill-gap calculations.
- `API_COVERED`: profile, opportunity, Gmail boundary, deadlines, notifications, saved, settings, Gap Analysis boundary.
- `MOCK_INTEGRATION_COVERED`: ResumeAI, discovery collaborators, Gmail/Guardian, Gap Agent, SMTP/Groq failures.
- `LIVE_INTEGRATION_NOT_TESTED`: all credentialed/external services and model loading.
- `END_TO_END_NOT_TESTED`: resume-to-discovery-to-save-to-Gmail-to-reminder full workflow.

Missing categories: migration from realistic old databases, concurrent duplicate writes, multi-worker scheduler behavior, autoreload soak, WebSocket disconnect races, malformed teammate models beyond current mocks, large JD/result payloads, privacy-retention checks, and complete demo workflow.

## 13. Git History Audit

Strengths:

- Person A work is generally incremental and traceable by schema/model/repository/router/test/docs concern.
- Later phases use clear Conventional Commit scopes (`gmail`, `deadlines`, `scheduler`, `notifications`, `saved`, `settings`, `gap-analysis`).
- Fix commits preserve the reason for scheduler event-loop isolation and agent keyword compatibility.
- No secret/generated artifact was found in tracked paths.

Weaknesses:

- Early `[Phase N]` subjects are consistent but not Conventional Commit format.
- Commits named `Added files`, `Added files in module 3`, and `(docs): updated build plan` are vague; ownership is unclear and should not be rewritten.
- `refactor(services): expose canonical reminder adapters` combines Groq, email, and scheduler changes.
- `feat(saved): expose saved opportunity tracker APIs` and `feat(gap-analysis): expose guarded analysis APIs` combine multiple endpoints, acceptable for hackathon pace but less granular than the plan requested.
- Shared merge commits interleave Person B/C work. This audit found no reason to rewrite history.

## 14. Build Plan Inconsistencies

All items below are `PLAN_INCONSISTENCY`, not implementation failures:

1. Header says Version 2.0 while body/footer describe v2.1.
2. Requested audit path differs from the actual plan location/casing.
3. “Five-agent” architecture numbers six agents after Gap Analysis was added.
4. Architecture says “5 tables” but visually lists six and Section 7 later expands the schema.
5. Root-level imports/layout conflict with the active `app/` package architecture.
6. Scheduler examples use `BackgroundScheduler`, naive local datetimes, and different job IDs; active async UTC design is superior.
7. Step 9 says verify five scheduler jobs, while reminder policy defines four.
8. Evidence levels are described as 0-3 in methodology text but final OpportunIQ models/service examples use 0-2.
9. Gap Agent sample directly persists every result while the frontend explicitly labels pasted-JD analysis “not saved.” Active ephemeral JD policy resolves this privacy conflict.
10. Gmail plan assigns router implementation to Person C, while later ownership and actual repository history split route boundary work.
11. Saved/notification endpoint examples omit required profile scoping used by the stateless API.
12. Several plan snippets use internal integer `id`; active APIs correctly use public UUIDs.
13. Database and WebSocket examples use unguarded imports/global state that do not reflect active compatibility and buffering requirements.

## 15. Completion Assessment

### A. Person A planned backend scope

- Complete or improved: **88-92%**.
- Partial/needs hardening: **5-8%**.
- Blocked by teammate dependencies: **3-5%** of Person A's observable integration outcomes.
- Not started: final hardening itself, represented separately rather than as missing feature implementation.

Basis: nearly all owned routes, repositories, scheduler work, tests, and docs exist. Discovery, Gmail, ResumeAI, and Gap execution cannot satisfy their end conditions without teammate modules/live services.

### B. Entire backend product

Estimated **68-76% complete**. Persistence and API surfaces are broad and stable, but core advertised intelligence/integration paths remain guarded rather than live.

### C. Full OpportunIQ product

Estimated **62-72% complete**. Frontend commits show substantial Person B progress, but this audit intentionally did not validate frontend behavior. Full demo flow and Person C integrations remain unverified.

These are reasoned ranges, not line-count percentages.

## 16. Remaining Blockers

- ResumeAI deployed endpoint and contract verification.
- Active Tavily, opportunity extraction, and ranking collaborators.
- Gmail OAuth/fetch service and Guardian Agent.
- Gap Analysis deterministic service, taxonomy, and agent.
- Valid SMTP/Groq credentials for live delivery/generation tests.
- Person B frontend completion and cross-contract verification.

## 17. Final Hardening Backlog

| Priority | Item | Files | Owner/blocker | Validation | Parallel-safe? |
|---|---|---|---|---|---|
| P0 | Lock and test teammate service contracts | profile/opportunity/Gmail/gap routers; service adapters | A with C | contract tests + one live smoke each | Yes, using adapters |
| P0 | Run complete demo workflow | all active routers + frontend | A/B/C | timed E2E under 6 minutes | Requires team readiness |
| P0 | Verify Gmail/Guardian and token lifecycle | Gmail router + incoming C modules | C/A | demo account OAuth/scan/disconnect | No until C lands |
| P0 | Verify Gap Agent outputs against API guards | gap router/models/repository | C/A | all three modes; JD DB inspection | No until C lands |
| P0 | Validate live reminder email and dashboard event | email/scheduler/notifications | C/A | test reminder, inbox, WebSocket | Credentials required |
| P0 | Prepare deterministic demo fallback dataset/runbook | seed script/README | A/C | offline demo rehearsal | Yes |
| P1 | Existing-database migration test | database + all repositories | A | fixture from pre-migration schema, two init runs | Yes |
| P1 | Standardize external timeouts/errors/log scrubbing | integration routers/services | A/C | failure matrix tests | Yes by module |
| P1 | Remove aware-datetime deprecations | WebSocket/opportunity repository | A | warnings and time-bound tests | Yes |
| P1 | Scheduler deployment constraint/leader strategy | scheduler/main/docs | A | multi-process/reload test | Yes |
| P1 | WebSocket authorization, limits, race tests | main/websocket manager | A/B | disconnect/reconnect/load tests | Coordinate client |
| P1 | OpenAPI/request-contract review with frontend | all routers | A/B | generated client/manual matrix | Yes |
| P1 | Privacy retention policy | profile/email/gap schema | A/C | DB/log inspection and documented policy | Yes |
| P1 | Concurrency/idempotency tests | saved/notification/deadline/gap repositories | A | parallel insert/update tests | Yes |
| P2 | Legacy root/table cleanup plan | root backend files; legacy DB tables | Shared | dependency search + migration rehearsal | After demo |
| P2 | Improve code formatting/readability in recent compact modules | saved/settings/gap modules | A | formatter/linter/full tests | After integration freeze |
| P2 | Upgrade deprecated TestClient/status usage | tests/routes | A | warning-free suite | After demo |

## 18. Demo Readiness Assessment

**Current rating: conditionally demo-ready for backend-owned local flows; not ready for the full advertised live demo.**

Strong demo paths: profile manual CRUD, cached/persisted opportunities, deadline calendar and filters, scheduler job creation/cancellation/restoration, dashboard notifications, saved tracker, settings, and lightweight skill gap.

Risky or unavailable paths: resume upload against real ResumeAI, Tavily/Groq/ranker discovery quality, Gmail connect/scan, extracted deadlines, live SMTP, and full Gap Advisor execution. The app degrades safely in many cases, but controlled 503/fallback behavior is not equivalent to feature completion.

## 19. Recommended Next Actions

1. Freeze API contracts with Person B and Person C using OpenAPI and adapter signatures.
2. Integrate one teammate module at a time with contract tests before broad refactoring.
3. Complete P0 live smoke tests using dedicated demo credentials.
4. Rehearse an offline fallback path and the full six-minute demo.
5. Begin Final Backend Hardening only after teammate interfaces are available or formally declared deferred.

Exact next-phase boundary: integration validation, reliability/security hardening, migration testing, warning cleanup, and demo runbook work. It excludes new product features, frontend implementation, taxonomy/scoring implementation, and teammate agent internals.

## 20. Validation Evidence

Commands and outcomes:

```text
pwd
# /Users/ananthugs/ananthu/Hackathons/NIT-Hack/OpportunIQ

git status --short
# clean before report creation

git branch --show-current
# main

python -m compileall app
# passed

pytest -q
# 194 passed, 0 failed, 0 skipped, 68 warnings in 9.13s

temporary DATABASE_PATH + init_db() twice
# passed; 11 non-system tables inspected

app.openapi()
# 38 HTTP operations across 32 paths
```

No external API, OAuth, SMTP, model download, source-code mutation, Build Plan edit, frontend edit, or teammate-code edit occurred during this audit.
