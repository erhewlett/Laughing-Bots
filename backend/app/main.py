"""JobHopper backend - FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.autoseed import autoseed
from app.config import settings
from app.database import initialize_database

# Import models so they register before database initialization runs.
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    autoseed()
    if settings.secret_is_default:
        # Auth signs tokens with a random per-process key when SECRET_KEY is
        # unset (see services/security.py). Tokens will not survive a restart.
        print(
            "\n*** WARNING: SECRET_KEY is unset; login tokens use a random "
            "per-process key and reset on restart. Set SECRET_KEY in "
            "backend/.env for stable sessions. ***\n"
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

app.include_router(wordcloud.router)
app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(game.router)
app.include_router(roadmap.router)
app.include_router(history.router)
