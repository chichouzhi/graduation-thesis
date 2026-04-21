"""AG-051: IdentityService credential validation and user loading."""
from __future__ import annotations

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.identity.service import IdentityService


def _create_user(*, username: str = "alice", password: str = "pwd-123") -> User:
    user = User(
        username=username,
        role=UserRole.student,
        display_name="Alice",
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_load_user_by_username_and_id() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        created = _create_user()
        svc = IdentityService()

        loaded_by_name = svc.load_user_by_username("alice")
        loaded_by_id = svc.load_user_by_id(created.id)

        assert loaded_by_name is not None
        assert loaded_by_id is not None
        assert loaded_by_name.id == created.id
        assert loaded_by_id.username == "alice"


def test_get_current_user_me_returns_userme_or_none() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        created = _create_user(username="me-user", password="me-pass")
        created.email = "me@example.com"
        created.student_profile = {"major": "cs"}
        db.session.commit()
        svc = IdentityService()

        payload = svc.get_current_user_me(created.id)
        missing = svc.get_current_user_me("missing-user-id")

        assert payload == created.to_user_me()
        assert missing is None


def test_update_current_user_me_updates_allowed_fields() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        created = _create_user(username="patch-me", password="patch-pass")
        svc = IdentityService()

        payload = svc.update_current_user_me(
            created.id,
            {
                "display_name": "Patched Name",
                "email": "patched@example.com",
                "student_profile": {"grade": "2026"},
                "teacher_profile": None,
            },
        )

        assert payload is not None
        assert payload["display_name"] == "Patched Name"
        assert payload["email"] == "patched@example.com"
        assert payload["student_profile"] == {"grade": "2026"}
        assert payload["teacher_profile"] is None


def test_update_current_user_me_returns_none_for_missing_user() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        svc = IdentityService()
        assert svc.update_current_user_me("missing-id", {"display_name": "X"}) is None


def test_update_current_user_me_rejects_invalid_patch() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        created = _create_user(username="patch-invalid", password="patch-pass")
        svc = IdentityService()

        with pytest.raises(ValueError, match="patch must include at least one updatable field"):
            svc.update_current_user_me(created.id, {"unknown": 1})
        with pytest.raises(ValueError, match="display_name must be non-empty"):
            svc.update_current_user_me(created.id, {"display_name": "   "})
        with pytest.raises(ValueError, match="student_profile must be an object or null"):
            svc.update_current_user_me(created.id, {"student_profile": "invalid"})


def test_validate_credentials_success_and_failures() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        created = _create_user(username="bob", password="secret-pass")
        svc = IdentityService()

        assert svc.validate_credentials("bob", "secret-pass").id == created.id
        assert svc.validate_credentials("bob", "wrong-pass") is None
        assert svc.validate_credentials("missing-user", "secret-pass") is None


def test_validate_credentials_returns_none_when_password_hash_missing() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(
            username="nohash",
            role=UserRole.teacher,
            display_name="No Hash",
            password_hash=None,
        )
        db.session.add(user)
        db.session.commit()

        assert IdentityService().validate_credentials("nohash", "anything") is None


def test_validate_credentials_returns_none_for_corrupted_hash() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(
            username="bad-hash",
            role=UserRole.student,
            display_name="Bad Hash",
            password_hash="not-a-werkzeug-hash",
        )
        db.session.add(user)
        db.session.commit()

        assert IdentityService().validate_credentials("bad-hash", "anything") is None


def test_identity_service_rejects_blank_input() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        svc = IdentityService()

        with pytest.raises(ValueError, match="username must be non-empty"):
            svc.load_user_by_username("   ")
        with pytest.raises(ValueError, match="user_id must be non-empty"):
            svc.load_user_by_id("  ")
        with pytest.raises(ValueError, match="password must be non-empty"):
            svc.validate_credentials("alice", "   ")


def test_issue_access_token_returns_contract_shape_and_ttl() -> None:
    app = create_app()
    app.config["ACCESS_TOKEN_EXPIRES_IN"] = 1800
    with app.app_context():
        db.create_all()
        user = _create_user(username="token-user", password="token-pass")
        svc = IdentityService()

        payload = svc.issue_access_token(user)

        assert isinstance(payload["access_token"], str)
        assert payload["access_token"]
        assert payload["token_type"] == "Bearer"
        assert payload["expires_in"] == 1800
        assert payload["user"] == user.to_user_summary()


def test_issue_access_token_rejects_non_positive_ttl() -> None:
    app = create_app()
    app.config["ACCESS_TOKEN_EXPIRES_IN"] = 0
    with app.app_context():
        db.create_all()
        user = _create_user(username="ttl-user", password="ttl-pass")
        svc = IdentityService()

        with pytest.raises(ValueError, match="ACCESS_TOKEN_EXPIRES_IN must be positive"):
            svc.issue_access_token(user)


def test_authenticate_and_issue_access_token_success_and_failure() -> None:
    app = create_app()
    app.config["ACCESS_TOKEN_EXPIRES_IN"] = 900
    with app.app_context():
        db.create_all()
        _create_user(username="combo-user", password="combo-pass")
        svc = IdentityService()

        ok_payload = svc.authenticate_and_issue_access_token("combo-user", "combo-pass")
        bad_payload = svc.authenticate_and_issue_access_token("combo-user", "wrong-pass")

        assert ok_payload is not None
        assert ok_payload["token_type"] == "Bearer"
        assert ok_payload["expires_in"] == 900
        assert bad_payload is None


def test_login_with_refresh_session_returns_login_and_cookie_params() -> None:
    app = create_app()
    app.config["ACCESS_TOKEN_EXPIRES_IN"] = 600
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="login-wrap", password="wrap-pass")
        svc = IdentityService()

        ok = svc.login_with_refresh_session("login-wrap", "wrap-pass")
        bad = svc.login_with_refresh_session("login-wrap", "nope")

        assert bad is None
        assert ok is not None
        assert ok["login"]["expires_in"] == 600
        assert ok["login"]["user"]["username"] == "login-wrap"
        ck = ok["refresh_cookie"]
        assert ck["key"] == "refresh_token"
        assert isinstance(ck["value"], str) and ck["value"]
        assert ck["httponly"] is True


def test_issue_refresh_token_and_rotate_cookie_payload() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_EXPIRES_IN"] = 7200
    app.config["REFRESH_TOKEN_COOKIE_NAME"] = "rt"
    app.config["REFRESH_TOKEN_COOKIE_PATH"] = "/api/v1/auth"
    app.config["REFRESH_TOKEN_COOKIE_SAMESITE"] = "Strict"
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="refresh-user", password="refresh-pass")
        svc = IdentityService()

        refresh_token = svc.issue_refresh_token(user)
        rotated = svc.rotate_refresh_token(user)

        assert isinstance(refresh_token, str)
        assert refresh_token
        assert isinstance(rotated["refresh_token"], str)
        assert rotated["refresh_token"]
        assert rotated["refresh_token"] != refresh_token
        assert rotated["cookie"] == {
            "key": "rt",
            "value": rotated["refresh_token"],
            "max_age": 7200,
            "httponly": True,
            "secure": False,
            "samesite": "Strict",
            "path": "/api/v1/auth",
        }


def test_refresh_token_rejects_non_positive_ttl_and_blank_cookie_value() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_EXPIRES_IN"] = 0
    with app.app_context():
        db.create_all()
        user = _create_user(username="refresh-ttl", password="refresh-ttl-pass")
        svc = IdentityService()

        with pytest.raises(ValueError, match="REFRESH_TOKEN_EXPIRES_IN must be positive"):
            svc.issue_refresh_token(user)
        with pytest.raises(ValueError, match="refresh_token must be non-empty"):
            svc.build_refresh_cookie("   ")


def test_logout_revokes_refresh_token_and_returns_clear_cookie_payload() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_NAME"] = "rt"
    app.config["REFRESH_TOKEN_COOKIE_PATH"] = "/api/v1/auth"
    app.config["REFRESH_TOKEN_COOKIE_SAMESITE"] = "Strict"
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="logout-user", password="logout-pass")
        svc = IdentityService()
        refresh_token = svc.issue_refresh_token(user)

        result = svc.logout(refresh_token)

        assert svc.is_refresh_token_revoked(refresh_token) is True
        assert result["cookie"] == {
            "key": "rt",
            "value": "",
            "max_age": 0,
            "expires": 0,
            "httponly": True,
            "secure": False,
            "samesite": "Strict",
            "path": "/api/v1/auth",
        }


def test_logout_rejects_blank_refresh_token() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        svc = IdentityService()

        with pytest.raises(ValueError, match="refresh_token must be non-empty"):
            svc.logout("  ")


def test_refresh_revocation_store_uses_jti_and_prunes_expired_entries(monkeypatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        svc = IdentityService()

        monkeypatch.setattr(
            "app.identity.service.identity_service.decode_token",
            lambda token: {"jti": f"jti-{token}", "exp": 200},
        )
        monkeypatch.setattr("app.identity.service.identity_service.time", lambda: 100)
        svc.revoke_refresh_token("active-token")

        revoked = app.extensions["identity_revoked_refresh_tokens"]
        assert revoked == {"jti-active-token": 200}
        assert svc.is_refresh_token_revoked("active-token") is True

        app.extensions["identity_revoked_refresh_tokens"]["jti-expired"] = 10
        monkeypatch.setattr("app.identity.service.identity_service.time", lambda: 300)
        assert svc.is_refresh_token_revoked("active-token") is False
        assert app.extensions["identity_revoked_refresh_tokens"] == {}

