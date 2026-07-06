"""JobHopper backend - FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine

# Import models so they register with Base.metadata before create_all runs.
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skeleton stage: create tables directly. Swap for Alembic migrations later.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="JobHopper API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


from app.routers import wordcloud

app.include_router(wordcloud.router)

# Remaining routers (auth, game, roadmap) get wired here as they're built.
