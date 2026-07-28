"""JobHopper backend - FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

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
        # Auth signs tokens with the key cached in backend/.dev_secret when
        # SECRET_KEY is unset (see services/security.py). Sessions survive a
        # restart, but the key is local to this checkout.
        print(
            "\n*** SECRET_KEY is unset; login tokens are signed with the "
            "development key in backend/.dev_secret. Fine for local work. "
            "Set SECRET_KEY in backend/.env before deploying anywhere. ***\n"
        )
    yield


app = FastAPI(title="JobHopper API", version="0.1.0", lifespan=lifespan)

# Compress JSON before it goes out. The quiz payload (10 questions x 4 options)
# and the word cloud are repetitive JSON that gzip cuts by roughly two thirds.
# Added BEFORE CORS on purpose: Starlette makes the last-added middleware the
# outermost, so this ordering keeps CORS outermost and preflight/error
# responses still carry CORS headers.
app.add_middleware(GZipMiddleware, minimum_size=500)

# Only the methods/headers the API actually uses (review hardening) - origins
# were already restricted to the configured frontend hosts.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return validation errors with `detail` as a plain string.

    FastAPI's default 422 sends `detail` as a list of error objects, while every
    HTTPException we raise sends a string. Callers that do the obvious thing
    (`alert(body.detail)`) render "[object Object]" on the list form, and a
    couple of the page scripts do exactly that. Flattening here means one
    predictable error shape for every non-2xx response, so no caller has to
    special-case validation failures.
    """
    errors = exc.errors()
    if not errors:
        return JSONResponse(status_code=422, content={"detail": "Invalid input."})

    first = errors[0]
    message = first.get("msg", "Invalid input.")
    # Custom field validators surface as "Value error, <our message>"; the
    # prefix is pydantic bookkeeping and means nothing to a player.
    if message.startswith("Value error, "):
        message = message[len("Value error, ") :]

    # loc is like ("body", "elapsed_seconds"); name the field when there is one
    # so "elapsed_seconds: Input should be >= 0" beats a bare "Input should...".
    # Skip the location kind, and skip non-string parts: a malformed body gives
    # loc=("body", 0) where 0 is a character offset, not a field, and rendering
    # it produced "0: JSON decode error". List indices inside a body are kept,
    # so nested errors still read as "answers.0.question_id: ...".
    parts = first.get("loc", ())
    location = [
        str(part)
        for i, part in enumerate(parts)
        if not (i == 0 and part in {"body", "query", "path", "header", "cookie"})
        and not (isinstance(part, int) and len(parts) == 2)
    ]
    if location:
        message = f"{'.'.join(location)}: {message}"

    return JSONResponse(status_code=422, content={"detail": message})


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
