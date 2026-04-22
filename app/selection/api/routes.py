"""Selection API 路由（contract：`/api/v1/applications`、`/assignments` 等）。

AG-101a：``POST /applications`` 学生新增志愿。
AG-101b：``GET /applications`` 志愿分页列表（学生/教师/管理员可见性由 ``SelectionService`` 裁剪）。
AG-102a：``DELETE /applications/{application_id}`` 学生在允许窗口内撤销志愿。
AG-102b：``PATCH /applications/{application_id}`` 学生调整志愿优先级。
AG-103：``POST /applications/{application_id}/decisions`` 教师接受/拒绝志愿。
AG-104a：``GET /assignments`` 返回当前用户相关指导关系列表。
AG-104b：``GET /assignments/{assignment_id}`` 返回单条指导关系详情。
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.common.policy import PolicyDenied
from app.selection.api import bp
from app.selection.service import SelectionService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


def _role_forbidden_detail(exc: PermissionError) -> str:
    msg = str(exc).strip() or "forbidden"
    if "only student" in msg.lower():
        return "student role required"
    if "only teacher/admin" in msg.lower():
        return "teacher or admin role required"
    if "only admin" in msg.lower():
        return "admin role required"
    return msg


def _selection_decision_error_status(exc: ValueError) -> tuple[ErrorCode, int]:
    msg = str(exc).strip().lower()
    if "not found" in msg:
        return ErrorCode.NOT_FOUND, 404
    return ErrorCode.VALIDATION_ERROR, 400


def _selection_policy_error_status(exc: PolicyDenied) -> int:
    if exc.code is ErrorCode.CAPACITY_EXCEEDED:
        return 409
    return 400


@bp.post("/applications")
@jwt_required()
def post_applications() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = SelectionService()
    try:
        created = svc.create_application_as_student(user_id, payload)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(created), 201


@bp.get("/applications")
@jwt_required()
def get_applications() -> tuple[Response, int]:
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

    svc = SelectionService()
    try:
        payload = svc.list_applications_for_user(
            user_id,
            term_id=request.args.get("term_id"),
            topic_id=request.args.get("topic_id"),
            page=page,
            page_size=page_size,
        )
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.delete("/applications/<application_id>")
@jwt_required()
def delete_application_by_id(application_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = SelectionService()
    try:
        ok = svc.withdraw_application_as_student(user_id, application_id)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if not ok:
        return _json_error(ErrorCode.NOT_FOUND, "application not found", 404)
    return "", 204


@bp.patch("/applications/<application_id>")
@jwt_required()
def patch_application_by_id(application_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = SelectionService()
    try:
        updated = svc.update_application_priority_as_student(user_id, application_id, payload)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if updated is None:
        return _json_error(ErrorCode.NOT_FOUND, "application not found", 404)
    return jsonify(updated), 200


@bp.post("/applications/<application_id>/decisions")
@jwt_required()
def post_application_decision(application_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)
    action = payload.get("action")
    if action is None:
        return _json_error(ErrorCode.VALIDATION_ERROR, "action is required", 400)

    svc = SelectionService()
    try:
        out = svc.teacher_accept_application(application_id, str(action), user_id)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except PolicyDenied as exc:
        return _json_error(exc.code, exc.message, _selection_policy_error_status(exc))
    except ValueError as exc:
        code, status = _selection_decision_error_status(exc)
        return _json_error(code, str(exc), status)
    return jsonify(out), 200


@bp.get("/assignments")
@jwt_required()
def get_assignments() -> tuple[Response, int]:
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

    svc = SelectionService()
    try:
        payload = svc.list_assignments_for_user(user_id, page=page, page_size=page_size)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.get("/assignments/<assignment_id>")
@jwt_required()
def get_assignment_by_id(assignment_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = SelectionService()
    try:
        payload = svc.get_assignment_for_user(user_id, assignment_id)
    except PermissionError as exc:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, _role_forbidden_detail(exc), 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if payload is None:
        return _json_error(ErrorCode.NOT_FOUND, "assignment not found", 404)
    return jsonify(payload), 200
