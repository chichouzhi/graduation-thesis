"""Topic API 路由（contract：`/api/v1/topics` 等）。

AG-098a：``GET /topics`` 返回课题分页列表。
AG-098b：``POST /topics`` 教师创建课题并返回 ``201``。
AG-099a：``GET /topics/{topic_id}`` 返回单课题详情。
AG-099b：``PATCH /topics/{topic_id}`` 更新草稿/被驳回课题（可触发 ``keyword_jobs``）。
AG-099c：``DELETE /topics/{topic_id}`` 撤回/关闭允许状态内的课题。
AG-100a：``POST /topics/{topic_id}/submit`` 教师提交审核。
AG-100b：``POST /topics/{topic_id}/review`` 管理员审核。
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.common.policy import PolicyDenied
from app.common.policy_http import http_status_for_policy_denied
from app.topic.api import bp
from app.topic.service import TopicService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


def _role_forbidden_detail(exc: PermissionError) -> str:
    msg = str(exc).strip() or "forbidden"
    if "only teacher/admin" in msg.lower():
        return "teacher or admin role required"
    if "only admin" in msg.lower():
        return "admin role required"
    return msg


@bp.get("/topics")
@jwt_required()
def get_topics() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    page_raw = request.args.get("page", "1")
    page_size_raw = request.args.get("page_size", "20")
    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
    except (TypeError, ValueError):
        return _json_error(ErrorCode.VALIDATION_ERROR, "page and page_size must be integers", 400)

    svc = TopicService()
    try:
        payload = svc.list_topics(
            status=request.args.get("status"),
            teacher_id=request.args.get("teacher_id"),
            term_id=request.args.get("term_id"),
            q=request.args.get("q"),
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.post("/topics")
@jwt_required()
def post_topics() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = TopicService()
    try:
        created = svc.create_topic_as_teacher(user_id, payload)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except PolicyDenied as exc:
        return _json_error(exc.code, exc.message, http_status_for_policy_denied(exc))
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(created), 201


@bp.get("/topics/<topic_id>")
@jwt_required()
def get_topic_by_id(topic_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = TopicService()
    try:
        payload = svc.get_topic(topic_id)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if payload is None:
        return _json_error(ErrorCode.NOT_FOUND, "topic not found", 404)
    return jsonify(payload), 200


@bp.patch("/topics/<topic_id>")
@jwt_required()
def patch_topic_by_id(topic_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = TopicService()
    try:
        updated = svc.update_topic_as_teacher(user_id, topic_id, payload)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except PolicyDenied as exc:
        return _json_error(exc.code, exc.message, http_status_for_policy_denied(exc))
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if updated is None:
        return _json_error(ErrorCode.NOT_FOUND, "topic not found", 404)
    return jsonify(updated), 200


@bp.delete("/topics/<topic_id>")
@jwt_required()
def delete_topic_by_id(topic_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = TopicService()
    try:
        ok = svc.delete_or_withdraw_topic_as_teacher(user_id, topic_id)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if not ok:
        return _json_error(ErrorCode.NOT_FOUND, "topic not found", 404)
    return "", 204


@bp.post("/topics/<topic_id>/submit")
@jwt_required()
def post_topic_submit(topic_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = TopicService()
    try:
        submitted = svc.submit_topic_for_review(user_id, topic_id)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if submitted is None:
        return _json_error(ErrorCode.NOT_FOUND, "topic not found", 404)
    return jsonify(submitted), 200


@bp.post("/topics/<topic_id>/review")
@jwt_required()
def post_topic_review(topic_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = TopicService()
    try:
        reviewed = svc.review_topic_as_admin(user_id, topic_id, payload)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if reviewed is None:
        return _json_error(ErrorCode.NOT_FOUND, "topic not found", 404)
    return jsonify(reviewed), 200
