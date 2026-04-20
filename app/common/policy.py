"""Policy 入队门面：``PolicyGateway`` / ``assert_can_enqueue``。

对齐 ``spec/contract.yaml`` → ``x-task-contracts.queues`` 队列名真源；
拒绝语义与 ``ErrorEnvelope`` / ``ErrorCode``（AG-005）一致；HTTP 429/503 映射见 ``app.common.policy_http``（AG-007）。
"""
from __future__ import annotations

from typing import Any, Final

from app.common.error_envelope import ErrorCode

# 与 contract ``x-task-contracts.queues`` 键一致（R-QUEUE-ISO）
CONTRACT_QUEUE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "chat_jobs",
        "pdf_parse",
        "document_jobs",
        "keyword_jobs",
        "reconcile_jobs",
    }
)


class PolicyDenied(Exception):
    """策略门拒绝入队；``code`` 用于映射 ``error.code``（如 ``POLICY_QUEUE_DEPTH`` / ``QUEUE_UNAVAILABLE``）。"""

    __slots__ = ("code", "message")

    def __init__(self, message: str, *, code: ErrorCode = ErrorCode.POLICY_QUEUE_DEPTH) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PolicyGateway:
    """入队前策略门：Redis/深度/in-flight/预算等由后续实现填充；默认放行。"""

    @staticmethod
    def assert_can_enqueue(*, queue: str, **context: Any) -> None:
        """校验是否允许向命名队列入队。

        :param queue: 契约队列名（须为 ``CONTRACT_QUEUE_NAMES`` 之一）。
        :param context: 观测与规则上下文（如 ``term_id``、``user_id``、``application_id`` 等），按调用域传递。
        :raises ValueError: ``queue`` 非契约声明名（编程错误）。
        :raises PolicyDenied: 策略拒绝入队（生产路径须转为 429/503 + ErrorEnvelope）。
        """
        if queue not in CONTRACT_QUEUE_NAMES:
            raise ValueError(
                "queue must match spec/contract.yaml x-task-contracts.queues keys; "
                f"got {queue!r}"
            )
        return None
