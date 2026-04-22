"""Chat API 路由（contract：`/api/v1/conversations` 等）。

AG-092a：``GET /conversations`` 委托 ``ChatService`` 返回当前用户会话分页列表。
AG-092b：``POST /conversations`` 委托 ``ChatService`` 新建当前用户会话。
AG-092c：``GET /conversations/{conversation_id}`` 委托 ``ChatService`` 返回会话元数据。
AG-092d：``DELETE /conversations/{conversation_id}`` 委托 ``ChatService`` 归档会话。
AG-093：``GET /conversations/{conversation_id}/messages`` 委托 ``ChatService`` 返回分页与游标消息列表。
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.chat.api import bp
from app.chat.service import ChatService
from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.common.policy import PolicyDenied
from app.common.policy_http import http_status_for_policy_denied


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


@bp.get("/conversations")
@jwt_required()
def get_conversations() -> tuple[Response, int]:
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

    svc = ChatService()
    try:
        payload = svc.list_conversations_for_user(user_id, page=page, page_size=page_size)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.post("/conversations")
@jwt_required()
def post_conversations() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = ChatService()
    try:
        created = svc.create_conversation_for_user(user_id, payload)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(created), 201


@bp.get("/conversations/<conversation_id>")
@jwt_required()
def get_conversation_by_id(conversation_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = ChatService()
    try:
        payload = svc.get_conversation_for_user(user_id, conversation_id)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if payload is None:
        return _json_error(ErrorCode.NOT_FOUND, "conversation not found", 404)
    return jsonify(payload), 200


@bp.delete("/conversations/<conversation_id>")
@jwt_required()
def delete_conversation_by_id(conversation_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = ChatService()
    try:
        archived = svc.archive_conversation_for_user(user_id, conversation_id)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if not archived:
        return _json_error(ErrorCode.NOT_FOUND, "conversation not found", 404)
    return "", 204


@bp.get("/conversations/<conversation_id>/messages")
@jwt_required()
def get_conversation_messages(conversation_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    page_raw = request.args.get("page", "1")
    page_size_raw = request.args.get("page_size", "20")
    order = request.args.get("order", "asc")
    after_message_id = request.args.get("after_message_id")
    before_message_id = request.args.get("before_message_id")
    try:
        page = int(page_raw)
        page_size = int(page_size_raw)
    except (TypeError, ValueError):
        return _json_error(ErrorCode.VALIDATION_ERROR, "page and page_size must be integers", 400)

    svc = ChatService()
    try:
        payload = svc.list_messages_for_conversation(
            user_id,
            conversation_id,
            page=page,
            page_size=page_size,
            order=order,
            after_message_id=after_message_id,
            before_message_id=before_message_id,
        )
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(payload), 200


@bp.post("/conversations/<conversation_id>/messages")
@jwt_required()
def post_conversation_messages(conversation_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    content = str(payload.get("content", "")).strip()
    if not content:
        return _json_error(ErrorCode.VALIDATION_ERROR, "content must be non-empty", 400)

    svc = ChatService()
    try:
        accepted = svc.send_user_message(
            conversation_id=conversation_id,
            content=content,
            user_id=user_id,
            client_request_id=payload.get("client_request_id"),
            seq=payload.get("seq"),
        )
    except PolicyDenied as exc:
        return _json_error(exc.code, exc.message, http_status_for_policy_denied(exc))
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(accepted), 202


@bp.get("/chat/jobs/<job_id>")
@jwt_required()
def get_chat_job_by_id(job_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    svc = ChatService()
    try:
        payload = svc.get_chat_job_for_user(user_id, job_id)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if payload is None:
        return _json_error(ErrorCode.NOT_FOUND, "chat job not found", 404)
    return jsonify(payload), 200


@bp.get("/conversations/<conversation_id>/stream")
@jwt_required()
def get_conversation_stream(conversation_id: str) -> tuple[Response, int]:
    """SSE 未启用占位：返回 **501** + ``ErrorEnvelope``（``SSE_NOT_ENABLED``）。"""
    _ = conversation_id
    return _json_error(
        ErrorCode.SSE_NOT_ENABLED,
        "server-sent events are not enabled in this deployment",
        501,
    )
