from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import anchors, auth, calendar, habit_logs, habits, insights, notifications, onboarding, schedule_blocks, suggestions, users
from app.core.config import get_settings
from app.core.database import get_engine, init_db_schema

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.create_tables_on_startup:
        await init_db_schema()
    yield
    await get_engine().dispose()


app = FastAPI(title="Micro Habit Coach API", lifespan=lifespan)

_settings = get_settings()
_allowed_origins = [
    "http://localhost:3000",
    "https://micro-habit-coach-frontend.vercel.app",  # deployed frontend
]
# Also include FRONTEND_URL from env if it differs (e.g. custom domain later).
if _settings.frontend_url and _settings.frontend_url not in _allowed_origins:
    _allowed_origins.append(_settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(anchors.router)
app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(notifications.router)
app.include_router(users.router)
app.include_router(habits.router)
app.include_router(schedule_blocks.router)
app.include_router(suggestions.router)
app.include_router(habit_logs.router)
app.include_router(insights.router)
app.include_router(onboarding.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
