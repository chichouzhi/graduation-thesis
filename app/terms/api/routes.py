"""Terms API 路由（contract：`/api/v1/terms` 等）。

AG-086a：``GET /terms`` 委托 ``TermService`` 返回当前用户可见学期列表。
"""

from __future__ import annotations

from flask import Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.common.error_envelope import ErrorCode, ErrorEnvelope
from app.terms.api import bp
from app.terms.service import TermService


def _json_error(code: ErrorCode, message: str, status: int) -> tuple[Response, int]:
    return jsonify(ErrorEnvelope(code=code, message=message).to_dict()), status


@bp.get("/terms")
@jwt_required()
def get_terms() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    payload = TermService().list_terms_for_user(user_id)
    return jsonify(payload), 200


@bp.post("/terms")
@jwt_required()
def post_terms() -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = TermService()
    try:
        term = svc.create_term_as_admin(user_id, payload)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "admin role required", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    return jsonify(term), 201


@bp.get("/terms/<term_id>")
@jwt_required()
def get_term_by_id(term_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    term = TermService().get_term_for_user(user_id, term_id)
    if term is None:
        return _json_error(ErrorCode.NOT_FOUND, "term not found", 404)
    return jsonify(term), 200


@bp.patch("/terms/<term_id>")
@jwt_required()
def patch_term_by_id(term_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = TermService()
    try:
        term = svc.update_term_as_admin(user_id, term_id, payload)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "admin role required", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)
    if term is None:
        return _json_error(ErrorCode.NOT_FOUND, "term not found", 404)
    return jsonify(term), 200


@bp.get("/terms/<term_id>/llm-config")
@jwt_required()
def get_term_llm_config(term_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    cfg = TermService().get_llm_config_for_user(user_id, term_id)
    if cfg is None:
        return _json_error(ErrorCode.NOT_FOUND, "term not found", 404)
    return jsonify(cfg), 200


@bp.patch("/terms/<term_id>/llm-config")
@jwt_required()
def patch_term_llm_config(term_id: str) -> tuple[Response, int]:
    user_id = str(get_jwt_identity() or "").strip()
    if not user_id:
        return _json_error(ErrorCode.UNAUTHORIZED, "invalid access token", 401)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_error(ErrorCode.VALIDATION_ERROR, "request body must be a JSON object", 400)

    svc = TermService()
    try:
        cfg = svc.update_llm_config_as_admin(user_id, term_id, payload)
    except PermissionError:
        return _json_error(ErrorCode.ROLE_FORBIDDEN, "admin role required", 403)
    except ValueError as exc:
        return _json_error(ErrorCode.VALIDATION_ERROR, str(exc), 400)

    if cfg is None:
        return _json_error(ErrorCode.NOT_FOUND, "term not found", 404)
    return jsonify(cfg), 200
