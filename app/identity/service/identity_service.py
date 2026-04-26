"""Identity service: credential validation and user loading (AG-051)."""
from __future__ import annotations

from datetime import timedelta
from threading import Lock
from time import time
from urllib.parse import urlparse
from typing import Any

from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
import redis
from werkzeug.security import check_password_hash

from app.config import broker_url_from_environ
from app.extensions import db
from app.identity.model import User


class InvalidRefreshTokenError(ValueError):
    """Raised when refresh-token state is invalid for authentication."""


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

    def update_current_user_me(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        """Apply ``PATCH /users/me`` fields and return updated ``UserMe``."""
        user = self.load_user_by_id(user_id)
        if user is None:
            return None
        if not isinstance(patch, dict):
            raise ValueError("patch must be a mapping")

        allowed_fields = {"display_name", "email", "student_profile", "teacher_profile"}
        updates = {k: v for k, v in patch.items() if k in allowed_fields}
        if not updates:
            raise ValueError("patch must include at least one updatable field")

        if "display_name" in updates:
            user.display_name = self._require_non_empty("display_name", updates["display_name"])
        if "email" in updates:
            user.email = self._require_non_empty("email", updates["email"])
        if "student_profile" in updates:
            if updates["student_profile"] is not None and not isinstance(updates["student_profile"], dict):
                raise ValueError("student_profile must be an object or null")
            user.student_profile = updates["student_profile"]
        if "teacher_profile" in updates:
            if updates["teacher_profile"] is not None and not isinstance(updates["teacher_profile"], dict):
                raise ValueError("teacher_profile must be an object or null")
            user.teacher_profile = updates["teacher_profile"]

        db.session.commit()
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

    def _refresh_store_broker_url(self) -> str:
        return str(current_app.config.get("BROKER_URL") or broker_url_from_environ()).strip()

    @staticmethod
    def _is_redis_broker_url(broker_url: str) -> bool:
        scheme = urlparse(str(broker_url).strip()).scheme.lower()
        return scheme in {"redis", "rediss", "unix"}

    def _redis_client_from_broker(self) -> redis.Redis | None:
        broker_url = self._refresh_store_broker_url()
        if not broker_url:
            return None
        if not self._is_redis_broker_url(broker_url):
            return None
        return redis.Redis.from_url(broker_url, decode_responses=False)

    @staticmethod
    def _refresh_revocation_key(jti: str) -> str:
        return f"identity:refresh:revoked:{jti}"

    @staticmethod
    def _decode_refresh_token_claims(refresh_token: str) -> dict[str, Any]:
        token = str(refresh_token).strip()
        try:
            claims = decode_token(token)
        except Exception as exc:
            raise InvalidRefreshTokenError("invalid refresh token") from exc
        if str(claims.get("type", "")).strip() != "refresh":
            raise InvalidRefreshTokenError("invalid refresh token")
        jti = str(claims.get("jti", "")).strip()
        if not jti:
            raise InvalidRefreshTokenError("refresh token jti is missing")
        exp_raw = claims.get("exp")
        if exp_raw is None:
            raise InvalidRefreshTokenError("refresh token exp is missing")
        claims["jti"] = jti
        claims["exp"] = int(exp_raw)
        return claims

    def _consume_refresh_token_claims(self, claims: dict[str, Any]) -> bool:
        jti = str(claims["jti"])
        exp = int(claims["exp"])
        ttl_seconds = max(exp - int(time()), 1)
        client = self._redis_client_from_broker()
        if client is not None:
            return bool(
                client.set(
                    self._refresh_revocation_key(jti),
                    str(exp),
                    ex=ttl_seconds,
                    nx=True,
                )
            )

        revoked: dict[str, int] = current_app.extensions.setdefault("identity_revoked_refresh_tokens", {})
        lock: Lock = current_app.extensions.setdefault("identity_revoked_refresh_tokens_lock", Lock())
        with lock:
            self._prune_expired_revocations(revoked, now_ts=int(time()))
            if jti in revoked:
                return False
            revoked[jti] = exp
            return True

    def _is_refresh_token_claims_revoked(self, claims: dict[str, Any]) -> bool:
        jti = str(claims["jti"])
        client = self._redis_client_from_broker()
        if client is not None:
            return bool(client.exists(self._refresh_revocation_key(jti)))

        revoked: dict[str, int] = current_app.extensions.setdefault("identity_revoked_refresh_tokens", {})
        lock: Lock = current_app.extensions.setdefault("identity_revoked_refresh_tokens_lock", Lock())
        with lock:
            self._prune_expired_revocations(revoked, now_ts=int(time()))
            return jti in revoked

    def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a refresh token in the configured shared store or local fallback."""
        token = self._require_non_empty("refresh_token", refresh_token)
        claims = self._decode_refresh_token_claims(token)
        if not self._consume_refresh_token_claims(claims):
            raise InvalidRefreshTokenError("refresh token has been revoked")

    def is_refresh_token_revoked(self, refresh_token: str) -> bool:
        """Return whether refresh token has been revoked."""
        token = self._require_non_empty("refresh_token", refresh_token)
        claims = self._decode_refresh_token_claims(token)
        return self._is_refresh_token_claims_revoked(claims)

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

    def refresh_access_session(self, refresh_token: str) -> dict[str, Any]:
        """Atomically consume refresh token, then rotate it and issue a new access token."""
        token = self._require_non_empty("refresh_token", refresh_token)
        claims = self._decode_refresh_token_claims(token)
        user_id = str(claims.get("sub", "")).strip()
        if not user_id:
            raise InvalidRefreshTokenError("refresh token subject is missing")

        user = self.load_user_by_id(user_id)
        if user is None:
            raise InvalidRefreshTokenError("user not found")

        login_body = self.issue_access_token(user)
        refresh = self.rotate_refresh_token(user)
        if not self._consume_refresh_token_claims(claims):
            raise InvalidRefreshTokenError("refresh token has been revoked")
        return {"login": login_body, "refresh_cookie": refresh["cookie"]}

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

    def login_with_refresh_session(self, username: str, password: str) -> dict[str, Any] | None:
        """登录成功时返回 ``LoginResponse`` 体与 HttpOnly refresh ``set_cookie`` 参数；凭据错误返回 ``None``。"""
        user = self.validate_credentials(username, password)
        if user is None:
            return None
        login_body = self.issue_access_token(user)
        refresh = self.rotate_refresh_token(user)
        return {"login": login_body, "refresh_cookie": refresh["cookie"]}

