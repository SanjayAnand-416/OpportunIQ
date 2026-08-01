# OpportunIQ — Build Plan
### TATA Centre AI/ML Hackathon | NIT Tiruchirappalli | AI for Education
### 36-Hour Implementation Reference · Version 2.0

> **Changelog v2.0:** ResumeAI integration updated to reflect the teammate's confirmed architecture.
> ResumeAI is a separate TypeScript/Node.js microservice that owns all resume parsing, text extraction,
> and Gemini AI calls. The Profile Agent (FastAPI) forwards the raw uploaded file to ResumeAI via
> `POST /api/v1/profile/extract` (multipart/form-data) and receives a structured JSON response.
> PyMuPDF removed from Profile Agent. Endpoint path, request format, and response schema updated throughout.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [User Flow Summary](#4-user-flow-summary)
5. [Page Specifications](#5-page-specifications)
6. [Agent Pipeline Design](#6-agent-pipeline-design)
7. [Database Schema](#7-database-schema)
8. [API Endpoint Registry](#8-api-endpoint-registry)
9. [Build Plan — Step by Step](#9-build-plan--step-by-step)
10. [Pre-Hackathon Checklist (Step 0)](#10-pre-hackathon-checklist-step-0)
11. [Environment Variables Reference](#11-environment-variables-reference)

---

## 1. System Overview

**OpportunIQ** is a five-agent agentic AI system built on LangGraph that solves two connected problems faced by every engineering student and fresher in India:

**Problem 1 — Fragmented Opportunity Discovery**
Relevant internships, jobs, and hackathons are scattered across LinkedIn, Naukri, Unstop, Devfolio, HackerEarth, Internshala, and company career portals. Students either miss opportunities entirely or discover them after the deadline has passed.

**Problem 2 — Missed Deadlines**
Once a student applies, critical follow-up deadlines — hackathon submissions, interview slots, offer acceptance windows — get buried in email inboxes and go unnoticed. There is no unified system that both discovers the right opportunities and proactively guards against missing the deadlines that follow.

**What OpportunIQ does:**
- Takes a student's resume or manual profile input
- Searches across 8+ platforms for matching opportunities using a hybrid JobSpy + Tavily discovery layer
- Ranks results by skill match (sentence-transformer cosine similarity) and deadline urgency
- Deduplicates cross-platform listings using a 3-layer pipeline
- **Runs a Gap Analysis Agent that compares the student's resume skills against a target job role or opportunity and produces a prioritised skill gap report with project suggestions and learning resources**
- Connects to Gmail (OAuth read-only) to extract application deadlines from emails using an LLM
- Schedules proactive reminders at 7 days, 3 days, 1 day, and same-day intervals
- Delivers contextual, personalised reminder messages via in-app notifications and email

> **v2.1 Addition — Gap Analysis Agent:** Added following Review 1 feedback. The Gap Analysis module is adapted from the ResumeAI project's `gap-advisor.service.ts` logic, re-implemented natively in Python to match OpportunIQ's FastAPI + SQLite stack. The TypeScript source cannot be copy-pasted directly (different runtime, database engine, and dependency chain), but the core methodology — deterministic evidence scoring + LLM narrative synthesis — is preserved exactly. See Section 6 (Agent Pipeline) and Section 9 (Build Plan Step 3.5) for implementation details.

**Thrust Area:** AI for Education
**Team Size:** 3 members
**Hackathon Format:** 36-hour on-site build

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                  │
│  Landing | Onboarding | Dashboard | Calendar | Settings     │
│  TailwindCSS · FullCalendar.js · Axios · WebSocket client  │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                  │
│  REST API · WebSocket server · OAuth callback handler       │
│  APScheduler (background reminder jobs)                     │
└──────┬──────────────┬───────────────────────┬───────────────┘
       │              │                       │
┌──────▼──────┐ ┌─────▼──────┐      ┌────────▼──────────────────────┐
│  LangGraph  │ │  SQLite DB │      │       External Services        │
│  Agent Graph│ │  (5 tables)│      │                               │
│             │ │            │      │  ┌─────────────────────────┐  │
│ ① Profile   │ │ profiles   │      │  │  ResumeAI Microservice  │  │
│ ② Discovery │ │ opportun.  │      │  │  (TypeScript / Node.js) │  │
│ ③ Gap Agent │ │ deadlines  │      │  │  POST /api/v1/profile/  │  │
│ ④ Ranker    │ │ saved_ops  │      │  │       extract           │  │
│ ⑤ Guardian  │ │ notifs     │      │  │  • PDF/DOC/DOCX parsing │  │
│ ⑥ Notifier  │ │ gap_anal.  │      │  │  • Gemini AI extraction │  │
└─────────────┘ └────────────┘      │  │  • Gemini AI extraction │  │
                                    │  │  • Returns structured   │  │
                                    │  │    profile JSON         │  │
                                    │  └─────────────────────────┘  │
                                    │  JobSpy (scrape)               │
                                    │  Tavily API                    │
                                    │  Gmail API (OAuth)             │
                                    │  Groq API (LLM)                │
                                    │  SMTP (Gmail relay)            │
                                    └───────────────────────────────┘
```

### ResumeAI Microservice — Separation of Concerns

This is a critical architectural boundary. **ResumeAI and the Profile Agent have distinct, non-overlapping responsibilities.**

| Responsibility | ResumeAI (TypeScript) | Profile Agent (FastAPI) |
|---|---|---|
| PDF / DOC / DOCX parsing | ✅ Owns this | ❌ Never does this |
| Resume text extraction | ✅ Owns this | ❌ Never does this |
| Gemini AI calls | ✅ Owns this | ❌ Never does this |
| AI prompt management | ✅ Owns this | ❌ Never does this |
| Returning structured JSON | ✅ Owns this | ❌ Never does this |
| Student profile storage | ❌ Never does this | ✅ Owns this |
| SQLite CRUD operations | ❌ Never does this | ✅ Owns this |
| Profile business logic | ❌ Never does this | ✅ Owns this |
| Missing field detection | ❌ Never does this | ✅ Owns this |
| Manual profile editing | ❌ Never does this | ✅ Owns this |

### Gap Analysis — Why the ResumeAI Module Cannot Be Copy-Pasted Directly

The ResumeAI Gap Analysis module (`gap-advisor.service.ts`, `gap-evidence.service.ts`, `gap-taxonomy.service.ts`) is TypeScript running on Node.js and depends on:
- A **PostgreSQL** database with `portfolio_items`, `job_targets`, `gap_analyses`, and `users.career_goal` tables — none of which exist in OpportunIQ's SQLite schema
- **BullMQ** queue infrastructure (Node.js-only)
- **NVIDIA NIM** as the primary LLM provider with Gemini + Groq fallback
- Portfolio embeddings stored as vector columns in PostgreSQL
- Authentication middleware tied to the ResumeAI user session system

**OpportunIQ uses Python, FastAPI, SQLite, and Groq.** Direct copy-paste is not possible.

**What IS reused:** The methodology, not the code.
- The **deterministic evidence scoring** logic (evidence levels 0–3 based on skill presence in profile)
- The **skill taxonomy mapping** from career goal → required skills
- The **JD comparison mode** (direct job description → required skills list)
- The **LLM synthesis pattern** (deterministic gaps computed first, LLM adds narrative and recommendations)
- The **output schema** (missing\_skills, suggested\_projects, learning\_resources, overall\_assessment)
- The **hallucination guard** (LLM output filtered against deterministic gap list)

This methodology is re-implemented in `services/gap_analysis_service.py` and `agents/gap_analysis_agent.py` in Python, adapted for OpportunIQ's data model where the student profile (skills, target\_roles) replaces `portfolio_items` and the opportunity's `skills_required` field replaces `job_targets`.

**Data flow for profile setup:**
```
Student uploads resume
        │
        ▼
Profile Agent (FastAPI) receives file
        │  HTTP POST multipart/form-data
        │  raw file forwarded — no parsing done here
        ▼
ResumeAI API  POST /api/v1/profile/extract
        │  Parses PDF/DOC/DOCX
        │  Extracts text
        │  Calls Gemini AI
        │  Validates JSON response
        ▼
Returns structured JSON:
{
  "success": true,
  "data": {
    "full_name": "...",
    "year_of_study": "...",
    "graduation_year": 2027,
    "target_roles": [...],
    "skills": [...],
    "preferred_location": "...",
    "opportunity_type": "..."
  }
}
        │
        ▼
Profile Agent maps response → StudentProfile Pydantic schema
Profile Agent identifies missing/null fields
Profile Agent saves to SQLite
Profile Agent returns { profile_id, profile, missing_fields[] }
```

### Data Flow — Opportunity Discovery

```
Student Profile (SQLite)
        │
        ▼
Discovery Agent
  ├── JobSpy: LinkedIn + Naukri + Indeed + Glassdoor + Google
  └── Tavily: Unstop + Devfolio + HackerEarth + Company portals
        │
        ▼
Raw Results (title, company, URL, description, deadline, skills)
        │
        ▼
Ranker Agent — 3-Layer Deduplication
  ├── Layer 1: URL hash (exact duplicates)
  ├── Layer 2: rapidfuzz title+company fuzzy match (≥85 threshold)
  └── Layer 3: sentence-transformer cosine similarity (≥0.92)
        │
        ▼
Scoring: 0.7 × skill_match + 0.3 × urgency_score
        │
        ▼
Top 15 Ranked Opportunity Cards → React Dashboard
```

### Data Flow — Deadline Guardian

```
Gmail OAuth (read-only)
        │
        ▼
Guardian Agent — 3-Pass Email Fetch
  ├── Pass 1: Wide subject keywords (interview, offer, shortlisted, deadline...)
  ├── Pass 2: Sender domain filter (naukri.com, linkedin.com, hr@, recruit@...)
  └── Pass 3: Body keyword sweep (closes on, submit by, offer letter...)
        │
        ▼
Dedup by message_id → Union of all 3 passes
        │
        ▼
Groq gpt-oss-20b (via Instructor + Pydantic)
→ Extracts: has_deadline, deadline_date, deadline_time,
            event_type, organization, action_required, confidence
        │
        ▼
confidence ≥ 0.6 → Deadline Registry (SQLite)
confidence < 0.6 → "Needs review" flag in dashboard
        │
        ▼
Notifier Agent (APScheduler DateTrigger × 4 per deadline)
  ├── 7 days before
  ├── 3 days before
  ├── 1 day before
  └── Same day at 9:00 AM
        │
        ▼
Groq gpt-oss-120b → Contextual reminder message
        │
  ┌─────┴──────┐
  ▼            ▼
WebSocket   SMTP email
(bell badge) (Gmail relay)
```

---

## 3. Tech Stack

### Backend

| Component | Technology | Purpose |
|---|---|---|
| Web framework | FastAPI (Python) | REST API + WebSocket server |
| Agent orchestration | LangGraph | 5-agent stateful pipeline |
| LLM client | Groq SDK + Instructor | Structured LLM output with Pydantic |
| LLM — high quality | `openai/gpt-oss-120b` on Groq | Opportunity extraction, reminder generation |
| LLM — high volume | `openai/gpt-oss-20b` on Groq | Email deadline extraction (50–100 emails) |
| Profile parsing | ResumeAI microservice (TypeScript/Node.js) | Separate deployed service — owns PDF/DOC/DOCX parsing, text extraction, and Gemini AI calls. Profile Agent only forwards the raw file and receives structured JSON. |
| Job scraping | `python-jobspy` | LinkedIn, Naukri, Indeed, Glassdoor, Google Jobs |
| Web search | Tavily API | Unstop, Devfolio, HackerEarth, company portals |
| Skill matching | `sentence-transformers` (all-MiniLM-L6-v2) | Cosine similarity for opportunity ranking |
| Fuzzy matching | `rapidfuzz` | Title+company deduplication |
| Gmail integration | `google-api-python-client` + `google-auth-oauthlib` | Read-only email access, OAuth 2.0 |
| Scheduling | APScheduler | Background reminder jobs |
| Email delivery | `smtplib` (Gmail SMTP relay) | Reminder emails to student |
| Database | SQLite + `aiosqlite` | Profile, opportunities, deadlines, notifications |
| Structured output | `instructor` + `pydantic` | Guaranteed JSON from Groq models |
| File upload | `python-multipart` | Resume file forwarding to ResumeAI (raw file proxy) |

### Frontend

| Component | Technology | Purpose |
|---|---|---|
| Framework | React 18 + Vite | Fast SPA setup |
| Styling | TailwindCSS | Utility-first styling |
| HTTP client | Axios | API calls |
| Calendar | `@fullcalendar/react` + `@fullcalendar/daygrid` | Deadline calendar view |
| Real-time | Native WebSocket API | Agent trace + notification push |
| Icons | `lucide-react` | Consistent icon set |
| Notifications | Custom React state + WebSocket | Bell badge + dropdown |

### Installation Commands

```bash
# Backend
pip install langgraph langchain langchain-community langchain-openai
pip install groq instructor pydantic
pip install tavily-python python-jobspy
pip install google-auth google-auth-oauthlib google-api-python-client
pip install sentence-transformers rapidfuzz
pip install apscheduler
pip install fastapi uvicorn python-multipart aiosqlite
pip install requests python-dotenv

# Frontend
npm create vite@latest opportuniq-frontend -- --template react
cd opportuniq-frontend
npm install axios tailwindcss @fullcalendar/react @fullcalendar/daygrid @fullcalendar/interaction lucide-react
npx tailwindcss init -p
```

---

## 4. User Flow Summary

The complete journey of a brand new user across all 14 steps.

| Step | Screen | User Action | System Response | Agent | LLM |
|---|---|---|---|---|---|
| 1 | Landing Page | Arrives at app | Static page with two CTAs | — | — |
| 2A | Resume Upload | Drops PDF | ResumeAI API → profile extracted | Profile Agent | ResumeAI API |
| 2B | Manual Form | Fills all fields | Profile saved to SQLite | Profile Agent | — |
| 3 | Profile Review | Completes amber fields, confirms | Validated profile saved | — | — |
| 4 | Dashboard (empty) | Views welcome state | Profile summary + Gmail prompt shown | — | — |
| 5 | Dashboard | Clicks "Find Opportunities" | LangGraph pipeline fires, agent trace opens | Discovery + Ranker | gpt-oss-120b |
| 5a | Agent Trace | (live stream) | Steps appear: JobSpy → Tavily → Dedup → Rank | Discovery + Ranker | gpt-oss-120b |
| 5b | Opportunity Feed | Results appear | 15 ranked cards with match % + deadline badge | — | — |
| 6 | Card Detail | Clicks a card | Detail drawer: full JD, skill gap breakdown | — | — |
| 7 | Card / Drawer | Clicks "Save" | Saved to tracker, status = "Not Applied" | — | — |
| 8 | Dashboard | Clicks "Connect Gmail" | OAuth flow completes, Guardian Agent runs | Guardian Agent | gpt-oss-20b |
| 8a | (auto) | Post-OAuth | 3-pass email fetch → deadlines extracted → calendar fills | Guardian Agent | gpt-oss-20b |
| 9 | Add Deadline form | Manually adds a deadline | Registry updated, 4 reminder jobs scheduled | Notifier Agent | — |
| 10 | Deadline Calendar | Views calendar | FullCalendar month view, colour-coded urgency | — | — |
| 10a | Calendar popup | Clicks an event | Detail popup: time remaining, notes, edit/delete | — | — |
| 11 | (background) | Reminder fires | Groq generates message → WebSocket push + SMTP | Notifier Agent | gpt-oss-120b |
| 11a | Bell dropdown | Clicks bell | Contextual reminder with skills reference shown | — | — |
| 12 | Saved Tab | Updates application status | Status dropdown updated in tracker | — | — |
| 13 | Settings | Re-scans Gmail | Guardian Agent re-runs 3-pass scan | Guardian Agent | gpt-oss-20b |
| 14 | Settings | Fires test reminder | Immediate notification + email for demo | Notifier Agent | gpt-oss-120b |

---

## 5. Page Specifications

### Page 1 — Landing Page `/`

**Purpose:** Convert first-time visitors into starting the onboarding flow.

**Layout:** Full-width hero with gradient background → 3 feature cards below → Footer.

**Components:**
- `Navbar` — logo + "Go to Dashboard" link
- `HeroSection` — headline, sub-headline, two CTA buttons ("Get Started with Resume" / "Set Up Manually")
- `FeatureCard × 3` — Discover / Match / Guard with icon + title + 2-line description
- `Footer` — project info, hackathon name

**API Calls:** None. Fully static.

**Navigation:**
- "Get Started with Resume" → `/onboarding/upload`
- "Set Up Manually" → `/onboarding/manual`

---

### Page 2 — Resume Upload `/onboarding/upload`

**Purpose:** Resume upload → Profile Agent forwards file to ResumeAI → transition to profile review.

**Layout:** Centred card. `StepIndicator` at top (Upload → Review → Discover).

**Components:**
- `StepIndicator` — 3-step progress bar (step 1 active)
- `FileDropzone` — drag-and-drop + click fallback. Accepts **PDF, DOC, DOCX**, max 5MB. Shows file name and format icon on selection.
- `UploadStateDisplay` — 4 states: idle → uploading (spinner, "Uploading your resume...") → parsing (spinner, "Extracting your profile with AI...") → success (green checkmark)
- `ErrorBanner` — shows on failure with "Try setting up manually →" link. Triggered by: unsupported file type, file size > 5MB, ResumeAI service error, timeout > 15s.

**Behaviour on upload:**
- Validate file type (PDF / DOC / DOCX) and size (≤5MB) client-side before sending
- `POST /api/profile/upload` — multipart/form-data with raw file
- Profile Agent receives file → forwards it unchanged to `ResumeAI POST /api/v1/profile/extract`
- ResumeAI handles all parsing and AI extraction internally
- On success → navigate to `/onboarding/review?profile_id={id}`
- On ResumeAI error (non-200, timeout >15s, `success: false`) → show `ErrorBanner` + auto-suggest manual form
- On unsupported file type from ResumeAI → show specific message: "This file format isn't supported. Please upload a PDF, DOC, or DOCX."

**Supported formats (enforced at both frontend and ResumeAI level):**
- `.pdf`
- `.doc`
- `.docx`

**API Calls:**
- `POST /api/profile/upload` (Profile Agent) → internally calls `POST /api/v1/profile/extract` (ResumeAI)

---

### Page 3 — Manual Profile Entry `/onboarding/manual`

**Purpose:** Structured form for manual profile creation (also the fallback if resume fails).

**Layout:** Single-column form card, centred. Sections: "About You" / "Your Goals" / "Preferences".

**Components:**
- `StepIndicator` (step 1 active)
- `TagInput` — for Skills and Target Roles. Type a skill and press Enter → renders as removable chip.
- `LocationAutocomplete` — text input with hardcoded Indian cities suggestions list
- `OpportunityTypeSelector` — four radio options with icons: Internship / Full-time / Hackathon / All

**Form Fields (all required unless noted):**

| Field | Type | Validation |
|---|---|---|
| Full Name | text | Required |
| Email | email | Required, valid email format |
| Year of Study | dropdown | 1st / 2nd / 3rd / 4th / Graduate / Fresher |
| Degree | text | Required |
| College | text | Required |
| Skills | TagInput | Min 1 tag |
| Target Roles | TagInput | Min 1 tag |
| Location Preference | text with suggestions | Required |
| Opportunity Type | radio | Required, one of 4 options |

**Behaviour:**
- Progress auto-saved to `localStorage` on every field change (prevents data loss)
- Submit button disabled until all required fields pass validation
- Inline error message under each invalid field on submit attempt
- On success → `/onboarding/review?profile_id={id}`

**API Calls:**
- `POST /api/profile/manual`

---

### Page 4 — Profile Review & Completion `/onboarding/review`

**Purpose:** Let users verify auto-extracted data, complete any missing fields, and confirm.

**Layout:** Two-column. Left: form. Right: live profile summary card (updates as user types).

**Components:**
- `ProfileReviewForm` — same fields as manual form, pre-populated from API response
- `FieldStatusBadge` — rendered next to each field:
  - Green ✓ badge — field confirmed by ResumeAI
  - Amber ⚠ badge + "Please complete" — field is null/empty
  - Orange ~ badge + "Please verify" — field extracted but confidence < 0.6
- `ProfileSummaryCard` — live right-panel showing name, skills chips, target roles, location
- `ConfirmButton` — stays disabled until all required fields are non-null

**Behaviour:**
- Loads profile via `GET /api/profile/{id}` on mount
- `null` fields rendered with amber left-border highlight
- "Confirm Profile & Find Opportunities" fires `PATCH /api/profile/{id}` → navigates to `/dashboard`
- "Edit Later" link navigates to dashboard but profile shows an "Incomplete" warning banner

**API Calls:**
- `GET /api/profile/{id}` on mount
- `PATCH /api/profile/{id}` on confirm

---

### Page 5 — Main Dashboard `/dashboard`

**Purpose:** Central hub. Opportunity feed, Gmail connection, deadline summary, notifications.

**Layout:**
- Fixed left sidebar (240px): logo, nav links, profile avatar
- Main content area: opportunity card grid
- Right panel (300px, collapsible): Gmail card + mini deadline calendar + agent trace panel
- Top navbar: search bar, bell icon + badge, profile menu

**Left Sidebar Navigation:**
- Discover (default, `/dashboard`)
- Saved (`/dashboard/saved`)
- Gap Advisor (`/dashboard/gap-analysis`) ← NEW
- Deadlines (`/dashboard/deadlines`)
- Notifications (`/dashboard/notifications`)
- Settings (`/dashboard/settings`)

**Key Components:**

`OpportunityCard`:
- Company letter-avatar (placeholder logo)
- Job title (bold), company name
- Platform badge — colour-coded by source (LinkedIn = blue, Naukri = teal, Unstop = purple, etc.)
- Location chip
- Match % circular badge — green >70%, amber 40–70%, red <40%
- Deadline badge — red "⏰ 2 days", amber "📅 5 days", green "✅ 15 days", grey "No deadline"
- "Also on: LinkedIn, Naukri" merge badge (when dedup merged sources)
- "Apply" button — opens URL in new tab
- "Save" bookmark icon — toggles saved state
- Click on card body → opens `OpportunityDetailDrawer`

`OpportunityDetailDrawer`:
- Slides in from the right (400px wide)
- Full job description text
- Skill match breakdown: list of required skills each showing ✓ (in profile) or ✗ (missing)
- "Apply Now" button
- "Save Opportunity" button
- "Add Deadline" quick-action → pre-fills deadline form with job title + company
- Close X button

`AgentTracePanel`:
- Appears when discovery pipeline is triggered
- Receives real-time events via WebSocket `ws://.../ws/agent-trace?session_id={id}`
- Renders a vertical timeline: agent name + status icon (⟳ running / ✓ done / ✗ error) + message + elapsed time
- Steps shown: Profile Agent → JobSpy Search → Tavily Search → Deduplication → Ranking → Complete
- Auto-hides 3 seconds after "Complete" event

`GmailConnectCard` (right panel, pre-connection):
- Shield icon + explanation: "Read-only. We never send emails."
- "Connect Gmail" button → initiates OAuth
- After connection: shows email address + last scan time + deadlines found count + "Re-scan" link

`DeadlineMiniCalendar` (right panel):
- 7-day week view showing upcoming deadlines as colour-coded dots
- Click any dot → navigates to `/dashboard/deadlines`

`NotificationBell` (top navbar):
- Shows red badge with unread count
- Click → dropdown: last 5 notifications with mark-read button
- "View all" → `/dashboard/notifications`

**API Calls on mount:**
- `GET /api/profile/{id}`
- `GET /api/opportunities?profile_id={id}` (load last session or empty)
- `GET /api/gmail/status`
- `GET /api/notifications?unread=true` (bell badge count)
- `GET /api/deadlines` (mini calendar)

**API Calls on user action:**
- `POST /api/opportunities/search` (Find Opportunities button)
- `WS /ws/agent-trace?session_id={id}` (agent trace stream)
- `GET /api/opportunities/{id}` (card click, load detail)
- `POST /api/saved/{opportunity_id}` (save button)

---

### Page 6 — Deadline Calendar `/dashboard/deadlines`

**Purpose:** Full calendar view of all registered deadlines with CRUD operations.

**Layout:** Full-width FullCalendar.js month view. Top-right: toggle (Month / List) + "Add Deadline" button.

**Components:**
- `FullCalendar` — `@fullcalendar/react` with `@fullcalendar/daygrid` plugin
- Event colours: red (≤3 days), amber (3–7 days), green (>7 days)
- `DeadlineDetailPopup` (appears on event click): title, organisation, event type, time remaining ("2 days 4 hours left"), notes, Edit + Delete buttons
- `DeadlineForm` (slide-in panel): title, organisation, date picker, time picker (default 23:59), event type dropdown, notes textarea
- `ViewToggle` — switches between Month calendar and List (chronological) view

**API Calls:**
- `GET /api/deadlines` on mount
- `POST /api/deadlines` — add new deadline
- `GET /api/deadlines/{id}` — load detail for popup
- `PUT /api/deadlines/{id}` — edit
- `DELETE /api/deadlines/{id}` — delete + cancel scheduler jobs

---

### Page 7 — Saved Opportunities & Tracker `/dashboard/saved`

**Purpose:** Track application progress for saved opportunities.

**Layout:** Stats row at top. Sortable, filterable table below.

**Stats Row:** 4 cards — Total Saved / Applied / Interview / Offers.

**Table Columns:** Company | Title | Platform | Status | Deadline | Saved At | Actions

**Status Dropdown (inline per row):**
- Not Applied (grey)
- Applied (blue)
- Interview Scheduled (amber)
- Offer Received (green)
- Rejected (red/muted)

**Filter Bar:** By status, by platform.

**API Calls:**
- `GET /api/saved` on mount
- `PATCH /api/saved/{id}` on status change
- `DELETE /api/saved/{id}` on remove

---

### Page 8 — Notifications `/dashboard/notifications`

**Purpose:** Full list of all past and pending notifications.

**Layout:** Two tabs (Unread / All). Sorted newest first. "Mark all read" in page header.

**NotificationCard:** Bell icon + type badge (Reminder / System) + message text + timestamp + "Mark read" button. Unread cards have light amber background.

**API Calls:**
- `GET /api/notifications`
- `PATCH /api/notifications/{id}/read`
- `PATCH /api/notifications/read-all`

---

### Page 9 — Profile & Settings `/dashboard/settings`

**Purpose:** Update profile, manage Gmail, configure reminders, test notifications.

**Layout:** Section accordion cards.

**Sections:**

1. **My Profile** — editable form (same as review page)
2. **Skills & Preferences** — TagInputs for skills and target roles
3. **Gmail Integration** — connected email, last scan timestamp, deadlines found count, "Re-scan Inbox" + "Disconnect" buttons
4. **Reminder Preferences** — 4 toggle switches (7 days / 3 days / 1 day / same day)
5. **Test Reminder** — select a deadline from dropdown → "Fire Test Reminder Now" button → immediate notification + email (no waiting for scheduled time)
6. **Danger Zone** — "Delete all my data" button with confirmation modal

**API Calls:**
- `GET /api/profile/{id}`, `PATCH /api/profile/{id}`
- `GET /api/gmail/status`, `POST /api/gmail/scan`, `DELETE /api/gmail/disconnect`
- `GET /api/settings/notifications`, `PUT /api/settings/notifications`
- `POST /api/notifications/test`

---

## 6. Agent Pipeline Design

### LangGraph State Object

```python
from typing import TypedDict, List, Optional
from datetime import datetime

class OpportunIQState(TypedDict):
    # Student profile
    profile_id: str
    name: str
    skills: List[str]
    target_roles: List[str]
    location: str
    opportunity_type: str          # internship | fulltime | hackathon | all

    # Discovery outputs
    raw_results: List[dict]        # from JobSpy + Tavily
    deduplicated_results: List[dict]
    ranked_results: List[dict]

    # Guardian outputs
    emails_fetched: List[dict]
    deadlines_extracted: List[dict]

    # Session metadata
    session_id: str
    current_agent: str
    errors: List[str]
```

### Agent Responsibilities

**① Profile Agent**
- Input: `profile_id`
- Action: Loads `StudentProfile` from SQLite
- Output: Populates `skills`, `target_roles`, `location`, `opportunity_type` in state
- Tool calls: SQLite read

**② Discovery Agent**
- Input: profile fields from state
- Action A (JobSpy): `scrape_jobs(site_name=["linkedin","naukri","indeed","glassdoor","google"], search_term="{role}", location="{location}", results_wanted=15, hours_old=168)`
- Action B (Tavily): 4–5 targeted queries for Unstop, Devfolio, HackerEarth, hackathons
- Groq gpt-oss-120b extracts structured `Opportunity` Pydantic object from each raw result
- Output: `raw_results` list in state

**③ Ranker Agent**
- Input: `raw_results`
- Action 1 — Deduplication:
  - Layer 1: SHA256 of normalised URL → skip if seen
  - Layer 2: `rapidfuzz.token_sort_ratio(title + company)` ≥ 85 → merge, keep richer record, append "Also on: X" badge
  - Layer 3: cosine similarity of `all-MiniLM-L6-v2` embedding ≥ 0.92 → merge
- Action 2 — Scoring: `combined = 0.7 × skill_cosine + 0.3 × (1 / (days_until_deadline + 1))`
- Action 3 — Filter expired (deadline in past)
- Output: `ranked_results` (top 15), saved to SQLite `opportunities` table

**⑤ Guardian Agent**
- Input: Gmail OAuth token from disk (`token.json`)
- Action 1 — 3-pass email fetch via Gmail API:
  - Pass 1: `q="subject:(interview OR shortlisted OR application OR offer OR submission OR test OR round OR accept OR congratulations OR selected OR rejected OR deadline OR schedule OR assessment) newer_than:60d"`
  - Pass 2: `q="from:(noreply@linkedin.com OR naukri.com OR unstop.com OR hackerearth.com OR internshala.com) newer_than:60d"`
  - Pass 3: `q="(\"last date\" OR \"closes on\" OR \"submit by\" OR \"before the deadline\" OR \"offer letter\" OR \"joining date\") newer_than:60d"`
- Action 2 — Dedup by `message_id`
- Action 3 — For each email: Groq gpt-oss-20b via Instructor extracts `DeadlineExtraction` Pydantic object
- Action 4 — confidence ≥ 0.6 → save to `deadline_registry`; < 0.6 → flag "Needs review"
- Output: `deadlines_extracted` list

**③ Gap Analysis Agent** *(new — added post Review 1)*
- Input: `profile_id` + one of: `target_role` (string), `job_description` (raw JD text), or `opportunity_id` (ID of a specific discovered opportunity)
- **Step 1 — Determine required skills** (deterministic, adapted from ResumeAI `gap-advisor.service.ts`):
  - If `opportunity_id` provided: load `opportunities.skills_required` from SQLite → use as required skills with frequency 1.0
  - If `job_description` provided: call Groq to extract `required_skills`, `preferred_skills`, `tech_stack` from JD text → assign frequencies 1.0 / 0.7 / 0.8 → cap at 20 skills
  - If `target_role` only: use a hardcoded skill taxonomy JSON (adapted from ResumeAI's `skills-taxonomy.json`) to map role → required skill clusters
- **Step 2 — Score student evidence** (deterministic, adapted from ResumeAI `gap-evidence.service.ts`):
  - Load `student_profiles.skills` from SQLite
  - For each required skill: assign evidence level
    - Level 0: skill not present in student skills list (case-insensitive, also checks synonyms)
    - Level 1: skill present in student skills list (listed but not "demonstrated")
    - Level 2: skill present AND appears in `target_roles` context (stronger signal)
  - Compute `priority`: high (evidence_level=0, frequency≥0.8), medium (level=0, freq<0.8 or level=1, freq≥0.8), low (otherwise)
  - Compute `learning_path_order` from taxonomy prerequisite ordering
- **Step 3 — LLM narrative synthesis** (adapted from ResumeAI gap-advisor prompt):
  - Pass deterministic gap list (max 8 skills) to Groq `openai/gpt-oss-120b` via Instructor
  - Prompt instructs LLM to: explain WHY each skill matters for the target role, suggest 3 concrete projects that address multiple gaps, recommend 5 specific learning resources with real URLs
  - LLM is explicitly told **not to invent new gaps** — it can only explain the provided list
  - Output validated against `GapAnalysisResult` Pydantic schema
- **Step 4 — Hallucination guard** (adapted from ResumeAI normalization step):
  - Remove any `missing_skills` LLM invented that are not in the deterministic list
  - Cap `missing_skills` at 8, `suggested_projects` at 3, `learning_resources` at 5
  - Verify all resource URLs start with `http`
  - Replace missing or very short `overall_assessment` with a default template
- **Step 5 — Persist**: save `GapAnalysisResult` to `gap_analyses` SQLite table
- Output: `GapAnalysisResult` JSON

**④ Ranker Agent** *(previously ③)*
- Input: `raw_results`
- Action 1 — Schedule 4 APScheduler `DateTrigger` jobs per deadline (7d, 3d, 1d, same-day 9 AM)
- Action 2 (when job fires) — Load deadline + student profile → Groq gpt-oss-120b generates contextual message
- Action 3 — Store notification in SQLite `notifications` table
- Action 4 — Push to WebSocket connection (bell badge update)
- Action 5 — Send SMTP email via Gmail relay

### Pydantic Schemas

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

# ── ResumeAI API response schema ──────────────────────────────────────────────
# Mirrors the exact JSON that POST /api/v1/profile/extract returns.
# The Profile Agent uses this only to parse and validate the response —
# it never calls Gemini or does any parsing itself.

class ResumeAIData(BaseModel):
    full_name: Optional[str]          # maps to → name
    year_of_study: Optional[str]      # e.g. "Third Year"
    graduation_year: Optional[int]    # e.g. 2027
    target_roles: Optional[List[str]] # e.g. ["SDE Intern"]
    skills: Optional[List[str]]       # e.g. ["Python", "FastAPI"]
    preferred_location: Optional[str] # maps to → location
    opportunity_type: Optional[str]   # e.g. "Internship"

class ResumeAIResponse(BaseModel):
    success: bool
    data: Optional[ResumeAIData]

# ── StudentProfile — owned by Profile Agent, stored in SQLite ─────────────────
# Field names here are OpportunIQ-internal. The mapping from ResumeAI fields
# is done in resume_service.py:map_resumeai_to_profile().

class StudentProfile(BaseModel):
    profile_id: str
    name: str                         # ← ResumeAI: full_name
    email: Optional[str]              # not returned by ResumeAI — user provides manually
    year_of_study: Optional[str]      # ← ResumeAI: year_of_study
    graduation_year: Optional[int]    # ← ResumeAI: graduation_year
    degree: Optional[str]             # not returned by ResumeAI — user provides manually
    college: Optional[str]            # not returned by ResumeAI — user provides manually
    skills: List[str]                 # ← ResumeAI: skills
    target_roles: List[str]           # ← ResumeAI: target_roles
    location: Optional[str]           # ← ResumeAI: preferred_location
    opportunity_type: Optional[str]   # ← ResumeAI: opportunity_type

# Fields NOT returned by ResumeAI (email, degree, college) will be null after
# extraction and will appear as amber "Please complete" fields on the review page.

class Opportunity(BaseModel):
    title: str
    company: str
    platform: str          # linkedin | naukri | unstop | devfolio | hackerearth | indeed | other
    url: str
    location: Optional[str]
    deadline: Optional[date]
    stipend_or_prize: Optional[str]
    eligibility: Optional[str]
    skills_required: List[str]
    description: Optional[str]

class DeadlineExtraction(BaseModel):
    has_deadline: bool
    organization: Optional[str]
    event_type: Optional[str]   # interview | submission | offer_acceptance | test | other
    deadline_date: Optional[str]
    deadline_time: Optional[str]
    action_required: Optional[str]
    confidence: float            # 0.0 to 1.0

class ReminderMessage(BaseModel):
    subject: str
    body: str
    urgency_level: str          # critical | high | medium

# ── Gap Analysis schemas ───────────────────────────────────────────────────────
# Adapted from ResumeAI gap-advisor.service.ts output schema.
# Re-implemented in Python for OpportunIQ's stack.

class EvidenceLevel(int):
    """
    0 = skill not found anywhere in student profile
    1 = skill listed in profile but not demonstrated via projects
    2 = skill appears in profile skills list or opportunity context
    3 = skill well-evidenced (multiple projects, high validation)
    In OpportunIQ: levels 2–3 are simplified to "in profile skills" vs "not in profile"
    since we don't have portfolio items. Level determined by skills list presence.
    """
    pass

class SkillEvidence(BaseModel):
    skill: str
    evidence_level: int             # 0 | 1 | 2 — simplified from ResumeAI's 0–3
    evidence_summary: str           # human-readable: "Not in your profile" etc.
    jd_frequency: float             # 1.0 = required, 0.8 = tech stack, 0.7 = preferred
    priority: str                   # high | medium | low
    learning_path_order: int        # 1 = learn first (taxonomy prerequisite order)
    cluster_name: Optional[str]     # skill cluster from taxonomy e.g. "Backend Infrastructure"

class MissingSkill(BaseModel):
    skill: str
    priority: str                   # high | medium | low
    reason: str                     # LLM-generated explanation (validated against deterministic data)
    evidence_level: int
    learning_path_order: int
    cluster_name: Optional[str]
    learning_resources: List[dict]  # [{ "resource": str, "url": str }]

class SuggestedProject(BaseModel):
    project_type: str
    description: str
    skills_addressed: List[str]     # capped at 3, only valid gap skills

class GapAnalysisResult(BaseModel):
    id: str
    profile_id: str
    target_role: str                # the student's target role (replaces career_goal)
    analysis_mode: str              # "profile_vs_role" | "profile_vs_jd" | "profile_vs_opportunity"
    overall_assessment: str         # LLM-generated summary (validated: min 20 chars)
    missing_skills: List[MissingSkill]  # capped at 8, only deterministic gaps
    suggested_projects: List[SuggestedProject]  # capped at 3
    evidence_data: List[SkillEvidence]           # full deterministic scoring
    jd_snippet: Optional[str]       # first 300 chars of JD if provided
    profile_snapshot: dict          # { skills_count, target_roles, opportunity_title }
    generated_at: str
    is_stale: bool                  # True if older than 7 days
```

---

## 7. Database Schema

**File:** `opportuniq.db` (SQLite, auto-created on first run)

```sql
-- Student profiles
-- Columns marked [ResumeAI] are populated from the ResumeAI API response.
-- Columns marked [Manual] must be entered by the user on the review page.
-- Both sets are stored here — Profile Agent owns this table exclusively.
CREATE TABLE IF NOT EXISTS student_profiles (
    id TEXT PRIMARY KEY,
    name TEXT,                -- [ResumeAI] full_name
    email TEXT,               -- [Manual] not extracted by ResumeAI
    year_of_study TEXT,       -- [ResumeAI] year_of_study  e.g. "Third Year"
    graduation_year INTEGER,  -- [ResumeAI] graduation_year  e.g. 2027
    degree TEXT,              -- [Manual] not extracted by ResumeAI
    college TEXT,             -- [Manual] not extracted by ResumeAI
    target_roles TEXT,        -- [ResumeAI] JSON array: ["SDE Intern"]
    skills TEXT,              -- [ResumeAI] JSON array: ["Python", "FastAPI"]
    location TEXT,            -- [ResumeAI] preferred_location
    opportunity_type TEXT,    -- [ResumeAI] e.g. "Internship"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Discovered opportunities
CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    profile_id TEXT,
    title TEXT,
    company TEXT,
    platform TEXT,
    url TEXT,
    url_hash TEXT,            -- SHA256 for dedup layer 1
    location TEXT,
    deadline DATE,
    stipend_or_prize TEXT,
    eligibility TEXT,
    skills_required TEXT,     -- JSON array
    description TEXT,
    also_on TEXT,             -- JSON array of merged platform names
    match_score REAL,
    urgency_score REAL,
    combined_score REAL,
    is_expired BOOLEAN DEFAULT FALSE,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deadline registry (from Gmail + manual)
CREATE TABLE IF NOT EXISTS deadline_registry (
    id TEXT PRIMARY KEY,
    profile_id TEXT,
    title TEXT NOT NULL,
    organization TEXT,
    deadline_datetime TIMESTAMP,
    event_type TEXT,
    action_required TEXT,
    notes TEXT,
    source TEXT NOT NULL,     -- gmail | manual
    gmail_message_id TEXT,
    needs_review BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Saved opportunities + tracker
CREATE TABLE IF NOT EXISTS saved_opportunities (
    id TEXT PRIMARY KEY,
    profile_id TEXT,
    opportunity_id TEXT,
    status TEXT DEFAULT 'Not Applied',
    -- Not Applied | Applied | Interview Scheduled | Offer Received | Rejected
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gap analysis results
-- One row per (profile_id, opportunity_id) pair for opportunity-specific analyses.
-- One row per profile_id with opportunity_id = NULL for role-level analyses.
-- Adapted from ResumeAI gap_analyses table — simplified for SQLite and OpportunIQ data model.
CREATE TABLE IF NOT EXISTS gap_analyses (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    opportunity_id TEXT,              -- NULL if analysis is against target_role only
    target_role TEXT NOT NULL,        -- role being analysed against (replaces career_goal)
    analysis_mode TEXT NOT NULL,      -- profile_vs_role | profile_vs_jd | profile_vs_opportunity
    overall_assessment TEXT,
    missing_skills TEXT,              -- JSON array of MissingSkill objects
    suggested_projects TEXT,          -- JSON array of SuggestedProject objects
    evidence_data TEXT,               -- JSON array of SkillEvidence objects
    jd_snippet TEXT,                  -- first 300 chars of JD if used
    profile_snapshot TEXT,            -- JSON: { skills_count, target_roles }
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    profile_id TEXT,
    deadline_id TEXT,
    subject TEXT,
    message TEXT,
    channel TEXT,             -- dashboard | email
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. API Endpoint Registry

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| POST | `/api/profile/upload` | Upload resume PDF → ResumeAI API | multipart `file` | `{ profile_id, profile, missing_fields[] }` |
| POST | `/api/profile/manual` | Create profile manually | `StudentProfile` JSON | `{ profile_id, profile }` |
| GET | `/api/profile/{id}` | Fetch profile | — | `StudentProfile` |
| PATCH | `/api/profile/{id}` | Update profile fields | partial `StudentProfile` | `{ success, profile }` |
| POST | `/api/opportunities/search` | Trigger LangGraph discovery | `{ profile_id }` | `{ session_id }` |
| GET | `/api/opportunities` | Fetch ranked results | `?session_id=X` or `?profile_id=X` | `Opportunity[]` |
| GET | `/api/opportunities/{id}` | Fetch single opportunity | — | `Opportunity` |
| POST | `/api/saved/{opportunity_id}` | Save an opportunity | — | `{ saved_id }` |
| GET | `/api/saved` | Get all saved | `?profile_id=X` | `SavedOpportunity[]` |
| PATCH | `/api/saved/{id}` | Update tracker status | `{ status }` | `{ success }` |
| DELETE | `/api/saved/{id}` | Remove from saved | — | `{ success }` |
| GET | `/api/gmail/connect` | Initiate OAuth flow | — | Redirect to Google |
| GET | `/api/gmail/callback` | OAuth callback handler | `?code=X` | Redirect to `/dashboard` |
| GET | `/api/gmail/status` | Check Gmail connection | — | `{ connected, last_scanned, deadlines_found }` |
| POST | `/api/gmail/scan` | Re-trigger inbox scan | `{ profile_id }` | `{ session_id }` |
| DELETE | `/api/gmail/disconnect` | Revoke Gmail token | — | `{ success }` |
| POST | `/api/deadlines` | Add manual deadline | `DeadlineEntry` JSON | `{ deadline_id, reminders_scheduled[] }` |
| GET | `/api/deadlines` | Get all deadlines | `?profile_id=X` | `Deadline[]` |
| GET | `/api/deadlines/{id}` | Get single deadline | — | `Deadline` |
| PUT | `/api/deadlines/{id}` | Edit deadline | `DeadlineEntry` | `{ success }` |
| DELETE | `/api/deadlines/{id}` | Delete + cancel reminders | — | `{ success }` |
| GET | `/api/notifications` | Get notifications | `?unread=true` optional | `Notification[]` |
| PATCH | `/api/notifications/{id}/read` | Mark one as read | — | `{ success }` |
| PATCH | `/api/notifications/read-all` | Mark all as read | — | `{ success }` |
| POST | `/api/notifications/test` | Fire immediate test reminder | `{ deadline_id }` | `{ success, message }` |
| GET | `/api/settings/notifications` | Get reminder preferences | — | `{ r_7d, r_3d, r_1d, r_same_day }` |
| PUT | `/api/settings/notifications` | Update reminder preferences | preference booleans | `{ success }` |
| WS | `/ws/agent-trace` | Stream agent step events | `?session_id=X` | Event JSON stream |
| POST | `/api/gap-analysis/run` | Run gap analysis for a profile vs role or JD | `{ profile_id, target_role?, job_description?, opportunity_id? }` | `GapAnalysisResult` |
| GET | `/api/gap-analysis/{profile_id}` | Get latest persisted gap analysis for profile | — | `GapAnalysisResult` (with `is_stale` flag if >7 days old) |
| GET | `/api/gap-analysis/{profile_id}/for-opportunity/{opportunity_id}` | Get opportunity-specific gap analysis | — | `GapAnalysisResult` or 404 if not yet run |

---

## 9. Build Plan — Step by Step

> **How to read this:** Each task block has a title, what exactly to build, what to install/set up, and what "done" looks like. All three team members can work in parallel once the project is initialised. Tasks are ordered so that the backend and frontend can be built simultaneously from Hour 4 onwards without blocking each other.

---

### STEP 0 — Pre-Hackathon Setup *(Do this before the event starts)*

**Everyone completes this independently on their own machine.**

See [Section 10](#10-pre-hackathon-checklist-step-0) for the full checklist.

---

### STEP 1 — Project Initialisation *(Hours 0–1, all three together)*

All three members do this simultaneously on the same codebase. One person creates the repo and shares it. Others clone.

**Person A — Backend skeleton**
```
opportuniq-backend/
├── main.py              # FastAPI app entry point
├── database.py          # aiosqlite connection + schema init
├── models.py            # All Pydantic schemas
├── agents/
│   ├── __init__.py
│   ├── graph.py         # LangGraph StateGraph definition
│   ├── profile_agent.py
│   ├── discovery_agent.py
│   ├── gap_analysis_agent.py  # ← NEW: Gap Analysis Agent
│   ├── ranker_agent.py
│   ├── guardian_agent.py
│   └── notifier_agent.py
├── routers/
│   ├── profile.py
│   ├── opportunities.py
│   ├── deadlines.py
│   ├── gmail.py
│   ├── notifications.py
│   ├── gap_analysis.py        # ← NEW: Gap Analysis routes
│   └── settings.py
├── services/
│   ├── jobspy_service.py
│   ├── tavily_service.py
│   ├── gmail_service.py
│   ├── groq_service.py
│   ├── ranker_service.py
│   ├── scheduler_service.py
│   └── gap_analysis_service.py  # ← NEW: deterministic scoring + taxonomy
├── data/
│   └── skills_taxonomy.json     # ← NEW: adapted from ResumeAI skills-taxonomy.json
├── .env                 # All API keys (never commit)
└── requirements.txt
```

```python
# main.py — starter template
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from services.scheduler_service import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="OpportunIQ API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

# Import and include all routers here
```

**Person B — Frontend skeleton**
```bash
npm create vite@latest opportuniq-frontend -- --template react
cd opportuniq-frontend
npm install axios tailwindcss @fullcalendar/react @fullcalendar/daygrid @fullcalendar/interaction lucide-react
npx tailwindcss init -p
```

```
opportuniq-frontend/src/
├── pages/
│   ├── Landing.jsx
│   ├── ResumeUpload.jsx
│   ├── ManualForm.jsx
│   ├── ProfileReview.jsx
│   ├── Dashboard.jsx
│   ├── DeadlineCalendar.jsx
│   ├── SavedOpportunities.jsx
│   ├── GapAnalysisPage.jsx       ← NEW
│   ├── Notifications.jsx
│   └── Settings.jsx
├── components/
│   ├── Navbar.jsx
│   ├── Sidebar.jsx
│   ├── OpportunityCard.jsx
│   ├── OpportunityDetailDrawer.jsx
│   ├── GapAnalysisCard.jsx       ← NEW
│   ├── AgentTracePanel.jsx
│   ├── GmailConnectCard.jsx
│   ├── DeadlineMiniCalendar.jsx
│   ├── NotificationBell.jsx
│   ├── DeadlineForm.jsx
│   ├── TagInput.jsx
│   ├── StepIndicator.jsx
│   └── FieldStatusBadge.jsx
├── api/
│   └── client.js        # Axios instance with base URL
├── App.jsx              # Router setup
└── main.jsx
```

**Person C — Database + Models**
```python
# database.py
import aiosqlite, uuid
DB_PATH = "opportuniq.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Paste all CREATE TABLE IF NOT EXISTS statements from Section 7
        await db.commit()

# models.py — paste all Pydantic schemas from Section 6
```

**Done when:** Backend starts with `uvicorn main:app --reload` without errors. Frontend starts with `npm run dev` without errors. Database file `opportuniq.db` is created with all 5 tables.

---

### STEP 2 — Profile System *(Hours 1–4)*

**Person A — Profile API routes**

Build `routers/profile.py`:
- `POST /api/profile/upload` — receive raw file (PDF/DOC/DOCX) → forward it unchanged to ResumeAI via `resume_service.forward_to_resumeai()` → parse `ResumeAIResponse` Pydantic schema → call `map_resumeai_to_profile()` to convert field names → identify missing fields (null values) → save `StudentProfile` to SQLite → return `{ profile_id, profile, missing_fields[] }`. **Do not use PyMuPDF here. Do not extract text here. ResumeAI owns all of that.**
- `POST /api/profile/manual` — validate `StudentProfile` body → generate UUID as profile_id → save to SQLite → return profile
- `GET /api/profile/{id}` — fetch from SQLite → return profile
- `PATCH /api/profile/{id}` — partial update → update `updated_at` → return updated profile

**Person B — Onboarding pages**

Build `ResumeUpload.jsx`:
- `FileDropzone` with `onDrop` handler
- Validate PDF + size before calling API
- Show 4 states (idle / uploading / parsing / success)
- On success: `navigate('/onboarding/review?profile_id=' + data.profile_id)`
- On error: show `ErrorBanner`

Build `ManualForm.jsx`:
- All form fields with validation
- `TagInput` component: controlled input → press Enter → push to array state → render chips with × button
- `localStorage` save on every change
- Submit → `POST /api/profile/manual` → navigate to review

Build `ProfileReview.jsx`:
- `GET /api/profile/{id}` on mount
- Pre-fill all fields
- `FieldStatusBadge`: green if value non-null and confident, amber if null, orange if low confidence
- Disable "Confirm" button until all required fields non-null
- On confirm: `PATCH /api/profile/{id}` → navigate to dashboard

**Person C — ResumeAI API integration**

Build `services/resume_service.py`:

```python
import httpx
import os
import uuid
from models import ResumeAIResponse, StudentProfile

# ResumeAI is a separate TypeScript/Node.js microservice.
# The correct endpoint is POST /api/v1/profile/extract
# We forward the raw file as multipart/form-data — no parsing done here.

RESUMEAI_BASE_URL = os.getenv("RESUMEAI_API_URL")  # e.g. https://resumeai.yourdomain.com
RESUMEAI_ENDPOINT = f"{RESUMEAI_BASE_URL}/api/v1/profile/extract"


async def forward_to_resumeai(file_bytes: bytes, filename: str, content_type: str) -> ResumeAIResponse:
    """
    Forward the raw uploaded file to ResumeAI.
    ResumeAI handles all parsing, text extraction, and Gemini AI calls.
    We only receive and validate the structured JSON response.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                RESUMEAI_ENDPOINT,
                files={"resume": (filename, file_bytes, content_type)},
                # Include auth header if ResumeAI requires it
                headers={"x-api-key": os.getenv("RESUMEAI_API_KEY", "")}
            )
            response.raise_for_status()
            return ResumeAIResponse(**response.json())
        except httpx.TimeoutException:
            # Return failure — Profile Agent will fall back to manual form
            return ResumeAIResponse(success=False, data=None)
        except httpx.HTTPStatusError as e:
            print(f"ResumeAI returned HTTP {e.response.status_code}: {e.response.text}")
            return ResumeAIResponse(success=False, data=None)
        except Exception as e:
            print(f"Unexpected ResumeAI error: {e}")
            return ResumeAIResponse(success=False, data=None)


def map_resumeai_to_profile(resumeai_data: dict, profile_id: str = None) -> dict:
    """
    Map ResumeAI response field names to OpportunIQ's internal StudentProfile field names.

    ResumeAI field       →  StudentProfile field
    ─────────────────────────────────────────────
    full_name            →  name
    year_of_study        →  year_of_study
    graduation_year      →  graduation_year
    target_roles         →  target_roles
    skills               →  skills
    preferred_location   →  location
    opportunity_type     →  opportunity_type

    Fields NOT in ResumeAI response (must be completed manually):
    - email       → set to None
    - degree      → set to None
    - college     → set to None
    """
    mapped = {
        "profile_id": profile_id or str(uuid.uuid4()),
        "name":             resumeai_data.get("full_name"),
        "email":            None,                                    # Manual — ResumeAI doesn't extract this
        "year_of_study":    resumeai_data.get("year_of_study"),
        "graduation_year":  resumeai_data.get("graduation_year"),
        "degree":           None,                                    # Manual — ResumeAI doesn't extract this
        "college":          None,                                    # Manual — ResumeAI doesn't extract this
        "skills":           resumeai_data.get("skills") or [],
        "target_roles":     resumeai_data.get("target_roles") or [],
        "location":         resumeai_data.get("preferred_location"),
        "opportunity_type": resumeai_data.get("opportunity_type"),
    }

    # Identify fields that are null or empty — these become amber on the review page
    required_fields = ["name", "skills", "target_roles", "location", "opportunity_type"]
    missing_fields = [
        field for field in required_fields
        if not mapped.get(field)
    ]
    # Always flag these as missing since ResumeAI never returns them
    always_manual = ["email", "degree", "college"]

    return {
        "profile": mapped,
        "missing_fields": missing_fields + always_manual
    }
```

**Done when:** Upload a real PDF/DOC/DOCX → Profile Agent forwards file to ResumeAI `POST /api/v1/profile/extract` → receives `{ success: true, data: { full_name, skills, ... } }` → field mapping runs → profile saved to SQLite → `missing_fields` includes `["email", "degree", "college"]` at minimum → review page renders green badges on ResumeAI-filled fields and amber badges on manual-required fields → confirm navigates to dashboard with profile loaded.

---

### STEP 3 — Discovery Pipeline *(Hours 4–12)*

This is the most important step. Build and test it carefully before moving on.

**Person A — JobSpy + Tavily service**

Build `services/jobspy_service.py`:
```python
from jobspy import scrape_jobs
import pandas as pd

def search_jobs(role: str, location: str, opportunity_type: str) -> list[dict]:
    site_names = ["linkedin", "naukri", "indeed", "glassdoor", "google"]
    try:
        jobs = scrape_jobs(
            site_name=site_names,
            search_term=role,
            location=location,
            results_wanted=15,
            hours_old=168,          # 1 week
        )
        return jobs.to_dict('records') if not jobs.empty else []
    except Exception as e:
        print(f"JobSpy error: {e}")
        return []
```

Build `services/tavily_service.py`:
```python
from tavily import TavilyClient
import os

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def search_hackathons_and_portals(role: str, skills: list[str]) -> list[dict]:
    queries = [
        f"{role} hackathon 2025 site:unstop.com",
        f"machine learning hackathon site:devfolio.co",
        f"{role} internship site:hackerearth.com",
        f"{' '.join(skills[:3])} internship site:internshala.com",
        f"{role} fresher jobs company careers portal India 2025",
    ]
    results = []
    for q in queries:
        try:
            r = client.search(q, search_depth="basic", max_results=5)
            results.extend(r.get("results", []))
        except Exception as e:
            print(f"Tavily error for query '{q}': {e}")
    return results
```

**Person B — Groq extraction service**

Build `services/groq_service.py`:
```python
from groq import Groq
import instructor
from models import Opportunity, DeadlineExtraction, ReminderMessage
import os

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
client_120b = instructor.from_openai(groq_client, mode=instructor.Mode.TOOLS)

def extract_opportunity(raw_text: str) -> Opportunity:
    return client_120b.create(
        model="openai/gpt-oss-120b",
        response_model=Opportunity,
        messages=[{
            "role": "user",
            "content": f"Extract structured job/internship/hackathon details from this text. Return null for missing fields.\n\n{raw_text[:3000]}"
        }]
    )

def extract_deadline(email_text: str) -> DeadlineExtraction:
    return client_120b.create(
        model="openai/gpt-oss-20b",
        response_model=DeadlineExtraction,
        messages=[{
            "role": "user",
            "content": f"Check if this email contains an application deadline, interview date, submission deadline, or offer acceptance date. Extract if present.\n\n{email_text[:2000]}"
        }]
    )

def generate_reminder(profile_name: str, skills: list, deadline_title: str,
                       deadline_dt: str, days_left: int) -> ReminderMessage:
    return client_120b.create(
        model="openai/gpt-oss-120b",
        response_model=ReminderMessage,
        messages=[{
            "role": "user",
            "content": f"Write a short, warm, personalised deadline reminder for {profile_name}. Deadline: {deadline_title} in {days_left} days ({deadline_dt}). Relevant skills from their profile: {', '.join(skills[:5])}. Keep it under 100 words. Be encouraging, not alarming."
        }]
    )
```

**Person C — Ranker Agent (dedup + scoring)**

Build `services/ranker_service.py`:
```python
import hashlib
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')

def normalise_url(url: str) -> str:
    # Strip UTM params, trailing slashes, query strings
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment="")).rstrip("/")

def deduplicate(results: list[dict]) -> list[dict]:
    seen_hashes = set()
    seen_pairs = []
    deduplicated = []

    for item in results:
        # Layer 1: URL hash
        url_hash = hashlib.sha256(normalise_url(item.get("url","")).encode()).hexdigest()
        if url_hash in seen_hashes:
            continue
        seen_hashes.add(url_hash)

        # Layer 2: Fuzzy title + company match
        pair = f"{item.get('title','')} {item.get('company','')}".lower()
        is_dup = False
        for existing_pair, existing_idx in seen_pairs:
            if fuzz.token_sort_ratio(pair, existing_pair) >= 85:
                # Merge: append source to "also_on" of existing
                src = item.get("platform","")
                if src and src not in deduplicated[existing_idx].get("also_on", []):
                    deduplicated[existing_idx].setdefault("also_on", []).append(src)
                is_dup = True
                break
        if is_dup:
            continue
        seen_pairs.append((pair, len(deduplicated)))
        deduplicated.append(item)

    return deduplicated

def score(opportunity: dict, student_skills: list[str]) -> float:
    opp_skills = opportunity.get("skills_required", [])
    if not opp_skills or not student_skills:
        skill_score = 0.0
    else:
        opp_emb = model.encode([" ".join(opp_skills)])[0]
        stu_emb = model.encode([" ".join(student_skills)])[0]
        skill_score = float(cosine_similarity([opp_emb], [stu_emb])[0][0])

    deadline = opportunity.get("deadline")
    if deadline:
        from datetime import date
        days = max((deadline - date.today()).days, 0)
        urgency = 1 / (days + 1)
    else:
        urgency = 0.1

    return 0.7 * skill_score + 0.3 * urgency
```

**Done when:** Trigger `POST /api/opportunities/search` → backend runs JobSpy + Tavily → results extracted by Groq → deduplicated → ranked → returned as JSON array. Test by printing ranked results to console. Confirm dedup removes duplicates by checking a known cross-platform listing.

---

---

### STEP 3.5 — Gap Analysis Agent *(Hours 8–14, parallel with Step 4)*

> **Context:** This step implements the Gap Analysis Agent — adapted from ResumeAI's `gap-advisor.service.ts`, `gap-evidence.service.ts`, and `gap-taxonomy.service.ts` — natively in Python. The core methodology is preserved: deterministic evidence scoring first, then LLM narrative synthesis, then hallucination guard. The code is new Python; the logic is from ResumeAI.

---

**Person A — `routers/gap_analysis.py` + agent wiring**

Build `routers/gap_analysis.py` with 3 endpoints:

`POST /api/gap-analysis/run`
- Accept body: `{ "profile_id": str, "target_role": str (optional), "job_description": str (optional), "opportunity_id": str (optional) }`
- Validate: at least one of `target_role`, `job_description`, or `opportunity_id` must be provided
- If `job_description` provided and len < 50 chars → return 422 "Job description must be at least 50 characters"
- Call `gap_analysis_agent.run(profile_id, target_role, job_description, opportunity_id)`
- Return `GapAnalysisResult` JSON
- Emit agent trace events via WebSocket during processing

`GET /api/gap-analysis/{profile_id}`
- Fetch latest persisted `gap_analyses` row for `profile_id` where `opportunity_id IS NULL`
- If no row exists → return 404 with message "No gap analysis found. Run POST /api/gap-analysis/run first."
- If `generated_at` is older than 7 days → add `is_stale: true` to response
- Return `GapAnalysisResult` JSON

`GET /api/gap-analysis/{profile_id}/for-opportunity/{opportunity_id}`
- Fetch `gap_analyses` row where both `profile_id` AND `opportunity_id` match
- Return `GapAnalysisResult` or 404

---

**Person B — `GapAnalysisPage.jsx` + `GapAnalysisCard.jsx`**

Build `pages/GapAnalysisPage.jsx` — accessible from the sidebar as "Gap Advisor":

**Two tabs (mirroring ResumeAI's Gap Advisor page):**

Tab 1 — "My Target Role":
- Load existing analysis via `GET /api/gap-analysis/{profile_id}` on mount
- If none exists → empty state: "Run your first gap analysis" button
- If stale → amber banner: "This analysis is 8+ days old — re-run for fresh results"
- "Re-run Analysis" button → `POST /api/gap-analysis/run` with just `{ profile_id, target_role: profile.target_roles[0] }`

Tab 2 — "Against a Job Description":
- Textarea for pasting a JD (minimum 50 characters enforced client-side)
- "Analyse" button → `POST /api/gap-analysis/run` with `{ profile_id, job_description: pastedJD }`
- Results shown immediately below — clearly labelled "This analysis is not saved"

Build `components/GapAnalysisCard.jsx` — renders a `GapAnalysisResult`:
- **Profile Snapshot section**: total skills count, target roles, when generated
- **Overall Assessment**: paragraph text
- **Skills to Close the Gap**: list of `missing_skills`, each card showing:
  - Skill name + priority badge (red = high, amber = medium, grey = low)
  - Evidence badge: "Not in your profile" (evidence_level=0) or "Listed but not demonstrated" (level=1)
  - Reason text (LLM-generated)
  - Learning resources as clickable links
- **Suggested Projects**: 3 project cards, each showing type, description, and skills addressed as tags
- "Run Again" button at the bottom

Also add a **"View Gap Analysis" button** on `OpportunityDetailDrawer.jsx`:
- Calls `GET /api/gap-analysis/{profile_id}/for-opportunity/{opportunity_id}`
- If 404 → shows "Run Gap Analysis for this role" button → triggers `POST /api/gap-analysis/run` with `opportunity_id`
- Once complete → renders `GapAnalysisCard` inline in the drawer

---

**Person C — `services/gap_analysis_service.py` + `agents/gap_analysis_agent.py` + `data/skills_taxonomy.json`**

**Build `data/skills_taxonomy.json`** — adapted from ResumeAI's `skills-taxonomy.json`. This is a hardcoded JSON file. Build it with at least these role → skill cluster mappings:

```json
{
  "role_patterns": {
    "sde intern": ["Python", "Data Structures", "Algorithms", "Git", "SQL", "Problem Solving"],
    "ml intern": ["Python", "Machine Learning", "NumPy", "Pandas", "Scikit-learn", "Statistics"],
    "data analyst": ["SQL", "Python", "Excel", "Data Visualization", "Statistics", "Pandas"],
    "frontend intern": ["HTML", "CSS", "JavaScript", "React", "Git", "Responsive Design"],
    "backend intern": ["Python", "REST APIs", "SQL", "FastAPI", "Git", "Authentication"],
    "full stack": ["React", "Node.js", "SQL", "REST APIs", "Git", "HTML", "CSS"],
    "devops": ["Linux", "Docker", "CI/CD", "Git", "Cloud Platforms", "Shell Scripting"],
    "data engineer": ["Python", "SQL", "ETL", "Apache Spark", "Cloud Platforms", "Data Warehousing"]
  },
  "skill_clusters": {
    "Python": "Core Programming",
    "Data Structures": "Core Programming",
    "Algorithms": "Core Programming",
    "Machine Learning": "AI/ML",
    "SQL": "Data",
    "React": "Frontend",
    "Docker": "DevOps"
  },
  "prerequisites": {
    "Machine Learning": ["Python", "NumPy", "Statistics"],
    "React": ["HTML", "CSS", "JavaScript"],
    "FastAPI": ["Python", "REST APIs"]
  },
  "skill_synonyms": {
    "js": "JavaScript",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "nlp": "Natural Language Processing"
  }
}
```

Add more roles and skills as time permits. The more complete this is, the better the career-goal mode results.

**Build `services/gap_analysis_service.py`** — three functions (adapted from ResumeAI's deterministic services):

```python
import json, uuid, os
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from models import GapAnalysisResult, MissingSkill, SuggestedProject, SkillEvidence

# Load taxonomy once
with open("data/skills_taxonomy.json") as f:
    TAXONOMY = json.load(f)

model = SentenceTransformer('all-MiniLM-L6-v2')  # already pre-downloaded


def determine_required_skills(
    target_role: str | None,
    jd_extracted: dict | None,     # from groq_service.extract_jd_skills() if JD provided
    opportunity_skills: list | None  # from opportunity.skills_required if opportunity_id provided
) -> list[dict]:
    """
    Returns list of { skill, frequency } pairs.
    Priority: opportunity_skills > jd_extracted > taxonomy mapping.
    Adapted from ResumeAI gap-advisor.service.ts determineRequiredSkills().
    """
    if opportunity_skills:
        # Direct opportunity mode: required=1.0
        return [{"skill": s, "frequency": 1.0} for s in opportunity_skills[:20]]

    if jd_extracted:
        # JD comparison mode: adapted from ResumeAI jd_comparison mode
        skills = []
        for s in jd_extracted.get("required_skills", []):
            skills.append({"skill": s, "frequency": 1.0})
        for s in jd_extracted.get("tech_stack", []):
            if s not in [x["skill"] for x in skills]:
                skills.append({"skill": s, "frequency": 0.8})
        for s in jd_extracted.get("preferred_skills", []):
            if s not in [x["skill"] for x in skills]:
                skills.append({"skill": s, "frequency": 0.7})
        return skills[:20]

    if target_role:
        # Career-goal / taxonomy mode
        role_key = target_role.lower().strip()
        matched = None
        for pattern in TAXONOMY["role_patterns"]:
            if pattern in role_key or role_key in pattern:
                matched = pattern
                break
        if matched:
            return [{"skill": s, "frequency": 1.0}
                    for s in TAXONOMY["role_patterns"][matched]]
        # Fallback: generic professional skills
        return [{"skill": s, "frequency": 0.8}
                for s in ["Python", "Git", "SQL", "Communication", "Problem Solving"]]
    return []


def score_student_evidence(
    required_skills: list[dict],
    student_skills: list[str]
) -> list[SkillEvidence]:
    """
    Deterministic evidence scoring. Adapted from ResumeAI gap-evidence.service.ts.
    Evidence levels simplified for OpportunIQ's data model (no portfolio_items):
      0 = not in student skills list and no semantic match
      1 = in student skills list (listed)
      2 = in student skills and is a primary skill (high confidence)
    """
    student_lower = [s.lower() for s in student_skills]
    synonyms = TAXONOMY.get("skill_synonyms", {})
    evidence_list = []

    for req in required_skills:
        skill = req["skill"]
        freq = req["frequency"]
        skill_lower = skill.lower()

        # Check synonyms
        canonical = synonyms.get(skill_lower, skill_lower)

        # Evidence level determination
        if canonical in student_lower or skill_lower in student_lower:
            evidence_level = 1  # listed in profile
            evidence_summary = f"'{skill}' is listed in your profile skills"
        else:
            # Semantic similarity check (optional enrichment)
            if student_skills:
                skill_emb = model.encode([skill])[0]
                stu_emb = model.encode([" ".join(student_skills)])[0]
                sim = float(cosine_similarity([skill_emb], [stu_emb])[0][0])
            else:
                sim = 0.0

            if sim > 0.75:
                evidence_level = 1  # semantically similar to profile content
                evidence_summary = f"'{skill}' is similar to skills in your profile"
            else:
                evidence_level = 0
                evidence_summary = f"'{skill}' was not found in your profile"

        # Priority: high if missing (level=0) and frequently required, else medium/low
        if evidence_level == 0 and freq >= 0.8:
            priority = "high"
        elif evidence_level == 0 and freq < 0.8:
            priority = "medium"
        elif evidence_level == 1 and freq >= 0.9:
            priority = "medium"
        else:
            priority = "low"

        cluster = TAXONOMY["skill_clusters"].get(skill, "General")

        # Learning path order from prerequisites
        prereqs = TAXONOMY.get("prerequisites", {})
        order = 1 if skill not in prereqs else 2  # skills with prerequisites come later

        evidence_list.append(SkillEvidence(
            skill=skill,
            evidence_level=evidence_level,
            evidence_summary=evidence_summary,
            jd_frequency=freq,
            priority=priority,
            learning_path_order=order,
            cluster_name=cluster
        ))

    # Sort: high priority first, then by frequency
    evidence_list.sort(key=lambda x: (x.priority != "high", x.priority != "medium", -x.jd_frequency))
    return evidence_list


def normalize_llm_output(
    llm_result: dict,
    deterministic_gaps: list[SkillEvidence]
) -> tuple[list[MissingSkill], list[SuggestedProject]]:
    """
    Hallucination guard. Adapted from ResumeAI normalization step.
    Removes LLM-invented skills. Caps lists. Validates URLs.
    """
    valid_gap_skills = {e.skill.lower() for e in deterministic_gaps if e.evidence_level == 0}

    # Filter missing_skills to only those in deterministic list
    missing = []
    for ms in llm_result.get("missing_skills", [])[:8]:
        if ms.get("skill", "").lower() in valid_gap_skills:
            # Validate learning resources
            resources = [
                r for r in ms.get("learning_resources", [])[:5]
                if r.get("url", "").startswith("http")
            ]
            # Use deterministic evidence for priority and order
            det = next((e for e in deterministic_gaps if e.skill.lower() == ms["skill"].lower()), None)
            missing.append(MissingSkill(
                skill=ms["skill"],
                priority=det.priority if det else ms.get("priority", "medium"),
                reason=ms.get("reason") or f"'{ms['skill']}' is required for this role and not present in your profile.",
                evidence_level=det.evidence_level if det else 0,
                learning_path_order=det.learning_path_order if det else 1,
                cluster_name=det.cluster_name if det else None,
                learning_resources=resources
            ))

    # Filter suggested projects: only reference valid gap skills
    projects = []
    for sp in llm_result.get("suggested_projects", [])[:3]:
        valid_addressed = [
            s for s in sp.get("skills_addressed", [])
            if s.lower() in valid_gap_skills
        ][:5]
        projects.append(SuggestedProject(
            project_type=sp.get("project_type", "Project"),
            description=sp.get("description", ""),
            skills_addressed=valid_addressed
        ))

    return missing, projects
```

**Build `agents/gap_analysis_agent.py`** — the orchestrator:

```python
import uuid, json
from datetime import datetime
from services.gap_analysis_service import (
    determine_required_skills, score_student_evidence, normalize_llm_output
)
from services.groq_service import run_gap_analysis_llm, extract_jd_skills
from models import GapAnalysisResult

async def run(profile_id: str, target_role: str = None,
              job_description: str = None, opportunity_id: str = None,
              session_id: str = None) -> GapAnalysisResult:
    from main import emit_trace
    import aiosqlite
    from database import DB_PATH

    await emit_trace(session_id, "Gap Analysis Agent", "running", "Loading student profile...")

    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Load profile
        row = await (await db.execute(
            "SELECT skills, target_roles FROM student_profiles WHERE id = ?", [profile_id]
        )).fetchone()
        if not row:
            raise ValueError("Profile not found")
        student_skills = json.loads(row[0] or "[]")
        target_roles = json.loads(row[1] or "[]")
        effective_role = target_role or (target_roles[0] if target_roles else "Software Engineer")

        # 2. Load opportunity skills if opportunity_id provided
        opp_skills = None
        if opportunity_id:
            opp = await (await db.execute(
                "SELECT skills_required, title FROM opportunities WHERE id = ?", [opportunity_id]
            )).fetchone()
            if opp:
                opp_skills = json.loads(opp[0] or "[]")
                effective_role = effective_role or opp[1]

    await emit_trace(session_id, "Gap Analysis Agent", "running", "Determining required skills...")

    # 3. Extract JD skills if JD provided
    jd_extracted = None
    if job_description:
        jd_extracted = await extract_jd_skills(job_description)  # add this to groq_service.py

    # 4. Determine required skills (deterministic)
    required = determine_required_skills(effective_role, jd_extracted, opp_skills)
    if not required:
        raise ValueError("Could not determine required skills for this role")

    await emit_trace(session_id, "Gap Analysis Agent", "running", "Scoring your profile against required skills...")

    # 5. Score evidence (deterministic)
    evidence = score_student_evidence(required, student_skills)
    gaps = [e for e in evidence if e.evidence_level == 0][:8]

    await emit_trace(session_id, "Gap Analysis Agent", "running", "Generating improvement recommendations...")

    # 6. LLM synthesis (narrative + projects + resources)
    llm_payload = {
        "target_role": effective_role,
        "student_skills": student_skills,
        "gaps": [{"skill": g.skill, "priority": g.priority, "cluster": g.cluster_name} for g in gaps]
    }
    llm_result = await run_gap_analysis_llm(llm_payload)  # add to groq_service.py

    # 7. Normalize (hallucination guard)
    missing_skills, suggested_projects = normalize_llm_output(llm_result, evidence)

    # 8. Build result
    mode = "profile_vs_opportunity" if opportunity_id else ("profile_vs_jd" if job_description else "profile_vs_role")
    result = GapAnalysisResult(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        target_role=effective_role,
        analysis_mode=mode,
        overall_assessment=llm_result.get("overall_assessment") or f"Analysis complete for {effective_role}.",
        missing_skills=missing_skills,
        suggested_projects=suggested_projects,
        evidence_data=evidence,
        jd_snippet=job_description[:300] if job_description else None,
        profile_snapshot={"skills_count": len(student_skills), "target_roles": target_roles},
        generated_at=datetime.now().isoformat(),
        is_stale=False
    )

    # 9. Persist to SQLite (upsert: one row per profile+opportunity pair)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO gap_analyses
            (id, profile_id, opportunity_id, target_role, analysis_mode,
             overall_assessment, missing_skills, suggested_projects,
             evidence_data, jd_snippet, profile_snapshot, generated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            result.id, profile_id, opportunity_id, effective_role, mode,
            result.overall_assessment,
            json.dumps([ms.dict() for ms in missing_skills]),
            json.dumps([sp.dict() for sp in suggested_projects]),
            json.dumps([ev.dict() for ev in evidence]),
            result.jd_snippet,
            json.dumps(result.profile_snapshot),
            result.generated_at
        ])
        await db.commit()

    await emit_trace(session_id, "Gap Analysis Agent", "complete", f"Gap analysis complete — {len(missing_skills)} skill gaps identified")
    return result
```

**Add two functions to `services/groq_service.py`:**

```python
async def extract_jd_skills(job_description: str) -> dict:
    """Extract required/preferred/tech skills from a pasted JD. Used by Gap Analysis Agent."""
    # Returns { required_skills: [], preferred_skills: [], tech_stack: [] }
    return client_120b.create(
        model="openai/gpt-oss-120b",
        response_model=...,  # create a JDSkillsExtraction Pydantic model
        messages=[{"role": "user", "content":
            f"Extract skills from this job description into three categories: required_skills, preferred_skills, tech_stack. Return as JSON.\n\n{job_description[:3000]}"}]
    )

async def run_gap_analysis_llm(payload: dict) -> dict:
    """LLM synthesis for Gap Analysis. Returns narrative + project suggestions + resources."""
    # CRITICAL: prompt must instruct LLM not to invent skills outside the provided gaps list
    prompt = f"""You are a career advisor. A student's profile has been analysed against the role '{payload["target_role"]}'.
    
The following skill gaps were deterministically identified:
{json.dumps(payload['gaps'], indent=2)}

The student's current skills: {', '.join(payload['student_skills'])}

Your task:
1. For each gap skill, write a 1-2 sentence explanation of WHY this skill matters for {payload['target_role']}.
2. Suggest exactly 3 projects the student can build to address multiple gaps. Be specific and practical.
3. For each gap skill, suggest 1 real learning resource with a real URL (must start with http).
4. Write a 2-3 sentence overall assessment of the student's readiness for {payload['target_role']}.

IMPORTANT: Only address the skills listed above. Do NOT add new gap skills not in the list above.

Return as JSON matching this schema:
{{
  "overall_assessment": "...",
  "missing_skills": [
    {{"skill": "...", "reason": "...", "learning_resources": [{{"resource": "...", "url": "http..."}}]}}
  ],
  "suggested_projects": [
    {{"project_type": "...", "description": "...", "skills_addressed": ["..."]}}
  ]
}}"""
    # Call Groq via instructor — use gpt-oss-120b for quality
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)
```

**Done when:**
- `POST /api/gap-analysis/run` with `{ profile_id, target_role: "SDE Intern" }` → returns `GapAnalysisResult` with `missing_skills` array (all items from deterministic evidence, not LLM hallucinations)
- `POST /api/gap-analysis/run` with `{ profile_id, job_description: "..." }` (min 50 chars) → JD mode works
- `GET /api/gap-analysis/{profile_id}` → returns the persisted result
- Gap Analysis Page Tab 1 renders the overall assessment + missing skills cards + suggested projects
- Gap Analysis Page Tab 2 allows JD paste and shows ephemeral result
- "View Gap Analysis" button in `OpportunityDetailDrawer` triggers and renders the analysis for that specific opportunity

---

### STEP 4 — Discovery Frontend *(Hours 8–14, parallel with Step 3)*

**Person B — Dashboard layout + opportunity feed**

Build `Dashboard.jsx`:
- Fixed sidebar, main content area, right panel layout using Tailwind flex/grid
- `OpportunityCard` component — all fields as specified (match % badge, deadline badge, platform badge, "Also on" merge badge)
- Card grid: `grid grid-cols-3 gap-4` (responsive)
- "Find Opportunities" button → `POST /api/opportunities/search` → store `session_id` → open WebSocket

Build `AgentTracePanel.jsx`:
```javascript
// Opens WebSocket on session_id received
useEffect(() => {
  if (!sessionId) return;
  const ws = new WebSocket(`ws://localhost:8000/ws/agent-trace?session_id=${sessionId}`);
  ws.onmessage = (e) => {
    const event = JSON.parse(e.data);
    setSteps(prev => [...prev, event]);
    if (event.status === 'complete') {
      setTimeout(() => setVisible(false), 3000);
      fetchOpportunities();
    }
  };
  return () => ws.close();
}, [sessionId]);
```

**Person A — WebSocket endpoint**

Add to `main.py`:
```python
from fastapi import WebSocket
import json, asyncio

active_connections: dict[str, WebSocket] = {}

@app.websocket("/ws/agent-trace")
async def agent_trace_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    try:
        while True:
            await asyncio.sleep(1)
    except:
        del active_connections[session_id]

async def emit_trace(session_id: str, agent: str, status: str, message: str):
    if session_id in active_connections:
        await active_connections[session_id].send_text(json.dumps({
            "agent": agent, "status": status,
            "message": message, "timestamp": str(datetime.now())
        }))
```

**Done when:** Click "Find Opportunities" → agent trace panel appears → steps stream in live → cards render after complete event. Match % badge shows correct colour. Deadline badge shows correct urgency colour.

---

### STEP 5 — Gmail Integration & Guardian Agent *(Hours 10–16)*

**Person C — Gmail OAuth + Guardian Agent**

Build `services/gmail_service.py`:
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import base64, json

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_oauth_flow():
    return Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/api/gmail/callback'
    )

def get_gmail_service(token_path='token.json'):
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build('gmail', 'v1', credentials=creds)

def fetch_emails_3pass(service) -> list[dict]:
    queries = [
        "subject:(interview OR shortlisted OR application OR offer OR submission OR test OR round OR accept OR congratulations OR selected OR rejected OR deadline OR schedule OR assessment) newer_than:60d",
        "from:(noreply@linkedin.com OR naukri.com OR unstop.com OR hackerearth.com OR internshala.com OR hr OR recruit OR talent OR careers) newer_than:60d",
        "(\"last date\" OR \"closes on\" OR \"submit by\" OR \"offer letter\" OR \"joining date\") newer_than:60d"
    ]
    seen_ids = set()
    emails = []
    for q in queries:
        result = service.users().messages().list(userId='me', q=q, maxResults=50).execute()
        for msg_ref in result.get('messages', []):
            if msg_ref['id'] in seen_ids:
                continue
            seen_ids.add(msg_ref['id'])
            msg = service.users().messages().get(userId='me', id=msg_ref['id'], format='full').execute()
            body = extract_body(msg)
            emails.append({"id": msg_ref['id'], "body": body, "snippet": msg.get("snippet","")})
    return emails

def extract_body(msg: dict) -> str:
    # Extract plain text from email payload
    payload = msg.get('payload', {})
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data', '')
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    data = payload.get('body', {}).get('data', '')
    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore') if data else msg.get('snippet', '')
```

Build `routers/gmail.py`:
- `GET /api/gmail/connect` → redirect to OAuth URL
- `GET /api/gmail/callback` → exchange code → save token.json → trigger Guardian Agent → redirect to `/dashboard`
- `GET /api/gmail/status` → check token.json exists → return status + stats
- `POST /api/gmail/scan` → re-run Guardian Agent
- `DELETE /api/gmail/disconnect` → delete token.json

**Done when:** Click "Connect Gmail" in browser → consent screen appears → after approval → redirected to dashboard → Guardian Agent runs → deadlines appear in database.

---

### STEP 6 — Deadline Calendar & Notifier Agent *(Hours 14–20)*

**Person B — Deadline calendar UI**

Build `DeadlineCalendar.jsx`:
```javascript
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';

// Map deadlines to FullCalendar events with colour coding
const events = deadlines.map(d => {
  const daysLeft = Math.floor((new Date(d.deadline_datetime) - new Date()) / 86400000);
  return {
    id: d.id,
    title: d.title,
    date: d.deadline_datetime.split('T')[0],
    color: daysLeft <= 3 ? '#E24B4A' : daysLeft <= 7 ? '#EF9F27' : '#1D9E75'
  };
});
```

Build `DeadlineForm.jsx` — slide-in panel with all fields. On submit → `POST /api/deadlines` → calendar refreshes.

**Person A — Notifier Agent + APScheduler**

Build `services/scheduler_service.py`:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()

def schedule_reminders(deadline_id: str, deadline_dt: datetime, profile_id: str):
    intervals = [7, 3, 1, 0]  # days before
    for days in intervals:
        fire_time = deadline_dt - timedelta(days=days)
        if days == 0:
            fire_time = deadline_dt.replace(hour=9, minute=0, second=0)
        if fire_time > datetime.now():
            scheduler.add_job(
                func=send_reminder,
                trigger=DateTrigger(run_date=fire_time),
                args=[deadline_id, profile_id],
                id=f"reminder_{deadline_id}_{days}d",
                replace_existing=True
            )

def cancel_reminders(deadline_id: str):
    for days in [7, 3, 1, 0]:
        job_id = f"reminder_{deadline_id}_{days}d"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

async def send_reminder(deadline_id: str, profile_id: str):
    # 1. Load deadline + profile from SQLite
    # 2. Call groq_service.generate_reminder()
    # 3. Save to notifications table
    # 4. Push to WebSocket
    # 5. Send SMTP email
    pass
```

**Person C — SMTP email delivery**

Build `services/email_service.py`:
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_reminder_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg['From'] = os.getenv("SMTP_FROM_EMAIL")
    msg['To'] = to_email
    msg['Subject'] = f"OpportunIQ: {subject}"
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(os.getenv("SMTP_FROM_EMAIL"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)
```

Build the "Add Deadline" manual form API: `routers/deadlines.py` → `POST /api/deadlines` → save to DB → call `schedule_reminders()`.

Build "Test Reminder" API: `POST /api/notifications/test` → immediately call `send_reminder()` bypassing scheduler.

**Done when:** Add a deadline manually → 4 scheduler jobs created → click "Test Reminder" in settings → notification appears in bell dropdown AND email arrives in inbox within 10 seconds.

---

### STEP 7 — Remaining Pages & Integration *(Hours 18–26)*

**Person A — Saved Opportunities Tracker API**
- Build `routers/saved.py` with all CRUD endpoints
- `GET /api/saved` returns opportunities joined with their current status and details

**Person B — Remaining frontend pages**
- `SavedOpportunities.jsx` — stats row + table with inline status dropdown
- `GapAnalysisPage.jsx` — two tabs: career goal mode and JD comparison mode. Renders `GapAnalysisCard`. See Step 3.5 for full spec.
- `Notifications.jsx` — tabbed list, mark read actions
- `Settings.jsx` — accordion sections, all 6 settings panels
- `NotificationBell.jsx` — badge count from `GET /api/notifications?unread=true`, WebSocket listener updates count in real time

**Person C — Notifications API + WebSocket push**
- `routers/notifications.py` — CRUD endpoints
- Wire WebSocket push in `send_reminder()`: after saving notification to DB, call `emit_trace()` with notification payload so bell badge updates in real time without page refresh

**Done when:** Save an opportunity → it appears in Saved tab with "Not Applied" status → change status to "Applied" → persists on refresh. Bell badge shows correct unread count. Mark all read clears the badge.

---

### STEP 8 — Opportunity Detail Drawer & Skill Gap *(Hours 20–24)*

**Person A — Skill gap calculation**

In `routers/opportunities.py`, add a `GET /api/opportunities/{id}/skill-gap` endpoint:
```python
async def get_skill_gap(opportunity_id: str, profile_id: str):
    opportunity = await db.fetch_opportunity(opportunity_id)
    profile = await db.fetch_profile(profile_id)

    opp_skills = set(s.lower() for s in opportunity.skills_required)
    stu_skills = set(s.lower() for s in profile.skills)

    # Exact matches
    matched = opp_skills & stu_skills

    # Semantic near-matches (cosine sim > 0.7 counts as partial match)
    partial = []
    missing = []
    for opp_skill in opp_skills - matched:
        scores = [(stu_skill, float(cosine_similarity(
            [model.encode(opp_skill)], [model.encode(stu_skill)])[0][0]))
            for stu_skill in stu_skills]
        best = max(scores, key=lambda x: x[1])
        if best[1] > 0.7:
            partial.append({"required": opp_skill, "matched_as": best[0], "similarity": best[1]})
        else:
            missing.append(opp_skill)

    return {"matched": list(matched), "partial": partial, "missing": missing}
```

**Person B — OpportunityDetailDrawer UI**
- Skill gap list: ✓ matched (green), ~ partial match (amber with matched skill name), ✗ missing (red)
- Full description text (from opportunity DB record)
- "Apply Now" button (opens URL in new tab)
- "Save Opportunity" / "Unsave" toggle button
- "Add Deadline" quick-action

**Done when:** Click any opportunity card → drawer slides in → skill gap shows matched/partial/missing correctly for the logged-in profile.

---

### STEP 9 — Polish, Integration Testing & Demo Prep *(Hours 26–32)*

**All three members — assign one each:**

**Person A — Backend hardening**
- Add error handling to all routes: try/catch, return appropriate HTTP status codes
- Add request timeout wrappers around all external API calls (ResumeAI, Tavily, JobSpy, Groq, Gmail)
- Add result caching: if same profile searches within 30 minutes, return cached results from SQLite instead of re-running Tavily/JobSpy (saves credits and time)
- Test Gmail 3-pass fetch with the pre-seeded demo Gmail account
- Verify all 5 APScheduler jobs are created on deadline entry and cancelled on delete

**Person B — Frontend polish**
- Add loading skeletons on opportunity cards while search runs
- Add empty state illustrations for: no opportunities found, no deadlines, no notifications
- Make sidebar responsive (collapse to icon-only on narrow screens)
- Add toast notifications for success/error on all form submissions
- Verify all API error states are handled gracefully (show error banner, not blank screen)

**Person C — Demo data + demo flow**
- Pre-load 2 realistic student resume PDFs into the system (one CSE, one ECE profile)
- Pre-seed the demo Gmail account with 8–10 realistic emails: hackathon confirmation, interview invite, offer letter, application shortlisted, submission reminder
- Run the full demo flow end-to-end 3 times and time it (target: under 6 minutes)
- Prepare the "Test Reminder" demo sequence: select SIH deadline → fire → show notification arrives → show email arrives
- Cache 15 realistic opportunity results in SQLite as fallback for demo (in case live search is slow)

**Done when:** Full demo flow completes under 6 minutes without any errors. All empty states are handled. Resume upload → profile review → search → results → Gmail connect → deadlines → test reminder → all work consecutively.

---

### STEP 10 — PPT + Presentation *(Hours 30–36)*

**Person C primarily, others contribute content**

**Slide structure:**
1. Title slide — OpportunIQ, team names, hackathon info
2. Problem Statement — two problems, quantified
3. Solution Overview — what OpportunIQ does in 3 bullet points
4. System Architecture — block diagram
5. Agent Pipeline — 5 agents with their responsibilities and tools
6. Tech Stack — table or visual
7. Demo Slide — "Live Demo" placeholder, used during presentation
8. Key Features — 9 core features with icons
9. Impact — target users, pain points addressed, measurable outcomes
10. Literature Survey Summary — 3–4 cited works, gaps identified
11. **How can OpportunIQ become an industry product?** (final required slide)

**Final Slide Content — "How can OpportunIQ become an industry product?"**

> - **Platform integrations at scale:** Partner directly with LinkedIn, Naukri, and Unstop via their official APIs (currently available under partnership programs) to move from web scraping to stable, real-time data feeds — enabling sub-minute opportunity updates across 10M+ listings.
> - **Multi-platform deadline intelligence:** Expand the Guardian Agent from Gmail to WhatsApp (via Twilio API), LinkedIn InMail, and SMS — intercepting deadline information wherever recruiters communicate.
> - **Institution licensing model:** License to universities and engineering colleges as an SaaS product. Admin dashboard for placement officers: see class-level opportunity coverage, placement rate tracking, and student engagement metrics.
> - **AI career coach layer:** Add a Career Coach Agent that analyses the student's application history, success rate by role/company type, and interview feedback to proactively recommend upskilling paths — powered by RAG over role-specific learning resources.
> - **Recruiter-facing product:** Flip the model — allow recruiters to post opportunities directly to OpportunIQ, with AI-powered student matching that delivers pre-qualified candidates. Revenue model: recruiter subscription + placement success fee.
> - **Mobile app:** React Native app with push notifications (Firebase Cloud Messaging) replacing SMTP email — enabling real-time, reliable deadline alerts even when students are away from their laptops.
> - **Privacy and compliance:** Move from OAuth read-only Gmail scanning to a verified integration with Google Workspace for Education, qualifying for institutional data agreements under India's DPDP Act 2023.

---

## 10. Pre-Hackathon Checklist (Step 0)

Complete everything below before the hackathon begins. This is the only step where work is done outside the 36-hour window.

### API Keys & Credentials

- [ ] **Tavily API** — Sign up at `tavily.com` → copy `TAVILY_API_KEY` (free, no card required)
- [ ] **Groq API** — Sign up at `console.groq.com` → create API key → copy `GROQ_API_KEY` (free)
- [ ] **ResumeAI microservice** — Confirm the TypeScript/Node.js service is deployed and reachable:
  - Verify `POST /api/v1/profile/extract` responds to a test request with a PDF file
  - Confirm the response matches the schema: `{ "success": true, "data": { "full_name", "skills", "target_roles", "preferred_location", "year_of_study", "graduation_year", "opportunity_type" } }`
  - Copy the base URL (without endpoint path) into `RESUMEAI_API_URL` in `.env`
  - If the service requires authentication, copy the key into `RESUMEAI_API_KEY`
  - Test from the Python side using `httpx` with a multipart POST before the hackathon starts:
    ```python
    import httpx
    with open("test_resume.pdf", "rb") as f:
        r = httpx.post(
            "https://your-resumeai-service.com/api/v1/profile/extract",
            files={"resume": ("test_resume.pdf", f, "application/pdf")},
            timeout=15.0
        )
    print(r.status_code, r.json())
    # Expected: 200, {"success": true, "data": {"full_name": ..., "skills": [...], ...}}
    ```
- [ ] **Google Cloud — Gmail API:**
  - Create project at `console.cloud.google.com`
  - Enable Gmail API for the project
  - Go to APIs & Services → Credentials → Create OAuth 2.0 Client ID (Web Application)
  - Add `http://localhost:8000/api/gmail/callback` as authorized redirect URI
  - Download `credentials.json` and place in the backend root folder
  - Run the OAuth flow once manually to generate `token.json`
  - Add your own email as a Test User in the OAuth consent screen
- [ ] **Gmail App Password (for SMTP relay):**
  - Gmail account → Settings → Security → 2-Step Verification (enable if not on)
  - App Passwords → Generate → select "Mail" → copy the 16-character password

### Python Libraries — Pre-install

```bash
pip install langgraph langchain langchain-community langchain-openai
pip install groq instructor pydantic
pip install tavily-python python-jobspy
pip install google-auth google-auth-oauthlib google-api-python-client
pip install sentence-transformers rapidfuzz scikit-learn
pip install apscheduler
pip install fastapi uvicorn python-multipart aiosqlite
pip install requests httpx python-dotenv
# Note: PyMuPDF (pymupdf) is NOT installed here.
# All PDF/DOC/DOCX parsing is handled exclusively by the ResumeAI microservice.
```

### Model Pre-download (mandatory — 80MB, takes 2–3 minutes)

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model ready:", model.encode(["test"]).shape)
```

### Frontend Dependencies — Pre-install

```bash
npm install axios tailwindcss @fullcalendar/react @fullcalendar/daygrid \
  @fullcalendar/interaction lucide-react
```

### Demo Data Preparation

- [ ] Prepare 2 realistic student resume PDFs (one CSE, one ECE with different skill sets)
- [ ] Create a demo Gmail account (separate from personal)
- [ ] Seed 8–10 realistic application emails into the demo Gmail account:
  - "You've been shortlisted for Google STEP Internship — complete your application by [date]"
  - "Smart India Hackathon 2025 — team submission deadline [date]"
  - "Interview scheduled — Zomato SDE Intern — [date + time]"
  - "Offer letter attached — please accept by [date]"
  - "Congratulations! Your application for Infosys is under review — next round details inside"
  - 3–4 more of similar types
- [ ] Run Gmail OAuth with the demo account and confirm `token.json` is generated
- [ ] Test one full pipeline run (search + extract + reminder) end-to-end before the hackathon

### Git Setup

```bash
git init opportuniq
cd opportuniq
mkdir opportuniq-backend opportuniq-frontend
echo "*.env\ntoken.json\ncredentials.json\n__pycache__/\nnode_modules/\n*.db" > .gitignore
git add . && git commit -m "Initial project structure"
# Share repo link with all team members
```

---

## 11. Environment Variables Reference

Create `.env` in `opportuniq-backend/`. Never commit this file.

```env
# Groq
GROQ_API_KEY=your_groq_api_key_here

# Tavily
TAVILY_API_KEY=your_tavily_api_key_here

# ResumeAI microservice (TypeScript/Node.js — separate deployed service)
# The Profile Agent calls: {RESUMEAI_API_URL}/api/v1/profile/extract
# Do NOT include the endpoint path here — only the base URL.
RESUMEAI_API_URL=https://your-resumeai-service.com
RESUMEAI_API_KEY=your_resumeai_key_if_auth_is_required

# Gmail SMTP (for sending reminder emails)
SMTP_FROM_EMAIL=your_demo_gmail@gmail.com
SMTP_APP_PASSWORD=your_16_char_app_password

# Gmail OAuth (file paths)
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# App
DATABASE_PATH=opportuniq.db
FRONTEND_URL=http://localhost:5173
```

Load in `main.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

*Build Plan v2.1 — OpportunIQ | TATA Centre AI/ML Hackathon*
*v2.0: ResumeAI microservice architecture confirmed (TypeScript/Node.js, POST /api/v1/profile/extract).*
*v2.1: Gap Analysis Agent added following Review 1 feedback. Methodology adapted from ResumeAI gap-advisor.service.ts, re-implemented natively in Python/FastAPI/SQLite. See Step 3.5 and Section 6 for full details.*
*All three team members work in parallel from Step 2 onwards.*
