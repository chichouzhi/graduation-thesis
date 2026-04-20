"""Identity service: credential validation and user loading (AG-051)."""
from __future__ import annotations

from datetime import timedelta
from time import time
from typing import Any

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
from werkzeug.security import check_password_hash

from app.extensions import db
from app.identity.model import User


class IdentityService:
    """Credential checks and user lookup for auth flows."""

    @staticmethod
    def _require_non_empty(name: str, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{name} must be non-empty")
        return text

    def load_user_by_username(self, username: str) -> User | None:
        normalized = self._require_non_empty("username", username)
        return User.query.filter_by(username=normalized).one_or_none()

    def load_user_by_id(self, user_id: str) -> User | None:
        normalized = self._require_non_empty("user_id", user_id)
        return db.session.get(User, normalized)

    def get_current_user_me(self, user_id: str) -> dict[str, Any] | None:
        """Return ``UserMe`` payload for current user, or ``None`` when missing."""
        user = self.load_user_by_id(user_id)
        if user is None:
            return None
        return user.to_user_me()

    def validate_credentials(self, username: str, password: str) -> User | None:
        normalized_password = self._require_non_empty("password", password)
        user = self.load_user_by_username(username)
        if user is None:
            return None
        if not user.password_hash:
            return None
        try:
            is_valid = check_password_hash(user.password_hash, normalized_password)
        except (ValueError, TypeError):
            # Corrupted/legacy hash should fail closed, not crash auth flow.
            return None
        if not is_valid:
            return None
        return user

    def issue_access_token(self, user: User) -> dict[str, object]:
        """Issue short-lived access token with contract-aligned envelope."""
        ttl_seconds = int(current_app.config.get("ACCESS_TOKEN_EXPIRES_IN", 3600))
        if ttl_seconds <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRES_IN must be positive")

        token = create_access_token(identity=user.id, expires_delta=timedelta(seconds=ttl_seconds))
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": ttl_seconds,
            "user": user.to_user_summary(),
        }

    def issue_refresh_token(self, user: User) -> str:
        """Issue refresh token for cookie-based session continuation."""
        ttl_seconds = int(current_app.config.get("REFRESH_TOKEN_EXPIRES_IN", 1209600))
        if ttl_seconds <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRES_IN must be positive")
        return create_refresh_token(identity=user.id, expires_delta=timedelta(seconds=ttl_seconds))

    def build_refresh_cookie(self, refresh_token: str) -> dict[str, object]:
        """Build HttpOnly refresh-cookie parameters for API layer."""
        token = self._require_non_empty("refresh_token", refresh_token)
        ttl_seconds = int(current_app.config.get("REFRESH_TOKEN_EXPIRES_IN", 1209600))
        if ttl_seconds <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRES_IN must be positive")
        return {
            "key": current_app.config.get("REFRESH_TOKEN_COOKIE_NAME", "refresh_token"),
            "value": token,
            "max_age": ttl_seconds,
            "httponly": True,
            "secure": bool(current_app.config.get("REFRESH_TOKEN_COOKIE_SECURE", True)),
            "samesite": current_app.config.get("REFRESH_TOKEN_COOKIE_SAMESITE", "Lax"),
            "path": current_app.config.get("REFRESH_TOKEN_COOKIE_PATH", "/api/v1/auth"),
        }

    def rotate_refresh_token(self, user: User) -> dict[str, object]:
        """Rotate refresh token and return cookie payload."""
        refresh_token = self.issue_refresh_token(user)
        return {
            "refresh_token": refresh_token,
            "cookie": self.build_refresh_cookie(refresh_token),
        }

    def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a refresh token in the current app process."""
        token = self._require_non_empty("refresh_token", refresh_token)
        claims = decode_token(token)
        jti = str(claims.get("jti", "")).strip()
        if not jti:
            raise ValueError("refresh_token jti is missing")
        exp_raw = claims.get("exp")
        if exp_raw is None:
            raise ValueError("refresh_token exp is missing")
        exp = int(exp_raw)

        revoked: dict[str, int] = current_app.extensions.setdefault("identity_revoked_refresh_tokens", {})
        self._prune_expired_revocations(revoked, now_ts=int(time()))
        revoked[jti] = exp

    def is_refresh_token_revoked(self, refresh_token: str) -> bool:
        """Return whether refresh token has been revoked."""
        token = self._require_non_empty("refresh_token", refresh_token)
        claims = decode_token(token)
        jti = str(claims.get("jti", "")).strip()
        if not jti:
            raise ValueError("refresh_token jti is missing")
        revoked: dict[str, int] = current_app.extensions.setdefault("identity_revoked_refresh_tokens", {})
        self._prune_expired_revocations(revoked, now_ts=int(time()))
        return jti in revoked

    def build_clear_refresh_cookie(self) -> dict[str, object]:
        """Build cookie payload that clears HttpOnly refresh cookie."""
        return {
            "key": current_app.config.get("REFRESH_TOKEN_COOKIE_NAME", "refresh_token"),
            "value": "",
            "max_age": 0,
            "expires": 0,
            "httponly": True,
            "secure": bool(current_app.config.get("REFRESH_TOKEN_COOKIE_SECURE", True)),
            "samesite": current_app.config.get("REFRESH_TOKEN_COOKIE_SAMESITE", "Lax"),
            "path": current_app.config.get("REFRESH_TOKEN_COOKIE_PATH", "/api/v1/auth"),
        }

    def logout(self, refresh_token: str) -> dict[str, object]:
        """Revoke refresh token and return clear-cookie payload."""
        self.revoke_refresh_token(refresh_token)
        return {"cookie": self.build_clear_refresh_cookie()}

    @staticmethod
    def _prune_expired_revocations(revoked: dict[str, int], *, now_ts: int) -> None:
        expired = [jti for jti, exp in revoked.items() if int(exp) <= now_ts]
        for jti in expired:
            revoked.pop(jti, None)

    def authenticate_and_issue_access_token(
        self,
        username: str,
        password: str,
    ) -> dict[str, object] | None:
        """Validate credentials and issue access token in one step."""
        user = self.validate_credentials(username, password)
        if user is None:
            return None
        return self.issue_access_token(user)

