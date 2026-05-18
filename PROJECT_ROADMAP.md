# Micro-Habit Coach — Cursor Build Roadmap

## Project Goal

Build a calm, AI-assisted micro-habit coaching app that helps users complete tiny habits at the right time instead of relying on fixed reminders. The core product idea is to suggest the best 2–5 minute habit window based on the user's routine, then improve over time using completion history, calendar data, and AI insights.

This project should be built as a **modular monolith** so V1 can ship quickly, while V2 and V3 can be added without a rewrite. Scalable MVP guidance consistently recommends modular architecture and clear service boundaries instead of premature microservices.[cite:384][cite:386]

---

## Product Vision

The app should answer one core question every time the user opens it:

**What is the best tiny habit for me to do right now?**

The app is not a generic habit tracker. It is a personalized habit coach that uses schedule-aware suggestions, completion logs, and eventually calendar and AI context to recommend habits at the right moment. MVP and AI product roadmaps consistently emphasize validating one narrow high-value use case before broadening scope.[cite:407][cite:408][cite:414]

---

## Version Strategy

### V1 — Prove the Core Loop

Goal: prove that smart timing plus tiny habits is useful.

**Core loop:**
1. User sets goals and daily schedule.
2. App suggests one micro-habit in the best available time window.
3. User marks Done / Snooze / Skip.
4. App logs behavior.
5. Weekly AI insight summarizes patterns.

**V1 features:**
- Authentication
- Onboarding flow
- Habit library + custom habits
- Manual schedule blocks
- Rule-based suggestion engine
- Home screen with one main suggestion
- Habit check-in actions
- Progress page
- Weekly AI summary
- Event logging foundation

### V2 — Make Timing Smarter

Goal: improve recommendation quality using real behavior and real availability.

**V2 features:**
- Adaptive suggestion engine using completion history
- Confidence score for suggestions
- Habit anchors / habit stacking
- Read-only Google Calendar integration
- Notification system
- Better analytics and timing heatmaps

### V3 — Add AI Depth

Goal: turn the app into a truly intelligent coach.

**V3 features:**
- RAG over habit-science content
- Energy and mood-aware recommendations
- AI habit recommendations based on user behavior
- Better explanation layer: why this habit, why this time
- LLM observability and evaluation

### V4 — Scale Product Surface

Possible future:
- Accountability buddy
- Coach mode
- Habit templates
- PWA/mobile packaging
- Monetization

---

## Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| IDE | Cursor | Best fit for solo full-stack iteration and fast editing workflows |
| Frontend | Next.js + TypeScript | Strong for app UI, routing, and long-term maintainability |
| Backend | FastAPI + Python | Excellent fit for APIs, scheduling logic, and AI integrations |
| Database | PostgreSQL | Best for structured product data and analytics |
| Local infra | Docker Compose | Easy local development with backend + DB |
| AI provider | OpenAI or Gemini | Good fit for weekly summaries and recommendation explanations |
| Frontend AI layer | Vercel AI SDK (optional in V1) | Useful for typed structured outputs in Next.js UI flows |
| Background jobs | APScheduler first, Celery later if needed | Keeps V1 simple and future-proof |
| Vector support | pgvector in V3 | Adds RAG without a separate vector DB |

Modern full-stack AI app guidance commonly recommends a frontend layer, backend layer, and separate AI/data layer rather than blending AI logic directly into UI code.[cite:388][cite:391]

---

## Architecture Principle

Build V1 as a **modular monolith**:
- one frontend app
- one backend app
- one database
- domain modules inside the backend

This is the right tradeoff for a solo developer because it is faster than microservices, but still structured enough for growth.[cite:384][cite:386]

### System shape

```text
Frontend (Next.js)
  -> talks to Backend API (FastAPI)
  -> renders onboarding, home, habits, progress, insights

Backend (FastAPI)
  -> handles auth, habits, schedules, suggestions, analytics, insights, AI
  -> runs scheduling logic
  -> stores logs and suggestions in Postgres

Database (PostgreSQL)
  -> users, habits, schedule_blocks, habit_logs, suggestions, insights, event_logs

Future AI/Data Layer (V2/V3)
  -> calendar integration
  -> RAG retrieval layer
  -> evaluation / observability
```

---

## Folder Structure

### Frontend

```text
frontend/
  app/
    onboarding/
    home/
    habits/
    progress/
    insights/
  components/
    ui/
    cards/
    forms/
    charts/
  features/
    habits/
    schedule/
    suggestions/
    insights/
  lib/
    api/
    types/
    utils/
    ai/
```

### Backend

```text
backend/
  app/
    api/
      routers/
    core/
      config.py
      database.py
      security.py
    modules/
      auth/
      users/
      habits/
      schedules/
      suggestions/
      insights/
      analytics/
      ai/
      common/
    tests/
```

This domain-first structure makes V2 and V3 much easier to add than a flat routes/models/utils layout.[cite:384][cite:388]

---

## Core Data Model

Plan the schema for future upgrades even if V1 does not use every field yet.

### Main entities
- `users`
- `habits`
- `schedule_blocks`
- `habit_logs`
- `habit_suggestions`
- `weekly_insights`
- `event_logs`
- `habit_anchors` (used later)
- `calendar_connections` (used later)

### Important future-ready fields
- `confidence_score`
- `source` (`manual`, `rule_engine`, `adaptive_engine`, `calendar`, `ai`)
- `anchor_event`
- `energy_level`
- `suggestion_reason`
- `model_version`
- `feedback_rating`

Scalable MVP guidance strongly recommends planning the data model early so future features can use historical logs without a schema rewrite.[cite:386][cite:390]

---

## API Surface to Lock Early

Keep the contracts stable even if the internals evolve.

### V1 endpoints
- `POST /users/onboarding`
- `GET /users/me`
- `GET /habits`
- `POST /habits`
- `PATCH /habits/:id`
- `GET /schedule-blocks`
- `POST /schedule-blocks`
- `GET /suggestions/today`
- `POST /habit-logs`
- `GET /progress/summary`
- `GET /insights/weekly`

### Future endpoints
- `POST /calendar/connect`
- `GET /calendar/status`
- `POST /anchors`
- `GET /analytics/heatmap`
- `POST /feedback/suggestion`

---

## Smart Timing Strategy

### V1
Use a deterministic rule-based engine.

Example rules:
- mindfulness -> morning free block
- movement -> morning or post-work free block
- learning -> lunch or evening free block
- productivity -> early workday free block
- finance -> any quiet free block
- social -> evening free block

The engine should:
1. Load today's schedule blocks
2. Find free windows
3. Match habit category to preferred time bucket
4. Pick the best window that fits the habit duration
5. Store the suggestion with `source = rule_engine`

### V2
Upgrade the engine using actual completion history.

New logic:
- compare suggested windows to completed times
- detect best-performing windows per habit/user
- increase `confidence_score` as data accumulates
- blend rule-based priors with observed behavior

### V3
Make the engine hybrid.

Combine:
- schedule data
- completion history
- calendar availability
- optional mood/energy signals
- AI explanation layer

---

## Google Calendar Plan

Google Calendar should **not** be part of V1. OAuth setup, token storage, consent screen configuration, and scope handling add real complexity, and MVP guidance consistently recommends deferring non-core integrations until the main value is validated.[cite:397][cite:403][cite:404]

### When to add it
Add direct Google Calendar reading in **V2** after:
- V1 core loop works
- suggestion logic feels useful
- manual schedule blocks feel limiting

### How to design for it now
- keep `schedule_blocks`
- add `calendar_connections` later
- design suggestion logic to accept generic “availability windows” from either manual input or external integrations
- include `source` fields from day one

---

## UI/UX Direction

The app should feel:
- calm
- personal
- lightweight
- mobile-first
- not like a dense productivity dashboard

Good habit apps and dashboard best practices emphasize focusing the user on the next action instead of overwhelming them with too many metrics at once.[cite:365][cite:366][cite:372]

### Core screens
1. **Onboarding** — goals, schedule, first habits
2. **Home** — one best suggestion right now
3. **Habits** — manage habit list
4. **Progress** — streaks, completion, patterns
5. **Weekly Insight** — AI summary and recommendation

### Home screen structure
- greeting
- main suggestion card
- reason for timing
- done / snooze / skip actions
- mini summary stats
- link to weekly insight

The key design principle is: **show one important next action, not everything at once**.[cite:365][cite:370]

---

## AI Usage Plan

### V1
Keep AI narrow and useful:
- weekly summary
- onboarding explanation for suggested habits

### V2
Use AI for:
- habit stacking suggestions
- better recommendation explanations
- message personalization

### V3
Use AI for:
- RAG-grounded coaching
- habit science answers
- adaptive recommendations
- deeper personalization

### Important architectural rule
All LLM calls should go through a dedicated AI service layer, not directly from scattered routes or UI components. This makes it easier to swap providers, add RAG, or add observability later.[cite:388]

---

## Observability and Logging

Event logging should exist from V1 so V2 can learn from real usage.

### Events to track
- suggestion_shown
- suggestion_done
- suggestion_skipped
- suggestion_snoozed
- habit_created
- habit_updated
- insight_viewed
- onboarding_completed

Without event history, adaptive timing in V2 becomes much weaker. Product and MVP guides recommend building instrumentation early so iteration is based on actual behavior, not guesswork.[cite:409][cite:420]

---

## Build Roadmap

### Phase 0 — Planning (3–5 days)
- freeze V1 scope
- finalize schema
- finalize endpoints
- create repo and folder structure
- create issue/task board

### Phase 1 — Foundation (1 week)
- scaffold Next.js frontend
- scaffold FastAPI backend
- set up PostgreSQL + Docker Compose
- implement auth
- create base DB models and migrations

### Phase 2 — Core V1 Build (3–5 weeks)
- onboarding flow
- habit management
- schedule blocks
- rule-based suggestion engine
- daily suggestion screen
- habit logs
- progress summary
- weekly AI insight

### Phase 3 — Stabilization (1–2 weeks)
- fix edge cases
- improve onboarding friction
- refine suggestion logic
- polish UI
- deploy and test with real usage

### Phase 4 — V2 (3–4 weeks)
- adaptive timing
- confidence scoring
- habit anchors
- read-only Google Calendar integration
- notifications
- richer analytics

### Phase 5 — V3 (4–6 weeks)
- RAG layer
- mood / energy tracking
- AI recommendation engine
- observability + evaluation

---

## Success Criteria

### V1 success
- user can complete onboarding in one sitting
- app gives at least one believable daily suggestion
- check-in loop feels easy
- weekly insight feels personal, not generic

### V2 success
- suggestions improve based on behavior
- calendar data improves timing quality
- users trust the recommendation windows more

### V3 success
- AI explanations are grounded and useful
- recommendations feel distinctly personalized
- the app behaves like a real coach, not a reminder list

---

## Instructions for Cursor

Use this roadmap as the project brief.

### Implementation priorities
1. Build V1 only first.
2. Keep backend modular by domain.
3. Keep API contracts stable.
4. Add future-ready schema fields now.
5. Put all AI logic behind an `ai` service module.
6. Keep suggestion logic separate from routes.
7. Do not add Google Calendar until V2.
8. Do not use microservices.
9. Log key events from V1.
10. Optimize for a clean, working product over feature count.

### Coding philosophy
- simple first
- deterministic before intelligent
- manual before integrated
- modular before distributed
- usable before ambitious

---

## Immediate Next Steps

1. Create the monorepo with `frontend/` and `backend/`
2. Set up Docker Compose with PostgreSQL
3. Define DB schema and migrations
4. Implement backend modules for users, habits, schedules, suggestions
5. Build onboarding UI
6. Implement rule-based suggestion engine
7. Build home screen with daily suggestion card
8. Add weekly AI summary
9. Deploy locally and dogfood the app

