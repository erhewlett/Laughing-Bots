"""Password hashing + token helpers, and the auth dependency.

SCAFFOLD - signatures and plan only. Implement in the Auth milestone.

Design decisions (proposed):
  - Passwords: bcrypt via passlib (already in requirements).
  - Sessions: JWT bearer tokens (add `pyjwt` to requirements when implementing),
    signed with settings.secret_key, ~24h expiry. Simpler than server-side
    sessions for a split frontend/backend team.
  - Username rules (from requirements doc): 4-16 chars, alphanumeric only,
    non-empty username AND password.
  - Password length follows the frontend form: 8-20 characters.
"""
from __future__ import annotations

# TODO(auth): uncomment when implementing
# from passlib.context import CryptContext
# import jwt  # pyjwt - add to requirements.txt
# from datetime import datetime, timedelta, timezone
# from fastapi import Depends, HTTPException
# from fastapi.security import OAuth2PasswordBearer
# from app.config import settings

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

USERNAME_MIN, USERNAME_MAX = 4, 16
PASSWORD_MIN, PASSWORD_MAX = 8, 20


def hash_password(plain: str) -> str:
    """bcrypt-hash a password for storage in User.password_hash."""
    # TODO(auth): return pwd_context.hash(plain)
    raise NotImplementedError


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time check of a login attempt against the stored hash."""
    # TODO(auth): return pwd_context.verify(plain, hashed)
    raise NotImplementedError


def validate_username(username: str) -> str | None:
    """Return an error message if the username violates the requirements,
    else None.

    Rules (functional requirements):
      - not empty
      - 4 to 16 characters
      - no special characters (alphanumeric only)
    """
    # TODO(auth):
    #   if not username or not username.strip(): return "Username is required."
    #   if not (USERNAME_MIN <= len(username) <= USERNAME_MAX): return "..."
    #   if not username.isalnum(): return "Username may not contain special characters."
    raise NotImplementedError


def create_access_token(user_id: int) -> str:
    """Issue a signed JWT: {"sub": user_id, "exp": now+24h}."""
    # TODO(auth): jwt.encode({...}, settings.secret_key, algorithm="HS256")
    # NOTE: refuse to start if settings.secret_key is still the default -
    # see review finding #2.
    raise NotImplementedError


def get_current_user():  # -> models.User
    """FastAPI dependency: decode bearer token -> load User or 401.

    Usage in routers:  user: models.User = Depends(get_current_user)
    Also provide get_current_user_optional for endpoints that work both
    logged-in and anonymous (e.g. /wordcloud saves a Search only if logged in).
    """
    # TODO(auth): decode token, db.get(models.User, sub), 401 on failure
    raise NotImplementedError
