"""Password hashing (bcrypt), JWT access tokens, and the auth dependencies.

Passwords are bcrypt-hashed; only the hash is stored (User.password_hash).
Access tokens are signed JWTs (HS256, 24h). If SECRET_KEY is left at the
default placeholder, a random per-process key is used instead so tokens are
never signed with a publicly known value (they will not survive a restart;
set SECRET_KEY in backend/.env for stable sessions).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import get_db

USERNAME_MIN, USERNAME_MAX = 4, 16
PASSWORD_MIN, PASSWORD_MAX = 8, 20
TOKEN_TTL_HOURS = 24
ALGORITHM = "HS256"
PASSWORD_MAX_BYTES = 72  # bcrypt rejects inputs longer than this; validated at register

# auto_error=False so we can return the same 401 for missing and invalid tokens.
bearer = HTTPBearer(auto_error=False)

# Used only when SECRET_KEY is the default placeholder (see module docstring).
_EPHEMERAL_SECRET = secrets.token_hex(32)


def _secret() -> str:
    return _EPHEMERAL_SECRET if settings.secret_is_default else settings.secret_key


def _pw_bytes(plain: str) -> bytes:
    # No truncation: register rejects over-72-byte passwords (see RegisterRequest),
    # so distinct passwords are never collapsed to the same 72-byte prefix.
    return plain.encode("utf-8")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_pw_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False  # malformed stored hash


def validate_username(username: str) -> str | None:
    """Return an error message if the username breaks the rules, else None.

    Rules: not empty, 4 to 16 characters, letters and digits only. (The request
    schema enforces the same rules; this is the server-side backstop.)
    """
    if not username or not username.strip():
        return "Username is required."
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        return f"Username must be {USERNAME_MIN} to {USERNAME_MAX} characters."
    if not username.isascii() or not username.isalnum():
        return "Username may contain only letters and numbers."
    return None


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def _user_from_token(token: str, db: Session) -> models.User | None:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    return db.get(models.User, user_id)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User:
    """Require a valid bearer token; 401 otherwise."""
    user = _user_from_token(creds.credentials, db) if creds else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User | None:
    """Return the user if a valid token is present, else None (anonymous ok)."""
    return _user_from_token(creds.credentials, db) if creds else None


def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.scalar(select(models.User).where(models.User.username == username))
