"""PROC_WORKER runtime entrypoint.

AG-048: connect broker and register ``chat_jobs`` consumer.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.config import broker_url_from_environ
from app.task import queue as queue_mod

JobHandler = Callable[[dict[str, Any]], None]


def _chat_jobs_handler(payload: dict[str, Any]) -> None:
    from app.task import chat_jobs

    chat_jobs.run(payload)


def _default_consumers() -> dict[str, JobHandler]:
    """Register default queue consumers for current runtime stage."""
    return {queue_mod.CHAT_JOBS: _chat_jobs_handler}


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

    for queue_name, handler in runtime_consumers.items():
        payload = queue_mod.pop_job(queue_name, broker_url=resolved_broker)
        if payload is None:
            continue
        if not isinstance(payload, Mapping):
            raise ValueError(f"job payload must be a mapping: queue={queue_name}")
        handler(dict(payload))
        return 1
    return 0
