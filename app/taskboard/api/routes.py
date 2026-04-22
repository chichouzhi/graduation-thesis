"""Taskboard API 路由（contract：`/api/v1/milestones` 等）。

AG-089a～AG-091：里程碑列表/创建/单条与教师 `student_id` 查询；仅转调 ``MilestoneService``。
"""

from __future__ import annotations

from datetime import date

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.taskboard.api import bp
from app.taskboard.service.milestone_service import MilestoneService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


def _optional_iso_date(name: str, raw: str | None) -> date | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


@bp.get("/milestones")
@jwt_required()
def get_milestones() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    student_id = request.args.get("student_id")
    page_raw = request.args.get("page", "1")
    page_size_raw = request.args.get("page_size", "20")
    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
    except (TypeError, ValueError):
        return _json_error(ErrorCode.VALIDATION_ERROR, "page and page_size must be integers", 400)

    try:
        from_date = _optional_iso_date("from_date", request.args.get("from_date"))
        to_date = _optional_iso_date("to_date", request.args.get("to_date"))
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)

    svc = MilestoneService()
    try:
        payload = svc.list_milestones_for_user(
            user_id,
            student_id=student_id,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "cannot list milestones for this student", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.post("/milestones")
@jwt_required()
def post_milestones() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = MilestoneService()
    try:
        created = svc.create_milestone_as_student(user_id, body)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "only student can create milestone", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(created), 201


@bp.get("/milestones/<milestone_id>")
@jwt_required()
def get_milestone_by_id(milestone_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = MilestoneService()
    try:
        row = svc.get_milestone_for_user(user_id, milestone_id)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "cannot access milestone for this student", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if row is None:
        return _json_error(ErrorCode.NOT_FOUND, "milestone not found", 404)
    return jsonify(row), 200


@bp.patch("/milestones/<milestone_id>")
@jwt_required()
def patch_milestone_by_id(milestone_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = MilestoneService()
    try:
        updated = svc.update_milestone_as_student(user_id, milestone_id, body)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "only student can update milestone", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if updated is None:
        return _json_error(ErrorCode.NOT_FOUND, "milestone not found", 404)
    return jsonify(updated), 200


@bp.delete("/milestones/<milestone_id>")
@jwt_required()
def delete_milestone_by_id(milestone_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = MilestoneService()
    try:
        ok = svc.delete_milestone_as_student(user_id, milestone_id)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "only student can delete milestone", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if not ok:
        return _json_error(ErrorCode.NOT_FOUND, "milestone not found", 404)
    return "", 204
