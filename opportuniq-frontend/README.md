# OpportunIQ Frontend

OpportunIQ is an AI-powered opportunity intelligence platform for students. The frontend is a React + Vite dashboard for resume onboarding, profile review, opportunity discovery, deadline tracking, saved opportunities, Gmail-assisted reminders, notifications and settings.

## Technology Stack

- React 18
- Vite
- React Router DOM
- Axios
- TailwindCSS package present, with project CSS in `src/styles/globals.css`
- Lucide React
- FullCalendar

## Frontend Architecture

```text
src/
├── api/                 Shared Axios API modules
├── components/
│   ├── common/          Reusable UI primitives, states, dialogs, toasts
│   ├── layout/          Dashboard shell, navigation, panels
│   ├── onboarding/      Upload/profile review form components
│   ├── dashboard/       Opportunity, Gmail, trace, notification widgets
│   ├── calendar/        Deadline form/detail components
│   └── settings/        Settings page primitives
├── constants/           Route and navigation constants
├── contexts/            App-level profile context
├── hooks/               Local storage, toast, WebSocket, focus helpers
├── pages/               Route-level pages, lazy-loaded
├── styles/              Global design system CSS
└── utils/               Feature-specific helpers and adapters
```

## Environment Variables

Create `.env` in the frontend root when overriding local defaults:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

If omitted, the app defaults to the same localhost values.

## Setup

```bash
npm install
npm run dev
```

The app will start on `http://localhost:5173` unless that port is occupied.

## Available Scripts

```bash
npm run dev       # Start Vite dev server
npm run build     # Production build
npm run lint      # ESLint audit
npm run preview   # Preview production build
```

## Backend Integration

The frontend expects the backend at `VITE_API_BASE_URL` and uses the shared Axios client in `src/api/client.js`. WebSocket features use `VITE_WS_BASE_URL`.

Important integrated areas:

- Resume upload: `POST /api/profile/upload`
- Profile: `GET/PATCH /api/profile/{profile_id}`
- Opportunities and saved tracker
- Deadlines calendar and CRUD
- Gmail status, scan and disconnect
- Notifications and WebSocket updates

## Release Notes

- Route-level lazy loading is enabled for faster initial load.
- A global Error Boundary protects the app shell and provides recovery actions.
- Unknown routes render a polished fallback page.
- Shared UI primitives live in `src/components/common`.
- Lint and production build should pass before every demo.

## Contributors

- Gowri
- OpportunIQ Hackathon Team
