"""AG-082: ``POST /auth/login`` 委托 ``IdentityService``。"""
from __future__ import annotations

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole


def _seed_user() -> None:
    user = User(
        username="api-login-user",
        role=UserRole.student,
        display_name="API Login",
        password_hash=generate_password_hash("correct-pass"),
    )
    db.session.add(user)
    db.session.commit()


def test_post_auth_login_success_sets_json_and_refresh_cookie() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _seed_user()
    client = app.test_client()
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "api-login-user", "password": "correct-pass"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body is not None
    assert body["token_type"] == "Bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert isinstance(body["expires_in"], int) and body["expires_in"] > 0
    assert body["user"]["username"] == "api-login-user"
    assert body["user"]["role"] == "student"
    set_cookie = r.headers.get("Set-Cookie", "")
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie


def test_post_auth_login_invalid_credentials_401() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        _seed_user()
    client = app.test_client()
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "api-login-user", "password": "wrong"},
    )
    assert r.status_code == 401
    err = r.get_json()
    assert err["error"]["code"] == "UNAUTHORIZED"


def test_post_auth_login_validation_errors_400() -> None:
    app = create_app()
    client = app.test_client()
    r = client.post("/api/v1/auth/login", data="not-json", content_type="text/plain")
    assert r.status_code == 400
    r2 = client.post("/api/v1/auth/login", json={"username": "only-user"})
    assert r2.status_code == 400
    assert r2.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_auth_logout_success_204_and_clear_cookie() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _seed_user()
    client = app.test_client()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "api-login-user", "password": "correct-pass"},
    )
    assert login_resp.status_code == 200

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204
    assert logout_resp.data == b""
    set_cookie = logout_resp.headers.get("Set-Cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_post_auth_logout_missing_cookie_401() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
    err = resp.get_json()
    assert err["error"]["code"] == "UNAUTHORIZED"


def test_post_auth_logout_invalid_refresh_token_401() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    client = app.test_client()
    client.set_cookie(
        key=app.config["REFRESH_TOKEN_COOKIE_NAME"],
        value="not-a-jwt",
        path=app.config["REFRESH_TOKEN_COOKIE_PATH"],
    )
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
    err = resp.get_json()
    assert err["error"]["code"] == "UNAUTHORIZED"


def test_get_users_me_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _seed_user()
    client = app.test_client()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "api-login-user", "password": "correct-pass"},
    )
    token = login_resp.get_json()["access_token"]

    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["username"] == "api-login-user"
    assert body["role"] == "student"


def test_get_users_me_unauthorized_without_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_patch_users_me_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _seed_user()
    client = app.test_client()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "api-login-user", "password": "correct-pass"},
    )
    token = login_resp.get_json()["access_token"]

    resp = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "New Name", "student_profile": {"major": "cs"}},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["display_name"] == "New Name"
    assert body["student_profile"] == {"major": "cs"}


def test_patch_users_me_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _seed_user()
    client = app.test_client()
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "api-login-user", "password": "correct-pass"},
    )
    token = login_resp.get_json()["access_token"]

    resp = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"unknown": "value"},
    )
    assert resp.status_code == 400
    err = resp.get_json()
    assert err["error"]["code"] == "VALIDATION_ERROR"


def test_patch_users_me_unauthorized_without_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.patch("/api/v1/users/me", json={"display_name": "x"})
    assert resp.status_code == 401
