"""Queue facade (skeleton)."""

from __future__ import annotations

import uuid
from typing import Any

from app.common.policy import PolicyGateway

# x-task-contracts.queues — spec/contract.yaml
CHAT_JOBS = "chat_jobs"
PDF_PARSE = "pdf_parse"
DOCUMENT_JOBS = "document_jobs"
KEYWORD_JOBS = "keyword_jobs"
RECONCILE_JOBS = "reconcile_jobs"


def enqueue(queue_name: str, payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队占位；返回可追踪句柄（contract / spy 测试）。

    若 ``payload`` 已含 ``job_id``（如 Chat 受理路径预分配），则回传同一值，便于与 HTTP 202 体一致。
    """
    _ = (queue_name, kwargs)
    if isinstance(payload, dict):
        jid = payload.get("job_id")
        if jid is not None and str(jid).strip() != "":
            return {"job_id": str(jid)}
    return {"job_id": str(uuid.uuid4())}


def enqueue_chat_jobs(payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队 ``chat_jobs``（``#/components/schemas/ChatJobPayload``）。"""
    return enqueue(CHAT_JOBS, payload, **kwargs)


def enqueue_pdf_parse(payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队 ``pdf_parse``（``#/components/schemas/PdfJobPayload``）。"""
    return enqueue(PDF_PARSE, payload, **kwargs)


def enqueue_document_jobs(payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队 ``document_jobs``（``#/components/schemas/DocumentJobPayload``）。"""
    return enqueue(DOCUMENT_JOBS, payload, **kwargs)


def enqueue_keyword_jobs(payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队 ``keyword_jobs``（``#/components/schemas/KeywordJobPayload``）。"""
    return enqueue(KEYWORD_JOBS, payload, **kwargs)


def enqueue_reconcile_jobs(
    payload: dict | None = None,
    *,
    policy_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, str]:
    """入队 ``reconcile_jobs``（``#/components/schemas/ReconcileJobPayload``）。

    入队前必须执行 ``PolicyGateway.assert_can_enqueue``（与受理侧 **M-POLICY-ENQUEUE** 同等）。
    """
    if policy_context is None:
        raise ValueError("policy_context is required for reconcile enqueue")
    PolicyGateway.assert_can_enqueue(queue=RECONCILE_JOBS, **policy_context)
    return enqueue(RECONCILE_JOBS, payload, **kwargs)


def pop_job(queue_name: str, **kwargs: Any) -> dict[str, Any] | None:
    """TODO: 从 broker 弹出一条任务；当前返回 ``None`` 表示空队列。"""
    _ = (queue_name, kwargs)
    return None
