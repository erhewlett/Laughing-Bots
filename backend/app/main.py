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
    if settings.secret_is_default:
        # review #2: loud warning now; MUST become `raise RuntimeError` when
        # the auth milestone starts signing tokens with this key.
        print(
            "\n*** WARNING: SECRET_KEY is the built-in default. "
            "Set a real one in backend/.env before implementing auth. ***\n"
        )
    yield


app = FastAPI(title="JobHopper API", version="0.1.0", lifespan=lifespan)

# Only the methods/headers the API actually uses (review hardening) - origins
# were already restricted to the configured frontend hosts.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


from app.routers import auth, game, history, meta, roadmap, wordcloud

app.include_router(wordcloud.router)   # implemented
app.include_router(meta.router)        # implemented
app.include_router(auth.router)        # scaffold (501): auth milestone
app.include_router(game.router)        # scaffold (501): game milestone
app.include_router(roadmap.router)     # scaffold (501): roadmap milestone
app.include_router(history.router)     # scaffold (501): history milestone
