# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered meeting booking application. Users see intelligently ranked available time slots (ranked by Gemini 2.0 Flash via LangChain) from the owner's Google Calendar, then book a slot which creates a calendar event with Google Meet.

## Tech Stack

- **Backend**: Python 3.9.6, FastAPI, LangChain + Google Gemini, Google Calendar API, SQLAlchemy, Pydantic
- **Frontend**: React 19 (JavaScript, not TypeScript), Axios, Create React App

## Commands

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (from repo root)
cd backend && uvicorn app.main:app --reload

# Run all tests
cd backend && pytest

# Run a single test file
cd backend && pytest tests/test_services.py

# Run a specific test
cd backend && pytest tests/test_services.py::test_function_name -v
```

### Frontend

```bash
cd frontend
npm install      # Install dependencies
npm start        # Dev server (port 3000)
npm test         # Run tests (Jest + React Testing Library)
npm run build    # Production build
```

## Architecture

```
Frontend (React)                    Backend (FastAPI)
─────────────────                   ─────────────────
App.js                              api/routes.py
├─ Header                             POST /booking/suggest-ai  ← main flow
├─ UserForm (name/email)               POST /booking/book
├─ SlotList (grouped by date)          GET  /calendar/events
├─ FeedbackForm (refine AI)            GET  /preferences
└─ DebugPanel (LLM inspect)           POST /preferences
                                       GET  /authorize (OAuth)
useBooking hook                        GET  /oauth2callback
 └─ services/api.js (Axios)
```

### Key User Flow

1. Frontend calls `POST /booking/suggest-ai` with timezone and optional feedback text
2. `services/calendar.py` generates all legal 1-hour slots (next 7 days, 7am–10pm, excluding busy events and `no_meetings` rules from `preferences.json`)
3. `services/ai_service.py` uses LangChain + Gemini 2.0 Flash to rank and select 5–10 best slots based on owner preferences and user feedback
4. Frontend displays ranked slots grouped by date
5. User fills in name/email, selects a slot → `POST /booking/book` creates Google Calendar event with Meet link

### Backend Service Layer

- **`services/calendar.py`** — Slot generation, busy-time detection, Google Calendar event creation. Handles timezone math with `zoneinfo`.
- **`services/ai_service.py`** — LangChain agent with `get_days_of_week` tool. Validates LLM output against legal slots to prevent hallucination. Falls back to raw slots if LLM fails.
- **`services/google_auth.py`** — OAuth2 flow, token persistence (env vars in production, `tokens.json` locally)
- **`services/preferences.py`** — Read/write owner preferences (`no_meetings` blocked ranges, `batch_meetings` flag)
- **`core/config.py`** — Pydantic Settings. Priority: env vars > local JSON files (`secrets.json`, `tokens.json`)

### Frontend Structure

- **`hooks/useBooking.js`** — Central state management hook for the booking flow (fetching slots, booking, feedback)
- **`services/api.js`** — Axios client; uses `REACT_APP_API_URL` env var (defaults to `http://localhost:8000`)
- **`components/`** — Header, UserForm, SlotList, FeedbackForm, DebugPanel

## Configuration

### Required Environment Variables

- `GOOGLE_AI_API_KEY` — For AI slot ranking (Gemini, via Google AI Studio)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` — Google OAuth
- `GOOGLE_SECRETS_JSON` — Full OAuth secrets JSON (production)
- `GOOGLE_TOKEN_JSON` — User tokens JSON (production)
- `ALLOWED_ORIGINS` — Comma-separated CORS origins (defaults to `http://localhost:3000`)
- `REACT_APP_API_URL` — Backend URL for frontend (defaults to localhost:8000)

### Local Development Files (not in git)

- `backend/secrets.json` — Google OAuth credentials
- `backend/tokens.json` — Generated after first OAuth login
- `backend/preferences.json` — Owner booking preferences (committed)

## Deployment

Heroku via `Procfile`: `web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
