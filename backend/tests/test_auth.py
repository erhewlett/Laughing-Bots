"""Auth tests: register, login, me, validation, and password hashing.

These are the acceptance criteria for the auth milestone.
"""
from __future__ import annotations

from app import models
from sqlalchemy import select


def _register(client, username="validuser", password="password123", **extra):
    return client.post(
        "/auth/register", json={"username": username, "password": password, **extra}
    )


def _login(client, username="validuser", password="password123"):
    return client.post("/auth/login", json={"username": username, "password": password})


# --- registration validation --------------------------------------------------

def test_register_password_too_short(client):
    assert _register(client, password="short").status_code == 422


def test_register_password_too_long(client):
    assert _register(client, password="x" * 21).status_code == 422


def test_register_username_too_short(client):
    assert _register(client, username="abc").status_code == 422


def test_register_username_too_long(client):
    assert _register(client, username="a" * 17).status_code == 422


def test_register_username_special_chars(client):
    assert _register(client, username="el!jah").status_code == 422


# --- registration success + conflict -----------------------------------------

def test_register_success_returns_user_without_password(client):
    r = _register(client, username="elijah1")
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "elijah1"
    assert "user_id" in body
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_username_conflicts(client):
    assert _register(client, username="dupe").status_code == 201
    assert _register(client, username="dupe").status_code == 409


def test_register_duplicate_email_conflicts(client):
    assert _register(client, username="userone", email="dup@x.com").status_code == 201
    # different username, same email -> controlled 409, not a 500
    assert _register(client, username="usertwo", email="dup@x.com").status_code == 409


def test_register_password_over_72_bytes_rejected(client):
    # 19 four-byte characters = 76 bytes but only 19 chars (within max_length),
    # so the byte-length check must reject it rather than truncate.
    pw = chr(0x1D51E) * 19
    assert _register(client, username="bigpw", password=pw).status_code == 422


def test_register_persists_email_and_name(client, db_session):
    _register(client, username="withinfo", email="e@x.com", name="Elijah")
    user = db_session.scalar(
        select(models.User).where(models.User.username == "withinfo")
    )
    assert user.email == "e@x.com" and user.name == "Elijah"


def test_password_is_stored_hashed_not_plaintext(client, db_session):
    _register(client, username="hashme", password="password123")
    user = db_session.scalar(
        select(models.User).where(models.User.username == "hashme")
    )
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")  # bcrypt hash marker


# --- login -------------------------------------------------------------------

def test_login_success_returns_token(client):
    _register(client, username="loginok")
    r = _login(client, username="loginok")
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_401(client):
    _register(client, username="wrongpw")
    assert _login(client, username="wrongpw", password="wrongpassword").status_code == 401


def test_login_unknown_user_same_401(client):
    unknown = _login(client, username="nobodyhere")
    assert unknown.status_code == 401
    # same generic message as a wrong password (no username enumeration)
    _register(client, username="realuser")
    wrong = _login(client, username="realuser", password="wrongpassword")
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_login_empty_password_422(client):
    assert _login(client, password="").status_code == 422


# --- /auth/me ----------------------------------------------------------------

def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_token_returns_current_user(client):
    _register(client, username="meuser")
    token = _login(client, username="meuser").json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "meuser"


def test_me_with_garbage_token_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_me_token_for_deleted_user_401(client, db_session):
    from sqlalchemy import delete

    _register(client, username="ghost")
    token = _login(client, username="ghost").json()["access_token"]
    db_session.execute(delete(models.User).where(models.User.username == "ghost"))
    db_session.commit()
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401  # valid signature, but the user no longer exists


# --- register returns a usable token ----------------------------------------


def test_register_returns_token_and_user(client):
    """One call, not register-then-login with a failure window between."""
    r = client.post(
        "/auth/register", json={"username": "onecall", "password": "password123"}
    )

    assert r.status_code == 201
    body = r.json()
    # original UserOut fields still present for callers that only read user data
    assert body["username"] == "onecall" and body["user_id"] >= 1
    assert body["token_type"] == "bearer" and body["access_token"]


def test_register_token_authenticates_immediately(client):
    """The returned token works without a separate login round trip."""
    token = client.post(
        "/auth/register", json={"username": "straight", "password": "password123"}
    ).json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200 and me.json()["username"] == "straight"


# --- one predictable error shape ---------------------------------------------


def test_validation_errors_return_string_detail(client):
    """422 detail is a string, like every HTTPException we raise.

    FastAPI's default sends a list of error objects, which callers that do
    alert(body.detail) render as "[object Object]".
    """
    # valid username so password is the first field that fails
    r = client.post("/auth/register", json={"username": "validname"})

    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)
    assert "password" in r.json()["detail"]


def test_validation_error_detail_names_the_field(client):
    r = client.post(
        "/auth/register", json={"username": "validname", "password": "short"}
    )

    assert r.status_code == 422
    assert r.json()["detail"].startswith("password:")
