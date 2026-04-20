"""全局 API 错误体：与 ``spec/contract.yaml`` 中 ``ErrorEnvelope`` 对齐。"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """``error.code`` 枚举；与 ``components.schemas.ErrorEnvelope`` 一致。"""

    QUEUE_UNAVAILABLE = "QUEUE_UNAVAILABLE"
    POLICY_QUEUE_DEPTH = "POLICY_QUEUE_DEPTH"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    TOPIC_NOT_FOUND = "TOPIC_NOT_FOUND"
    APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
    ROLE_FORBIDDEN = "ROLE_FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    UNAUTHORIZED = "UNAUTHORIZED"
    SSE_NOT_ENABLED = "SSE_NOT_ENABLED"
    DOMAIN_ERROR = "DOMAIN_ERROR"


@dataclass(frozen=True)
class ErrorEnvelope:
    """可 ``jsonify`` 的字典形状：``{"error": {"code", "message", "details"?}}``。"""

    code: ErrorCode
    message: str
    details: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        err: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.details is not None:
            err["details"] = dict(self.details)
        return {"error": err}
