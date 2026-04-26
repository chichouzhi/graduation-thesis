"""Queue facade (skeleton)."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from flask import current_app, has_app_context
import redis

from app.config import broker_url_from_environ

# x-task-contracts.queues — spec/contract.yaml
CHAT_JOBS = "chat_jobs"
PDF_PARSE = "pdf_parse"
DOCUMENT_JOBS = "document_jobs"
KEYWORD_JOBS = "keyword_jobs"
RECONCILE_JOBS = "reconcile_jobs"
_KNOWN_QUEUE_NAMES = frozenset(
    {
        CHAT_JOBS,
        PDF_PARSE,
        DOCUMENT_JOBS,
        KEYWORD_JOBS,
        RECONCILE_JOBS,
    }
)
_LOCAL_QUEUE_BACKLOG: dict[str, deque[str]] = defaultdict(deque)
_LOCAL_QUEUE_LOCK = Lock()


def _broker_url_from_current_app() -> str:
    if not has_app_context():
        return ""
    for key in ("BROKER_URL", "REDIS_URL"):
        raw = current_app.config.get(key, "")
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return ""


def _resolved_broker_url(broker_url: str | None = None) -> str:
    explicit = str(broker_url or "").strip()
    if explicit:
        return explicit

    app_broker = _broker_url_from_current_app()
    if app_broker:
        return app_broker

    return broker_url_from_environ()


def _fallback_queue_state() -> tuple[dict[str, deque[str]], Lock]:
    if has_app_context():
        backlog = current_app.extensions.setdefault("task_queue_local_backlog", defaultdict(deque))
        lock = current_app.extensions.setdefault("task_queue_local_backlog_lock", Lock())
        return backlog, lock
    return _LOCAL_QUEUE_BACKLOG, _LOCAL_QUEUE_LOCK


def _redis_client_from_url(broker_url: str | None = None) -> redis.Redis:
    url = _resolved_broker_url(broker_url)
    if not url:
        raise RuntimeError("BROKER_URL or REDIS_URL is required for queue operations")
    return redis.Redis.from_url(url, decode_responses=False)


def _require_known_queue_name(queue_name: str) -> str:
    name = str(queue_name).strip()
    if name not in _KNOWN_QUEUE_NAMES:
        raise ValueError(f"unknown queue: {queue_name}")
    return name


def enqueue(queue_name: str, payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队并返回可追踪句柄（contract / spy 测试）。

    若 ``payload`` 已含 ``job_id``（如 Chat 受理路径预分配），则回传同一值，便于与 HTTP 202 体一致。
    """
    queue_key = _require_known_queue_name(queue_name)
    body = dict(payload or {})
    job_id = str(body.get("job_id") or uuid.uuid4())
    body["job_id"] = job_id
    encoded = json.dumps(body, ensure_ascii=False)
    broker_url = _resolved_broker_url(kwargs.get("broker_url"))
    if not broker_url:
        backlog, lock = _fallback_queue_state()
        with lock:
            backlog.setdefault(queue_key, deque()).append(encoded)
        return {"job_id": job_id}
    client = _redis_client_from_url(broker_url)
    client.rpush(queue_key, encoded)
    return {"job_id": job_id}


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

    入队前经 ``get_policy_gateway().assert_can_enqueue``（与 **SVC** 侧 **PolicyGateway** 注入一致，**M-POLICY-ENQUEUE**）。
    """
    if policy_context is None:
        raise ValueError("policy_context is required for reconcile enqueue")
    from app.extensions import get_policy_gateway

    get_policy_gateway().assert_can_enqueue(queue=RECONCILE_JOBS, **policy_context)
    return enqueue(RECONCILE_JOBS, payload, **kwargs)


def pop_job(queue_name: str, **kwargs: Any) -> dict[str, Any] | None:
    """从 broker 弹出一条任务；空队列返回 ``None``。"""
    queue_key = _require_known_queue_name(queue_name)
    broker_url = _resolved_broker_url(kwargs.get("broker_url"))
    if not broker_url:
        backlog, lock = _fallback_queue_state()
        with lock:
            queue_items = backlog.get(queue_key)
            raw = queue_items.popleft() if queue_items else None
    else:
        client = _redis_client_from_url(broker_url)
        raw = client.lpop(queue_key)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("queue payload must decode to a mapping")
    return data
