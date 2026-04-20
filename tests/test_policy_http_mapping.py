"""AG-007：Policy 拒绝 → HTTP 429/503 与 ``POLICY_QUEUE_DEPTH`` / ``QUEUE_UNAVAILABLE`` 映射（单元）。"""
from __future__ import annotations

import pytest

from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.common.policy_http import http_status_for_policy_denied, http_status_for_policy_error_code


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        (ErrorCode.POLICY_QUEUE_DEPTH, 429),
        (ErrorCode.QUEUE_UNAVAILABLE, 503),
    ],
    ids=["policy_queue_depth_429", "queue_unavailable_503"],
)
def test_enqueue_policy_error_code_maps_to_contract_http_status(
    code: ErrorCode, expected_status: int
) -> None:
    assert http_status_for_policy_error_code(code) == expected_status


def test_policy_denied_maps_via_embedded_code() -> None:
    depth = PolicyDenied("queue depth exceeded", code=ErrorCode.POLICY_QUEUE_DEPTH)
    assert http_status_for_policy_denied(depth) == 429
    unavailable = PolicyDenied("redis down", code=ErrorCode.QUEUE_UNAVAILABLE)
    assert http_status_for_policy_denied(unavailable) == 503


def test_mapping_rejects_non_enqueue_policy_codes() -> None:
    with pytest.raises(ValueError, match="POLICY_QUEUE_DEPTH"):
        http_status_for_policy_error_code(ErrorCode.LLM_RATE_LIMITED)
