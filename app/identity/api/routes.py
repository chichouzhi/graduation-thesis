"""Identity API 路由（contract：`/api/v1` 下 `/auth/*`、`/users/me` 等）。

AG-082：``POST /auth/login`` 仅编排 HTTP 与 ``IdentityService``，不含凭据校验业务逻辑。
"""

from __future__ import annotations

from typing import Any

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.identity.api import bp
from app.identity.service import IdentityService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


@bp.post("/auth/login")
def post_auth_login() -> tuple[Response, int]:
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)
    if "username" not in raw or "password" not in raw:
        return _json_error(
            ErrorCode.VALIDATION_ERROR,
            "username and password are required",
            400,
        )
    username = raw.get("username")
    password = raw.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return _json_error(ErrorCode.VALIDATION_ERROR, "username and password must be strings", 400)

    svc = IdentityService()
    try:
        result = svc.login_with_refresh_session(username, password)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)

    if result is None:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid username or password", 401)

    login_body = result["login"]
    cookie: dict[str, Any] = result["refresh_cookie"]
    resp = jsonify(login_body)
    resp.set_cookie(
        key=str(cookie["key"]),
        value=str(cookie["value"]),
        max_age=int(cookie["max_age"]),
        httponly=bool(cookie["httponly"]),
        secure=bool(cookie["secure"]),
        samesite=str(cookie["samesite"]),
        path=str(cookie["path"]),
    )
    return resp, 200


@bp.post("/auth/logout")
def post_auth_logout() -> tuple[Response, int]:
    svc = IdentityService()
    refresh_cookie_name = str(svc.build_clear_refresh_cookie()["key"])
    refresh_token = request.cookies.get(refresh_cookie_name, "")
    if not str(refresh_token).strip():
        return _json_error(ErrorCode.UNAUTHORIZED, "refresh token is required", 401)

    try:
        result = svc.logout(str(refresh_token))
    except Exception:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid refresh token", 401)

    cookie: dict[str, Any] = result["cookie"]
    resp = Response(status=204)
    resp.set_cookie(
        key=str(cookie["key"]),
        value=str(cookie["value"]),
        max_age=int(cookie["max_age"]),
        expires=cookie.get("expires"),
        httponly=bool(cookie["httponly"]),
        secure=bool(cookie["secure"]),
        samesite=str(cookie["samesite"]),
        path=str(cookie["path"]),
    )
    return resp, 204


@bp.get("/users/me")
@jwt_required()
def get_users_me() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = IdentityService()
    profile = svc.get_current_user_me(user_id)
    if profile is None:
        return _json_error(ErrorCode.NOT_FOUND, "user not found", 404)
    return jsonify(profile), 200


@bp.patch("/users/me")
@jwt_required()
def patch_users_me() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = IdentityService()
    try:
        updated = svc.update_current_user_me(user_id, payload)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if updated is None:
        return _json_error(ErrorCode.NOT_FOUND, "user not found", 404)
    return jsonify(updated), 200
