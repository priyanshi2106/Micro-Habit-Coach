# Micro Habit Coach

A minimal habit coaching app that suggests one habit at the right time each day, based on your free schedule and habit category preferences.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS v3 |
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL (via Docker) |

---

## Running locally

**Prerequisites:** Docker Desktop, Python 3.9+, Node.js 18+

```bash
# 1. Start Postgres
docker compose up -d

# 2. Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# 3. Start frontend (new terminal)
cd frontend
npm run dev
```

App: http://localhost:3000  
API docs: http://localhost:8000/docs

---

## Architecture

Modular monolith. Each domain (users, habits, schedules, suggestions, habit_logs) has its own `models.py`, `schemas.py`, `service.py` under `backend/app/modules/`. Routers are thin — business logic lives in services.

---

## Product rules

### Streak calculation (v1.2)

`current_streak` counts consecutive calendar days on which the user has at least one log with status `"done"`.

**Key rule:** if the user has not completed a habit yet today, the streak is not considered broken until a full day has passed without a done log. A streak of N shown today means the user was consistent through at least yesterday, and today still has an opportunity to extend it.

This is an intentional product decision — not a technical accident — to avoid penalising users who open the app early in the day before completing their habit.

---

## Identity (v1 shortcut)

User identity is a UUID stored in `localStorage` under the key `micro_habit_user_id` and sent as the `X-User-Id` header on every API request. There is no authentication in v1. Clearing localStorage loses the account.

---

## Deferred

- Real authentication
- Push notifications / reminders
- AI-powered suggestions (engine is rule-based in v1)
- Calendar integration
