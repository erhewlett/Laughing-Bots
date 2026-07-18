"""Auth endpoints: register, login, current user.

  POST /auth/register  {username, password, email?, name?}  -> 201 UserOut
  POST /auth/login     {username, password}                 -> 200 {access_token}
  GET  /auth/me        (Bearer token)                       -> 200 UserOut

Login returns one generic 401 for both unknown-username and wrong-password so
it does not reveal which usernames exist.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import security

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> models.User:
    err = security.validate_username(req.username)
    if err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, err)

    if security.get_user_by_username(db, req.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username is already taken.")
    if req.email and db.scalar(
        select(models.User).where(models.User.email == req.email)
    ) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered.")

    user = models.User(
        username=req.username,
        password_hash=security.hash_password(req.password),
        email=req.email,
        name=req.name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Backstop for a race between the checks above and commit.
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Username or email is already in use."
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = security.get_user_by_username(db, req.username)
    # Always run exactly one bcrypt verify (against a dummy hash when the
    # username is unknown) so both failure kinds take the same time and
    # response timing cannot be used to enumerate usernames.
    stored_hash = (
        user.password_hash if user is not None else security.DUMMY_PASSWORD_HASH
    )
    password_ok = security.verify_password(req.password, stored_hash)
    if user is None or not password_ok:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=security.create_access_token(user.user_id))


@router.get("/me", response_model=UserOut)
def me(user: models.User = Depends(security.get_current_user)) -> models.User:
    return user
