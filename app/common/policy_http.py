"""Policy / 入队侧错误码 → HTTP 状态：与 ``spec/contract.yaml`` 路径说明一致。

Chat/Document/Topic 等路径在 Policy 拒绝或入队不可用时返回 **429** 或 **503**；
``error.code`` 使用 ``POLICY_QUEUE_DEPTH`` / ``QUEUE_UNAVAILABLE``（见 ErrorEnvelope 枚举）。
"""
from __future__ import annotations

from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied


def http_status_for_policy_error_code(code: ErrorCode) -> int:
    """将入队 Policy 语义错误码映射为 HTTP 状态。

    - ``POLICY_QUEUE_DEPTH`` → **429**（背压 / 队列深度拒绝）
    - ``QUEUE_UNAVAILABLE`` → **503**（broker 不可用或入队失败）

    :raises ValueError: ``code`` 不是上述两种之一（避免误将其它 ``ErrorCode`` 套用到本映射）。
    """
    if code is ErrorCode.POLICY_QUEUE_DEPTH:
        return 429
    if code is ErrorCode.QUEUE_UNAVAILABLE:
        return 503
    raise ValueError(
        "enqueue policy HTTP mapping applies only to POLICY_QUEUE_DEPTH or "
        f"QUEUE_UNAVAILABLE; got {code!r}"
    )


def http_status_for_policy_denied(exc: PolicyDenied) -> int:
    """``PolicyDenied`` 携带的 ``code`` → HTTP 状态（同上）。"""
    return http_status_for_policy_error_code(exc.code)
