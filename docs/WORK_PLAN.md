# OpportunIQ — Work Plan
### TATA Centre AI/ML Hackathon | NIT Tiruchirappalli
### 36-Hour Parallel Build Plan — All Three Developers

---

## Team

| Developer | Role Label (in Build Plan) | Primary Ownership |
|---|---|---|
| **Anantha Ram G S** | Person A | Backend APIs · LangGraph Agents · WebSocket |
| **Gowri J S** | Person B | Frontend UI · React Pages · UX Integration |
| **Sanjay Anand M** | Person C | Services · Integrations · Demo Prep |

> **How to use this document:** Each phase has three parallel columns — one per developer. Read only your column for what you build. Read the **Sync Points** to know when you need to talk to each other. The `✅ Done when` line at the end of each phase is the shared exit condition — nobody moves to the next phase until all three conditions are met.

---

## Before the Hackathon Starts — Step 0
### Everyone does this independently on their own laptop

These are non-negotiable. If Step 0 is incomplete, the 36-hour clock is wasted.

### Anantha Ram G S

- [ ] Sign up at `console.groq.com` → get `GROQ_API_KEY`
- [ ] Sign up at `tavily.com` → get `TAVILY_API_KEY`
- [ ] Google Cloud Console → create project → enable Gmail API → create OAuth 2.0 Web App credentials → download `credentials.json` → add `http://localhost:8000/api/gmail/callback` as redirect URI
- [ ] Run the Gmail OAuth flow once on a personal/demo Gmail account → confirm `token.json` is generated
- [ ] Gmail → Settings → Security → App Passwords → generate one for SMTP → save the 16-character password
- [ ] Install all Python libraries:
  ```bash
  pip install langgraph langchain langchain-community langchain-openai
  pip install groq instructor pydantic
  pip install tavily-python python-jobspy
  pip install google-auth google-auth-oauthlib google-api-python-client
  pip install sentence-transformers rapidfuzz scikit-learn
  pip install apscheduler fastapi uvicorn python-multipart aiosqlite
  pip install requests httpx python-dotenv
  ```
- [ ] Pre-download the sentence-transformer model (80MB — do this on Wi-Fi, not at venue):
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer('all-MiniLM-L6-v2')
  print("Model ready:", model.encode(["test"]).shape)
  ```
- [ ] Confirm model loads without error

### Gowri J S

- [ ] Install Node.js (v18+) and npm if not already installed
- [ ] Install all frontend dependencies:
  ```bash
  npm install axios tailwindcss @fullcalendar/react @fullcalendar/daygrid @fullcalendar/interaction lucide-react
  ```
- [ ] Read and understand the 9 page specifications in `BUILD_PLAN.md` Section 5 — know which pages you own before Day 1
- [ ] Prepare 2 realistic student resume PDFs (one CSE student, one ECE student with different skill sets) — these are your demo files
- [ ] Bookmark Tailwind CSS docs (`tailwindcss.com/docs`) and FullCalendar React docs — you will need them during the build
- [ ] Create a demo Gmail account (separate from personal) and seed it with 8–10 realistic application emails:
  - Subject: "You've been shortlisted for Google STEP Internship — complete your application by Nov 15"
  - Subject: "Smart India Hackathon 2025 — team submission deadline Nov 20"
  - Subject: "Interview scheduled — Zomato SDE Intern — Nov 12, 10:00 AM"
  - Subject: "Offer letter attached — please accept by Nov 18"
  - Subject: "Round 2 details — Infosys InfyTQ — your test link is inside"
  - Subject: "Congratulations! You are shortlisted for Microsoft Engage"
  - Subject: "HackerEarth Challenge — submission closes Nov 14 at 11:59 PM"
  - Subject: "Unstop — your registration for Smart India Hackathon is confirmed"
  - Add 2–3 more of similar types

### Sanjay Anand M

- [ ] Confirm the ResumeAI microservice is live and reachable. Test it with this exact script:
  ```python
  import httpx
  with open("test_resume.pdf", "rb") as f:
      r = httpx.post(
          "https://your-resumeai-service.com/api/v1/profile/extract",
          files={"resume": ("test_resume.pdf", f, "application/pdf")},
          timeout=15.0
      )
  print(r.status_code, r.json())
  # Expected: 200 and {"success": true, "data": {"full_name": ..., "skills": [...], ...}}
  ```
- [ ] Confirm the response has these exact fields: `full_name`, `year_of_study`, `graduation_year`, `target_roles`, `skills`, `preferred_location`, `opportunity_type`
- [ ] Note down the base URL (without `/api/v1/profile/extract`) — this goes in `.env` as `RESUMEAI_API_URL`
- [ ] Install all Python libraries (same as Anantha's list above — install on your machine too)
- [ ] Pre-download the sentence-transformer model (same as Anantha's step above)
- [ ] Set up the Git repository:
  ```bash
  git init opportuniq
  cd opportuniq
  mkdir opportuniq-backend opportuniq-frontend
  printf "*.env\ntoken.json\ncredentials.json\n__pycache__/\nnode_modules/\n*.db\n" > .gitignore
  git add . && git commit -m "Initial project structure"
  ```
- [ ] Share the repo link with Anantha and Gowri and confirm both can clone and push

---

## Phase 1 — Project Initialisation
### Hours 0–1 | All three work simultaneously

> One person creates the shared repo. The other two clone it. All three scaffold their layer at the same time.

---

### Anantha Ram G S

**Create the backend folder structure:**

```
opportuniq-backend/
├── main.py
├── database.py
├── models.py
├── agents/
│   ├── __init__.py
│   ├── graph.py
│   ├── profile_agent.py
│   ├── discovery_agent.py
│   ├── ranker_agent.py
│   ├── guardian_agent.py
│   └── notifier_agent.py
├── routers/
│   ├── profile.py
│   ├── opportunities.py
│   ├── deadlines.py
│   ├── gmail.py
│   ├── notifications.py
│   └── settings.py
├── services/
│   ├── resume_service.py
│   ├── jobspy_service.py
│   ├── tavily_service.py
│   ├── gmail_service.py
│   ├── groq_service.py
│   ├── ranker_service.py
│   ├── scheduler_service.py
│   └── email_service.py
├── .env
└── requirements.txt
```

Paste this into `main.py` and confirm it runs:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    from database import init_db
    await init_db()
    yield

app = FastAPI(title="OpportunIQ API", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"])
```

Run: `uvicorn main:app --reload` — must start with no errors.

---

### Gowri J S

**Create the React frontend:**

```bash
npm create vite@latest opportuniq-frontend -- --template react
cd opportuniq-frontend
npm install axios tailwindcss @fullcalendar/react @fullcalendar/daygrid @fullcalendar/interaction lucide-react
npx tailwindcss init -p
npm run dev
```

Create all page and component files as empty stubs (just `export default function X() { return <div>X</div>; }`):

```
src/pages/      Landing.jsx, ResumeUpload.jsx, ManualForm.jsx,
                ProfileReview.jsx, Dashboard.jsx, DeadlineCalendar.jsx,
                SavedOpportunities.jsx, Notifications.jsx, Settings.jsx

src/components/ Navbar.jsx, Sidebar.jsx, OpportunityCard.jsx,
                OpportunityDetailDrawer.jsx, AgentTracePanel.jsx,
                GmailConnectCard.jsx, DeadlineMiniCalendar.jsx,
                NotificationBell.jsx, DeadlineForm.jsx,
                TagInput.jsx, StepIndicator.jsx, FieldStatusBadge.jsx

src/api/        client.js
```

Set up `client.js`:
```javascript
import axios from 'axios';
const api = axios.create({ baseURL: 'http://localhost:8000' });
export default api;
```

Set up `App.jsx` with React Router routes for all 9 pages.

Run: `npm run dev` — must open at `localhost:5173` without errors.

---

### Sanjay Anand M

**Create `database.py`** with all 5 table schemas and `init_db()` function. Copy the exact SQL from `BUILD_PLAN.md` Section 7.

**Create `models.py`** with all Pydantic schemas from `BUILD_PLAN.md` Section 6:
- `ResumeAIData`
- `ResumeAIResponse`
- `StudentProfile`
- `Opportunity`
- `DeadlineExtraction`
- `ReminderMessage`

**Create `.env`** in `opportuniq-backend/`:
```env
GROQ_API_KEY=your_key
TAVILY_API_KEY=your_key
RESUMEAI_API_URL=https://your-resumeai-service.com
RESUMEAI_API_KEY=your_key_if_needed
SMTP_FROM_EMAIL=your_demo_gmail@gmail.com
SMTP_APP_PASSWORD=your_16_char_app_password
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
DATABASE_PATH=opportuniq.db
FRONTEND_URL=http://localhost:5173
```

**Create `requirements.txt`** listing all installed packages.

Run: `python -c "import database; import asyncio; asyncio.run(database.init_db()); print('DB OK')"` — must print `DB OK` and create `opportuniq.db`.

---

**✅ Phase 1 done when:**
- Anantha: `uvicorn main:app --reload` starts without errors
- Gowri: `npm run dev` opens at `localhost:5173` without errors
- Sanjay: `opportuniq.db` exists with all 5 tables confirmed

**🔁 Sync point:** All three confirm to each other that their layer is up. Push to Git. Now you can work in full parallel.

---

## Phase 2 — Profile System
### Hours 1–4 | Full parallel — no blocking

---

### Anantha Ram G S

**Build `routers/profile.py`** with 4 endpoints:

`POST /api/profile/upload`
- Receive the uploaded file (PDF/DOC/DOCX) using FastAPI `UploadFile`
- Read file bytes: `file_bytes = await file.read()`
- Call `resume_service.forward_to_resumeai(file_bytes, file.filename, file.content_type)`
- If `response.success == False` → return HTTP 422 with `{ "error": "ResumeAI extraction failed", "fallback": "manual" }`
- Call `resume_service.map_resumeai_to_profile(response.data.dict())`
- Save the mapped profile to SQLite `student_profiles` table
- Return `{ "profile_id": ..., "profile": ..., "missing_fields": [...] }`

`POST /api/profile/manual`
- Validate request body against `StudentProfile` Pydantic model
- Generate UUID as `profile_id`
- Save to SQLite
- Return `{ "profile_id": ..., "profile": ... }`

`GET /api/profile/{id}`
- Fetch row from `student_profiles` where `id = profile_id`
- Return as `StudentProfile` JSON

`PATCH /api/profile/{id}`
- Accept partial JSON (only fields being updated)
- Update only those fields in SQLite + update `updated_at`
- Return full updated profile

---

### Gowri J S

**Build `ResumeUpload.jsx`:**
- Drag-and-drop zone using HTML `onDrop` + `onDragOver` events (no external library needed)
- Accept `.pdf`, `.doc`, `.docx` only — validate MIME type client-side before sending
- Show 4 states: idle → uploading (spinner) → parsing ("Extracting your profile with AI...") → success (green tick)
- Call `POST /api/profile/upload` with `FormData`
- On success: `navigate('/onboarding/review?profile_id=' + data.profile_id)`
- On error or timeout: show `ErrorBanner` with "Try setting up manually →" link

**Build `ManualForm.jsx`:**
- Form sections: "About You", "Your Goals", "Preferences"
- Build the `TagInput` component: controlled text input → press Enter or comma → push tag to array state → render as removable chip with × button. Reuse this for both Skills and Target Roles fields.
- `OpportunityTypeSelector`: four radio options (Internship / Full-time / Hackathon / All) with icons from `lucide-react`
- Save form state to `localStorage` on every change (prevents data loss on accidental navigation)
- Submit → `POST /api/profile/manual` → navigate to `/onboarding/review?profile_id=...`

**Build `ProfileReview.jsx`:**
- On mount: `GET /api/profile/{id}` → pre-fill all form fields
- `FieldStatusBadge` logic: green ✓ for non-null fields, amber ⚠ for null fields, always-amber for `email`, `degree`, `college`
- "Confirm Profile" button: disabled until `skills.length > 0`, `target_roles.length > 0`, `location` is filled, `opportunity_type` is filled
- On confirm: `PATCH /api/profile/{id}` → navigate to `/dashboard`

---

### Sanjay Anand M

**Build `services/resume_service.py`** — complete implementation:
- `forward_to_resumeai()`: use `httpx.AsyncClient` with 15s timeout to forward raw file to ResumeAI `POST /api/v1/profile/extract` as multipart. Handle `TimeoutException`, `HTTPStatusError`, and generic exceptions — all return `ResumeAIResponse(success=False, data=None)`.
- `map_resumeai_to_profile()`: explicit field mapping from ResumeAI response to `StudentProfile`. `full_name → name`, `preferred_location → location`. `email`, `degree`, `college` always set to `None` (always flagged as missing).

Reference the exact code in `BUILD_PLAN.md` Step 2 (Person C section) — copy it directly.

Test it in isolation before Anantha wires it into the router:
```python
import asyncio, httpx
# Call your deployed ResumeAI and print what comes back
# Confirm the field names match what map_resumeai_to_profile() expects
```

---

**✅ Phase 2 done when:**
- Upload a real PDF → ResumeAI parses it → profile review page shows green and amber fields correctly
- Manual form submits and saves without errors
- Confirm button navigates to dashboard with profile loaded in state
- `GET /api/profile/{id}` returns the correct JSON for a saved profile

**🔁 Sync point:** Anantha and Sanjay test the upload route together once Sanjay's `resume_service.py` is ready. Gowri tests the three onboarding pages independently using a mock API response, then swaps to the real backend once it's up.

---

## Phase 3 — Discovery Pipeline (Backend)
### Hours 4–12 | Full parallel — Gowri starts Dashboard in Phase 4 simultaneously

---

### Anantha Ram G S

**Build `services/jobspy_service.py`:**
- Wrap `scrape_jobs()` from `python-jobspy` targeting `["linkedin", "naukri", "indeed", "glassdoor", "google"]`
- Parameters: `search_term=role`, `location=location`, `results_wanted=15`, `hours_old=168`
- Return `jobs.to_dict('records')` if not empty, else `[]`
- Wrap in `try/except` — JobSpy can throw unpredictably; never let it crash the pipeline

**Build `routers/opportunities.py`** with `POST /api/opportunities/search`:
- Read student profile from SQLite using `profile_id`
- Call `jobspy_service.search_jobs()` for each `target_role` in the profile
- Call `tavily_service.search_hackathons_and_portals()` (built by Sanjay)
- Combine raw results into one list
- Call `groq_service.extract_opportunity()` (built by Sanjay) for each raw result
- Pass extracted results to `ranker_service.deduplicate()` then `ranker_service.score()` (built by Sanjay)
- Save top 15 to `opportunities` table in SQLite with `session_id`
- Return `{ "session_id": ... }`
- Throughout this pipeline, call `emit_trace()` at each step to stream progress to WebSocket

**Add WebSocket endpoint to `main.py`:**
```python
from fastapi import WebSocket
import json, asyncio
from datetime import datetime

active_connections: dict[str, WebSocket] = {}

@app.websocket("/ws/agent-trace")
async def agent_trace_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        active_connections.pop(session_id, None)

async def emit_trace(session_id: str, agent: str, status: str, message: str):
    ws = active_connections.get(session_id)
    if ws:
        await ws.send_text(json.dumps({
            "agent": agent, "status": status,
            "message": message, "timestamp": str(datetime.now())
        }))
```

**Build `GET /api/opportunities`:**
- Accept `?session_id=X` or `?profile_id=X`
- Fetch ranked results from SQLite
- Return as list of `Opportunity` JSON objects

---

### Gowri J S

> You work on Phase 4 (Dashboard UI) simultaneously while Anantha and Sanjay build the backend. Do not wait for the backend to be complete — build the UI with mock data first.

**This is covered in Phase 4 below. Start Phase 4 now.**

---

### Sanjay Anand M

**Build `services/tavily_service.py`:**
- `TavilyClient` with `TAVILY_API_KEY` from env
- 5 targeted queries: Unstop, Devfolio, HackerEarth, Internshala, company career portals
- Use `search_depth="basic"` (1 credit each — don't use `advanced` here)
- Return list of result dicts with title, URL, snippet
- Wrap each query in `try/except` — partial failures are acceptable

**Build `services/groq_service.py`** — 3 functions:
- `extract_opportunity(raw_text)`: Groq `openai/gpt-oss-120b` via Instructor → `Opportunity` Pydantic model. Prompt: "Extract structured job/internship/hackathon details. Return null for missing fields."
- `extract_deadline(email_text)`: Groq `openai/gpt-oss-20b` via Instructor → `DeadlineExtraction` Pydantic model.
- `generate_reminder(name, skills, title, dt, days_left)`: Groq `openai/gpt-oss-120b` → `ReminderMessage` Pydantic model. Keep message under 100 words.

Reference the exact code in `BUILD_PLAN.md` Step 3 (Person B section).

**Build `services/ranker_service.py`** — 3 functions:
- `normalise_url(url)`: strip query params, trailing slash
- `deduplicate(results)`: 3-layer pipeline — URL SHA256 hash → rapidfuzz `token_sort_ratio` ≥ 85 → cosine similarity ≥ 0.92. Merge "Also on" badge on surviving card.
- `score(opportunity, student_skills)`: `0.7 × skill_cosine + 0.3 × urgency`. Urgency = `1 / (days_until_deadline + 1)`, default 0.1 if no deadline.

Reference the exact code in `BUILD_PLAN.md` Step 3 (Person C section).

Test `ranker_service.py` in isolation:
```python
from services.ranker_service import deduplicate, score

# Create 5 fake opportunities, 2 of which are duplicates
# Confirm deduplicate returns 3 and the merged card has "also_on" populated
# Confirm score returns a float between 0 and 1
```

---

**✅ Phase 3 done when:**
- `POST /api/opportunities/search` → JobSpy fetches results → Tavily fetches results → Groq extracts structured data → dedup runs → top 15 scored and saved to SQLite → `GET /api/opportunities?session_id=X` returns them as JSON
- WebSocket streams at least 4 trace events during the search
- No crashes on any of: JobSpy timeout, Tavily API error, Groq rate limit (all fail gracefully and continue)

**🔁 Sync point:** Anantha calls Sanjay once the services are ready to wire into the router. Gowri connects the real API to the Dashboard as soon as `GET /api/opportunities` returns real data.

---

## Phase 4 — Discovery Frontend
### Hours 8–14 | Gowri works alone, others continue Phase 3

---

### Anantha Ram G S

> Continuing Phase 3 backend work during this window. See Phase 3 above.

---

### Gowri J S

**Build `Dashboard.jsx`** with the 3-column layout:
- Left sidebar (240px, fixed): logo, nav links using `lucide-react` icons, profile avatar at bottom
- Main content area (flex-grow): opportunity card grid
- Right panel (300px): Gmail connect card + mini deadline calendar

**Build `OpportunityCard.jsx`:**
- Company letter-avatar (first letter of company name in a coloured circle)
- Job title (bold), company name, location chip
- Platform badge (colour-coded: LinkedIn = blue, Naukri = teal, Unstop = purple, Devfolio = indigo, HackerEarth = green, Indeed = orange, Google = grey)
- Match % circular badge (green >70%, amber 40–70%, red <40%)
- Deadline badge (red "⏰ 2 days", amber "📅 5 days", green "✅ 15 days", grey "No deadline")
- "Also on: LinkedIn, Naukri" text tag (if `also_on` array is non-empty)
- Apply button (opens `opportunity.url` in new tab)
- Bookmark icon → saves opportunity (wired in Phase 7)
- Click on card body → opens `OpportunityDetailDrawer`

**Build `AgentTracePanel.jsx`:**
- Slides in from the right when `sessionId` is set
- Connects to `ws://localhost:8000/ws/agent-trace?session_id={sessionId}`
- Each incoming WebSocket event renders as a timeline row: status icon (⟳ running / ✓ done) + agent name + message + elapsed time
- Auto-hides 3 seconds after receiving an event with `status === "complete"`
- After hiding, call `fetchOpportunities()` to load the ranked cards

**Develop with mock data first** — create a `mockData.js` file with 5 hardcoded opportunity objects. Wire up the real `GET /api/opportunities` endpoint once Anantha confirms it returns data.

---

### Sanjay Anand M

> Continuing Phase 3 services work — `groq_service.py` and `ranker_service.py`. See Phase 3 above.

---

**✅ Phase 4 done when:**
- Click "Find Opportunities" → agent trace panel slides in → step events stream live → cards appear after the complete event
- Match % badge colours are correct
- Deadline badge shows correct urgency colour
- Platform badge is colour-coded correctly
- "Also on" merge badge appears for any deduplicated result

**🔁 Sync point:** Gowri and Anantha test this together. Anantha must confirm the WebSocket emits events before Gowri can test the trace panel with real data.

---

## Phase 5 — Gmail Integration & Guardian Agent
### Hours 10–16 | Sanjay leads, Anantha wires

---

### Anantha Ram G S

**Build `routers/gmail.py`** with 5 endpoints:

`GET /api/gmail/connect`
- Call `gmail_service.get_oauth_flow()` → get authorization URL → `return RedirectResponse(auth_url)`

`GET /api/gmail/callback`
- Exchange `code` query parameter for tokens using the OAuth flow
- Save token to `token.json`
- Trigger Guardian Agent pipeline (call `run_guardian_agent(profile_id)`)
- Redirect to `http://localhost:5173/dashboard`

`GET /api/gmail/status`
- Check if `token.json` exists
- If yes, return `{ "connected": true, "last_scanned": ..., "deadlines_found": N }`
- If no, return `{ "connected": false }`

`POST /api/gmail/scan`
- Re-trigger Guardian Agent for `profile_id` in request body

`DELETE /api/gmail/disconnect`
- Delete `token.json`
- Return `{ "success": true }`

---

### Gowri J S

**Build `GmailConnectCard.jsx`:**
- Pre-connection state: shield icon + "Read-only access. We never send emails." + "Connect Gmail" button + "I'll add deadlines manually" link
- "Connect Gmail" button: calls `window.location.href = 'http://localhost:8000/api/gmail/connect'` (full redirect — not Axios)
- Post-connection state: connected email address + last scan timestamp + deadline count + "Re-scan" link + "Disconnect" link

**Build `DeadlineForm.jsx`** (slide-in panel for manual deadline entry):
- Fields: Title (text), Organisation (text), Deadline Date (date picker), Deadline Time (time picker, default 23:59), Event Type (dropdown: Interview / Submission / Offer Acceptance / Test / Other), Notes (textarea optional)
- Submit → `POST /api/deadlines` → close panel → trigger calendar refresh
- Can be opened from the nav sidebar or from an opportunity card's "Add Deadline" quick-action

---

### Sanjay Anand M

**Build `services/gmail_service.py`** — complete implementation:
- `get_oauth_flow()`: `Flow.from_client_secrets_file('credentials.json', scopes=['...gmail.readonly'], redirect_uri='http://localhost:8000/api/gmail/callback')`
- `get_gmail_service(token_path)`: load credentials from `token.json` → return Gmail API service object
- `fetch_emails_3pass(service)`: run 3 queries, dedup by `message_id`, return list of `{ id, body, snippet }`
- `extract_body(msg)`: decode base64 payload, prefer `text/plain` parts

**Build `agents/guardian_agent.py`:**
- Call `gmail_service.fetch_emails_3pass()`
- For each email: call `groq_service.extract_deadline(email.body)`
- Filter: `has_deadline == True` and `confidence >= 0.6`
- For `confidence < 0.6`: save to DB with `needs_review = True`
- Save qualifying deadlines to `deadline_registry` SQLite table
- For each saved deadline: call `scheduler_service.schedule_reminders(deadline_id, deadline_dt, profile_id)`

Reference the exact code in `BUILD_PLAN.md` Step 5 (Person C section).

---

**✅ Phase 5 done when:**
- Click "Connect Gmail" → browser redirects to Google consent → after approval → redirected back to `/dashboard`
- Guardian Agent runs automatically post-redirect
- Deadlines extracted from the pre-seeded demo Gmail account appear in `deadline_registry` table
- `GET /api/gmail/status` returns `{ "connected": true, "deadlines_found": N }`
- Manual deadline entry form submits and saves to DB correctly

**🔁 Sync point:** All three test this together. Sanjay confirms the Guardian Agent runs and extracts deadlines. Anantha confirms the OAuth router works. Gowri confirms the Gmail card changes state correctly after connection.

---

## Phase 6 — Deadline Calendar & Notifier Agent
### Hours 14–20 | Full parallel

---

### Anantha Ram G S

**Build `services/scheduler_service.py`:**
- `BackgroundScheduler` started in `main.py` lifespan
- `schedule_reminders(deadline_id, deadline_dt, profile_id)`: create 4 `DateTrigger` jobs at 7d, 3d, 1d, same-day 09:00 before the deadline (skip if fire time is in the past)
- `cancel_reminders(deadline_id)`: remove all 4 jobs for that deadline
- `send_reminder(deadline_id, profile_id)` (the actual job function): load deadline + profile from DB → call `groq_service.generate_reminder()` → save to `notifications` table → call `emit_trace()` to push WebSocket notification → call `email_service.send_reminder_email()`

**Build `routers/deadlines.py`** with full CRUD:
- `POST /api/deadlines` → save to `deadline_registry` → call `schedule_reminders()` → return `{ "deadline_id": ..., "reminders_scheduled": [...] }`
- `GET /api/deadlines` → fetch all for `profile_id`, sorted by `deadline_datetime`
- `GET /api/deadlines/{id}` → single deadline
- `PUT /api/deadlines/{id}` → update + reschedule reminders (cancel old → schedule new)
- `DELETE /api/deadlines/{id}` → delete from DB + call `cancel_reminders()`

**Build `POST /api/notifications/test`:**
- Accept `{ "deadline_id": "..." }` in request body
- Call `send_reminder(deadline_id, profile_id)` immediately (bypass scheduler)
- This is your demo safety net — use it during the presentation

---

### Gowri J S

**Build `DeadlineCalendar.jsx`:**
- Full `FullCalendar` React component with `dayGridPlugin` and `interactionPlugin`
- Fetch deadlines via `GET /api/deadlines` on mount
- Map each deadline to a FullCalendar event object: `{ id, title, date, color }`
- Colour logic: `daysLeft ≤ 3 → '#E24B4A'`, `≤ 7 → '#EF9F27'`, `> 7 → '#1D9E75'`
- Month view is default; add a List view toggle button
- On event click → show `DeadlineDetailPopup` with: title, organisation, event type, time remaining ("2 days 4 hours left"), notes, Edit button, Delete button
- "Add Deadline" button top-right → opens `DeadlineForm` slide-in panel
- After any `POST / PUT / DELETE` on a deadline → refetch and re-render calendar

**Build `NotificationBell.jsx`:**
- Bell icon (`lucide-react Bell`) in the top navbar with unread count badge
- On mount: `GET /api/notifications?unread=true` → set badge count
- Open WebSocket listener: when a `notification` event arrives → increment badge count without page reload
- Click bell → dropdown showing last 5 notifications, each with: message text + timestamp + "Mark read" button
- "View all" link → navigate to `/dashboard/notifications`

---

### Sanjay Anand M

**Build `services/email_service.py`:**
- `send_reminder_email(to_email, subject, body)`: standard `smtplib` SMTP via `smtp.gmail.com:587` with `starttls()`, login with `SMTP_FROM_EMAIL` and `SMTP_APP_PASSWORD` from env
- Subject line: `"OpportunIQ: {subject}"`
- Wrap in `try/except` — email failure must never crash the reminder pipeline (log it and continue)

**Complete `agents/notifier_agent.py`** by implementing `send_reminder()` fully:
```python
async def send_reminder(deadline_id: str, profile_id: str):
    # Step 1: Load deadline from deadline_registry
    # Step 2: Load student profile from student_profiles
    # Step 3: Compute days_left = (deadline_dt - now).days
    # Step 4: Call groq_service.generate_reminder(name, skills, title, dt, days_left)
    # Step 5: Save to notifications table (channel='dashboard')
    # Step 6: emit_trace() to push WebSocket notification event
    # Step 7: email_service.send_reminder_email(profile.email, message.subject, message.body)
    # Step 8: Save to notifications table again (channel='email')
    pass  # implement each step
```

**Test SMTP before the hackathon ends:**
```python
from services.email_service import send_reminder_email
send_reminder_email("your_email@gmail.com", "Test", "This is a test reminder from OpportunIQ.")
# Confirm the email arrives in inbox
```

---

**✅ Phase 6 done when:**
- Add a deadline manually → 4 APScheduler jobs created (visible in scheduler job list)
- Click "Test Reminder" (Notifier Agent called directly) → notification appears in bell dropdown within 5 seconds AND email arrives in inbox within 10 seconds
- Deadline calendar shows all deadlines with correct colour coding
- Click a calendar event → popup shows time remaining correctly
- Delete a deadline → calendar updates + APScheduler jobs cancelled

**🔁 Sync point:** All three test the test reminder flow together. Sanjay confirms the email arrives. Gowri confirms the bell badge increments. Anantha confirms the scheduler job was created and the notification was saved to DB.

---

## Phase 7 — Remaining Pages & Skill Gap
### Hours 18–26 | Full parallel

---

### Anantha Ram G S

**Build `routers/saved.py`:**
- `POST /api/saved/{opportunity_id}` → insert into `saved_opportunities` with `status = "Not Applied"` → return `{ "saved_id": ... }`
- `GET /api/saved` → join `saved_opportunities` with `opportunities` → return full details with current status
- `PATCH /api/saved/{id}` → update `status` field + `updated_at`
- `DELETE /api/saved/{id}` → remove from `saved_opportunities`

**Build skill gap endpoint in `routers/opportunities.py`:**
- `GET /api/opportunities/{id}/skill-gap?profile_id=X`
- Return `{ "matched": [...], "partial": [...], "missing": [...] }`
- Use `sentence_transformers` cosine similarity > 0.7 for partial matches

**Build `routers/notifications.py`:**
- `GET /api/notifications` → fetch all, accept `?unread=true` filter
- `PATCH /api/notifications/{id}/read` → set `is_read = true`
- `PATCH /api/notifications/read-all` → set `is_read = true` for all

**Build `routers/settings.py`:**
- `GET /api/settings/notifications` → return reminder preferences (store in a simple `settings` table or in SQLite `student_profiles`)
- `PUT /api/settings/notifications` → update preferences

---

### Gowri J S

**Build `SavedOpportunities.jsx`:**
- Stats row: 4 summary cards (Total Saved / Applied / Interview / Offers) — compute from the list
- Table with columns: Company | Title | Platform | Status | Deadline | Saved At | Actions
- `StatusDropdown` per row: `select` element with options and colour-coded text (Not Applied = grey, Applied = blue, Interview = amber, Offer = green, Rejected = red)
- On status change → `PATCH /api/saved/{id}` immediately (no save button needed)
- Delete icon → `DELETE /api/saved/{id}` → remove row

**Build `Notifications.jsx`:**
- Two tabs: "Unread" / "All" — filter from the same `GET /api/notifications` response
- Each notification card: bell icon + message text + timestamp + "Mark read" button
- Unread cards: light amber background
- "Mark all read" button → `PATCH /api/notifications/read-all`

**Build `Settings.jsx`:**
- 6 accordion sections (click header to expand/collapse):
  1. My Profile (same form as review, editable inline)
  2. Skills & Preferences (TagInput for skills and target roles)
  3. Gmail Integration (status + last scanned + "Re-scan" + "Disconnect" buttons)
  4. Reminder Preferences (4 toggle switches: 7 days / 3 days / 1 day / same day)
  5. Test Reminder (dropdown to select a deadline + "Fire Test Reminder Now" button)
  6. Danger Zone ("Delete all data" with confirmation modal)

**Build `OpportunityDetailDrawer.jsx`:**
- Slides in from the right (400px) when a card is clicked
- Full job description text
- Skill gap section: call `GET /api/opportunities/{id}/skill-gap` → render matched ✓ (green), partial ~ (amber), missing ✗ (red)
- "Apply Now" button → opens opportunity URL in new tab
- "Save" / "Unsave" toggle → `POST /api/saved/{id}` or `DELETE /api/saved/{id}`
- "Add Deadline" quick-action → opens `DeadlineForm` with title and org pre-filled

---

### Sanjay Anand M

**Wire `send_reminder()` to WebSocket push:**
- After saving notification to DB, call the global `emit_trace()` function from `main.py` with `agent="notifier"`, `status="notification"`, and the notification message as the payload
- This is what updates the bell badge in real time without a page reload

**Build the demo fallback cache:**
- Write a Python script `seed_demo_opportunities.py` that inserts 15 realistic opportunity records directly into the `opportunities` SQLite table
- Include a mix of: 5 LinkedIn jobs, 3 Naukri jobs, 3 Unstop hackathons, 2 Devfolio hackathons, 2 company portals
- Include realistic skills, deadlines (some in 2 days, some in 7 days, some in 14 days), and match scores
- This cache is your presentation safety net if live search is slow during the demo

**Pre-load the demo Gmail account:**
- Confirm the 8–10 seeded emails from Step 0 are still in the inbox
- Run the Guardian Agent manually against this account and confirm deadlines are extracted:
  ```python
  import asyncio
  from agents.guardian_agent import run_guardian_agent
  asyncio.run(run_guardian_agent(profile_id="demo_profile_id"))
  ```
- Confirm at least 5 deadlines appear in `deadline_registry`

---

**✅ Phase 7 done when:**
- Save an opportunity from a card → appears in Saved tab with "Not Applied" status → change to "Applied" → persists on refresh
- Click any opportunity card → detail drawer shows skill gap with ✓ / ~ / ✗ labels correctly
- Notifications page shows all notifications, mark-read works
- Settings page: all 6 accordion sections open and close, Test Reminder fires immediately
- Demo opportunity cache is loaded and visible in the feed as fallback

**🔁 Sync point:** All three do a full feature walkthrough together. Each person tests the other's work to catch integration issues before polish begins.

---

## Phase 8 — Polish, Integration Testing & Demo Rehearsal
### Hours 26–32 | Full parallel

---

### Anantha Ram G S — Backend Hardening

- Add `try/except` around every external API call. Return `{ "error": "...", "fallback": "..." }` — never let an exception return a 500 with a stack trace
- Add result caching: if the same `profile_id` has searched within the last 30 minutes, return cached results from SQLite instead of calling JobSpy/Tavily again (saves credits and avoids rate limits during the demo)
- Test the Gmail 3-pass fetch against the pre-seeded demo account — confirm it catches all 8–10 emails
- Verify APScheduler: add a deadline → print scheduler jobs → confirm 4 jobs exist → delete the deadline → confirm 4 jobs are removed
- Run `GET /api/profile/{id}`, `GET /api/opportunities`, `GET /api/deadlines`, `GET /api/notifications` in sequence and confirm all return correct data

---

### Gowri J S — Frontend Polish

- Add loading skeleton cards on the opportunity feed while `POST /api/opportunities/search` is running (prevents the grid from jumping from empty to full)
- Add empty state views for: no opportunities (with "Find Opportunities" CTA), no deadlines (with "Add Deadline" CTA), no notifications (with "You're all caught up ✓" message)
- Add toast notifications (`lucide-react` `Toast` or a simple custom implementation) for all form submissions — success: green toast, error: red toast
- Verify all API error states show a banner instead of a blank screen or console error
- Test all 9 pages on a narrower window (1024px) — fix any overflow or broken layout

---

### Sanjay Anand M — Demo Preparation

- Load the 2 demo resume PDFs into the system: upload each through the UI, complete the profile review, and save both profiles
- Run the complete demo flow 3 times from start to finish, timing each run. Target: under 6 minutes
  - Resume upload → profile review → confirm → find opportunities → view a card → save it → connect Gmail → view calendar → test reminder → check notifications
- Prepare the "Test Reminder" demo sequence precisely:
  - Select the SIH deadline from the dropdown → click "Fire Now" → switch to bell icon → show notification arrived → switch to Gmail inbox tab → show email arrived
- Confirm the demo opportunity fallback cache has 15 results and they look realistic
- Prepare the pitch talking points for each slide — 1 sentence per slide that Sanjay delivers while the other two do the live demo

---

**✅ Phase 8 done when:**
- Full demo flow runs cleanly twice in a row in under 6 minutes
- No 500 errors anywhere in the backend logs
- All empty states are handled with proper UI
- Toast notifications appear on all form submissions
- "Test Reminder" → notification + email both arrive consistently

---

## Phase 9 — PPT Finalisation & Presentation Prep
### Hours 30–36 | Sanjay leads, others contribute

---

### Anantha Ram G S

- Review system architecture slide — confirm the diagram matches the built system exactly
- Write 2–3 bullet points for the "Impact" slide from your own perspective as the backend engineer
- Be available for any last-minute backend fixes if the demo reveals a bug during rehearsal

---

### Gowri J S

- Review all frontend pages one final time — fix any visual issues noticed during rehearsal
- Take screenshots of each major page for the PPT (opportunity feed, calendar, notification bell, settings)
- Write 2–3 bullet points for the "Key Features" slide from the frontend perspective

---

### Sanjay Anand M

- Finalise the PPT slides using the content from the Beamer `.tex` file
- Add screenshots from Gowri's captures to the "Implementation Progress" slide
- Rehearse the presentation once with all three as an audience
- Prepare concise answers for likely judge questions:
  - "What is your novelty over existing platforms?" → 6 gaps identified in literature survey, none closed by existing tools
  - "How do you handle rate limiting on LinkedIn?" → JobSpy with proxy rotation; Tavily as fallback
  - "Is Gmail data secure?" → read-only OAuth scope, no data stored externally, only deadlines extracted
  - "How does this become a product?" → refer to the final PPT slide on industry conversion

---

**✅ Phase 9 done when:**
- PPT is complete with screenshots of the actual built system
- All three have rehearsed the demo flow at least once as a group
- Answers to 4 likely judge questions are prepared

---

## Shared Rules — Read These Before Starting

**Git discipline:**
- Commit and push after completing every file. Commit message format: `[Step N] short description`
- Never commit `.env`, `token.json`, `credentials.json`, or `*.db`
- If two people edit the same file, coordinate on Slack/WhatsApp before pushing

**Blocking dependency rules:**
- Gowri can build any page using mock data from `mockData.js` — do not wait for Anantha's routes to be ready
- Sanjay's services must be complete before Anantha can wire them into the routers — communicate when each service file is ready
- Anantha's routes must return at least a stub response before Gowri connects the real API

**If something breaks:**
- Paste the error in the group chat immediately — do not spend more than 15 minutes debugging alone
- If an external API (Tavily, Groq, Gmail) fails, use the fallback cache / mock data and continue
- If JobSpy rate-limits during the demo, the cached 15 opportunities will display automatically

**Demo safety net:**
- The cached 15 opportunities in SQLite are always there regardless of whether live search works
- The manual deadline entry form works regardless of whether Gmail OAuth works
- The "Test Reminder" button works regardless of whether APScheduler has scheduled jobs

---

## Hour-by-Hour Summary

| Hours | Anantha Ram G S | Gowri J S | Sanjay Anand M |
|---|---|---|---|
| 0–1 | Backend folder structure + main.py | React Vite setup + all page stubs | database.py + models.py + .env |
| 1–4 | `routers/profile.py` (4 endpoints) | `ResumeUpload.jsx` + `ManualForm.jsx` + `ProfileReview.jsx` | `resume_service.py` (forward + map) |
| 4–8 | `routers/opportunities.py` + `jobspy_service.py` | Start `Dashboard.jsx` layout + `OpportunityCard.jsx` | `tavily_service.py` + `groq_service.py` |
| 8–12 | WebSocket endpoint + `emit_trace()` | `AgentTracePanel.jsx` + mock data integration | `ranker_service.py` (dedup + score) |
| 12–16 | `routers/gmail.py` (5 endpoints) | `GmailConnectCard.jsx` + `DeadlineForm.jsx` | `gmail_service.py` + `guardian_agent.py` |
| 14–20 | `scheduler_service.py` + `routers/deadlines.py` + test reminder endpoint | `DeadlineCalendar.jsx` + `NotificationBell.jsx` | `email_service.py` + complete `send_reminder()` |
| 18–26 | `routers/saved.py` + skill gap + `routers/notifications.py` | `SavedOpportunities.jsx` + `Notifications.jsx` + `Settings.jsx` + `OpportunityDetailDrawer.jsx` | WebSocket push wiring + demo cache + demo Gmail prep |
| 26–32 | Backend hardening + caching + integration testing | Frontend polish + empty states + toasts | Full demo rehearsal (3 runs) + pitch prep |
| 30–36 | Review arch slide + answer prep | Screenshots + feature slide | PPT finalisation + presentation rehearsal |

---

*Work Plan v1.0 — OpportunIQ | TATA Centre AI/ML Hackathon*
*Anantha Ram G S · Gowri J S · Sanjay Anand M | NIT Tiruchirappalli*
