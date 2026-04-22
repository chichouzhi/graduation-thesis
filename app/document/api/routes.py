"""Document API 路由（contract：`/api/v1/document-tasks` 等）。

AG-096a：``POST /document-tasks`` 受理上传并返回 ``202``。
AG-096b：``GET /document-tasks`` 返回当前用户文献任务列表。
AG-097：``GET /document-tasks/{task_id}`` 返回单任务详情。
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.common.policy import PolicyDenied
from app.common.policy_http import http_status_for_policy_denied
from app.document.api import bp
from app.document.service import DocumentService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


@bp.post("/document-tasks")
@jwt_required()
def post_document_tasks() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    upload = request.files.get("file")
    term_id = str(request.form.get("term_id", "")).strip()
    if upload is None:
        return _json_error(ErrorCode.VALIDATION_ERROR, "file is required", 400)
    if not term_id:
        return _json_error(ErrorCode.VALIDATION_ERROR, "term_id is required", 400)

    task_type = request.form.get("task_type")
    language = request.form.get("language")
    filename = str(upload.filename or "").strip()
    file_bytes = upload.read()

    svc = DocumentService()
    try:
        created = svc.create_document_task(
            user_id=user_id,
            term_id=term_id,
            storage_path="",
            filename=filename,
            file_bytes=file_bytes,
            task_type=task_type,
            language=language,
        )
    except PolicyDenied as exc:
        return _json_error(exc.code, exc.message, http_status_for_policy_denied(exc))
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(created), 202


@bp.get("/document-tasks")
@jwt_required()
def get_document_tasks() -> tuple[Response, int]:
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

    svc = DocumentService()
    try:
        payload = svc.list_document_tasks_for_user(user_id, page=page, page_size=page_size)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.get("/document-tasks/<task_id>")
@jwt_required()
def get_document_task_by_id(task_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = DocumentService()
    try:
        payload = svc.get_document_task_for_user(user_id, task_id)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if payload is None:
        return _json_error(ErrorCode.NOT_FOUND, "document task not found", 404)
    return jsonify(payload), 200
