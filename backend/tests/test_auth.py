"""Auth tests - SCAFFOLD (test names = the validation requirements verbatim).

Every username rule below is an explicit functional requirement, so these
tests ARE the acceptance criteria for the auth milestone.
"""
# TODO(auth+tests): implement against the conftest client fixture.

# def test_register_username_too_short(client):       # 3 chars -> 422
# def test_register_username_too_long(client):        # 17 chars -> 422
# def test_register_username_special_chars(client):   # "el!jah" -> 422
# def test_register_empty_username(client):           # "" -> 422 w/ message
# def test_register_empty_password(client):           # "" -> 422 w/ message
# def test_register_duplicate_username(client):       # -> 409
# def test_login_success_returns_token(client):
# def test_login_wrong_password_401_same_message_as_unknown_user(client):
# def test_me_requires_token(client):                 # no token -> 401
# def test_password_stored_hashed(client):            # DB never holds plaintext
