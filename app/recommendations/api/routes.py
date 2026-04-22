"""Recommendations API 路由（contract：`/api/v1/recommendations/topics` 等）。

AG-105：``GET /recommendations/topics`` 学生 Top-N 推荐（同步只读）。
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.recommendations.api import bp
from app.recommendations.service import RecommendService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


def _parse_bool_arg(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    text = value.strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ValueError("explain must be a boolean")


@bp.get("/recommendations/topics")
@jwt_required()
def get_recommendation_topics() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    term_id = str(request.args.get("term_id", "")).strip()
    if not term_id:
        return _json_error(ErrorCode.VALIDATION_ERROR, "term_id is required", 400)

    top_n_raw = request.args.get("top_n", "10")
    try:
        top_n = int(top_n_raw)
    except (TypeError, ValueError):
        return _json_error(ErrorCode.VALIDATION_ERROR, "top_n must be an integer", 400)

    try:
        explain = _parse_bool_arg(request.args.get("explain"), default=False)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)

    svc = RecommendService()
    try:
        payload = svc.recommend_topics_for_student(
            user_id=user_id,
            term_id=term_id,
            top_n=top_n,
            explain=explain,
        )
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "student role required", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200
