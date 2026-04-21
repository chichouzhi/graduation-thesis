"""Identity API 路由（contract：`/api/v1` 下 `/auth/*`、`/users/me` 等）。

AG-082：``POST /auth/login`` 仅编排 HTTP 与 ``IdentityService``，不含凭据校验业务逻辑。
"""

from __future__ import annotations

from typing import Any

from flask import Response, jsonify, request

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
