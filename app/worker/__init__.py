"""PROC_WORKER runtime entrypoint.

AG-048: connect broker and register ``chat_jobs`` consumer.
AG-049: register ``pdf_parse`` / ``document_jobs`` consumers.
AG-050: register ``keyword_jobs`` / ``reconcile_jobs`` consumers.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from app.config import broker_url_from_environ
from app.task import queue as queue_mod

JobHandler = Callable[[dict[str, Any]], None]
logger = logging.getLogger(__name__)
_queue_cursor = 0


def _chat_jobs_handler(payload: dict[str, Any]) -> None:
    from app.task import chat_jobs

    chat_jobs.run(payload)


def _pdf_parse_handler(payload: dict[str, Any]) -> None:
    from app.task import pdf_parse_jobs

    pdf_parse_jobs.run(payload)


def _document_jobs_handler(payload: dict[str, Any]) -> None:
    from app.task import document_jobs

    document_jobs.run(payload)


def _keyword_jobs_handler(payload: dict[str, Any]) -> None:
    from app.task import keyword_jobs

    keyword_jobs.run(payload)


def _reconcile_jobs_handler(payload: dict[str, Any]) -> None:
    from app.task import reconcile_jobs

    reconcile_jobs.run(payload)


def _default_consumers() -> dict[str, JobHandler]:
    """Register default queue consumers for current runtime stage."""
    return {
        queue_mod.CHAT_JOBS: _chat_jobs_handler,
        queue_mod.PDF_PARSE: _pdf_parse_handler,
        queue_mod.DOCUMENT_JOBS: _document_jobs_handler,
        queue_mod.KEYWORD_JOBS: _keyword_jobs_handler,
        queue_mod.RECONCILE_JOBS: _reconcile_jobs_handler,
    }


def _iter_consumers_round_robin(consumers: Mapping[str, JobHandler]) -> list[tuple[str, JobHandler]]:
    """Return consumers in round-robin order to reduce queue starvation."""
    global _queue_cursor
    items = list(consumers.items())
    if not items:
        return []
    start = _queue_cursor % len(items)
    _queue_cursor = (_queue_cursor + 1) % len(items)
    return items[start:] + items[:start]


def _resolve_broker_url(broker_url: str | None) -> str:
    if broker_url is not None and str(broker_url).strip():
        return str(broker_url).strip()
    return broker_url_from_environ()


def run_once(
    *,
    broker_url: str | None = None,
    consumers: Mapping[str, JobHandler] | None = None,
) -> int:
    """Poll broker once and dispatch at most one job.

    Returns processed job count for this tick (0 or 1).
    """
    runtime_consumers = dict(consumers or _default_consumers())
    resolved_broker = _resolve_broker_url(broker_url)

    for queue_name, handler in _iter_consumers_round_robin(runtime_consumers):
        try:
            payload = queue_mod.pop_job(queue_name, broker_url=resolved_broker)
        except Exception:
            logger.exception("worker pop failed for queue=%s", queue_name)
            continue
        if payload is None:
            continue
        if not isinstance(payload, Mapping):
            logger.error("worker payload must be a mapping: queue=%s", queue_name)
            continue
        try:
            handler(dict(payload))
        except Exception:
            logger.exception("worker handler failed for queue=%s", queue_name)
            continue
        logger.info("worker processed job queue=%s", queue_name)
        return 1
    return 0
