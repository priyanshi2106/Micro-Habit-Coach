from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import habit_logs, habits, schedule_blocks, suggestions, users
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

# Allow the Next.js dev server and any configured frontend origin.
# Tighten this list before going to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(habits.router)
app.include_router(schedule_blocks.router)
app.include_router(suggestions.router)
app.include_router(habit_logs.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
