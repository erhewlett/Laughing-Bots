"""Auth endpoints - register, login, current user.

SCAFFOLD - contract is final, bodies are TODO (return 501 so /docs shows the
full planned API for the frontend team).

Frontend contract:
  POST /auth/register  {username, password, email?, name?}      -> 201 {user_id, username}
  POST /auth/login     {username, password}                     -> 200 {access_token, token_type}
  GET  /auth/me        (Bearer token)                           -> 200 {user_id, username, target_role, ...}

Validation errors return 422 with a message the frontend can display
(requirement: "display an error if username or password input is empty").
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest):
    # TODO(auth):
    #   1. err = security.validate_username(req.username); 422 if err
    #      (schema already enforces non-empty password)
    #   2. reject if username already taken -> 409
    #   3. user = models.User(username=..., password_hash=security.hash_password(...))
    #   4. db.add / commit / refresh; return user
    raise HTTPException(501, "Not implemented yet - auth milestone")


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    # TODO(auth):
    #   1. look up user by username; verify_password against stored hash
    #   2. identical 401 message for unknown-user vs wrong-password
    #      (don't leak which usernames exist)
    #   3. return {"access_token": create_access_token(user.user_id), "token_type": "bearer"}
    raise HTTPException(501, "Not implemented yet - auth milestone")


@router.get("/me", response_model=UserOut)
def me():
    # TODO(auth): user = Depends(security.get_current_user); return user
    raise HTTPException(501, "Not implemented yet - auth milestone")
