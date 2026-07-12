"""Unit tests for the security service: hashing, username rules, tokens."""
from __future__ import annotations

import jwt
import pytest

from app.services import security


# --- password hashing --------------------------------------------------------

def test_hash_then_verify_true():
    h = security.hash_password("password123")
    assert security.verify_password("password123", h) is True


def test_verify_wrong_password_false():
    h = security.hash_password("password123")
    assert security.verify_password("wrongpassword", h) is False


def test_hash_is_salted_so_two_hashes_differ():
    assert security.hash_password("password123") != security.hash_password("password123")


def test_hash_is_not_the_plaintext():
    h = security.hash_password("password123")
    assert "password123" not in h


def test_verify_handles_malformed_hash_without_crashing():
    assert security.verify_password("password123", "not-a-real-hash") is False


# --- username validation -----------------------------------------------------

@pytest.mark.parametrize(
    "username, ok",
    [
        ("", False),
        ("   ", False),
        ("abc", False),        # too short
        ("a" * 17, False),     # too long
        ("el!jah", False),     # special char
        ("has space", False),
        ("valid1", True),
        ("Elijah", True),
        ("a" * 4, True),
        ("a" * 16, True),
    ],
)
def test_validate_username(username, ok):
    result = security.validate_username(username)
    assert (result is None) == ok


# --- access token ------------------------------------------------------------

def test_token_encodes_user_id_as_sub():
    token = security.create_access_token(42)
    payload = jwt.decode(token, security._secret(), algorithms=[security.ALGORITHM])
    assert payload["sub"] == "42"


def test_token_has_expiry():
    token = security.create_access_token(1)
    payload = jwt.decode(token, security._secret(), algorithms=[security.ALGORITHM])
    assert "exp" in payload
