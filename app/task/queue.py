"""Queue facade (skeleton)."""

from __future__ import annotations

import uuid
from typing import Any


def enqueue(queue_name: str, payload: dict | None = None, **kwargs: Any) -> dict[str, str]:
    """入队占位；返回可追踪句柄（contract / spy 测试）。"""
    _ = (queue_name, payload, kwargs)
    return {"job_id": str(uuid.uuid4())}


def pop_job(queue_name: str, **kwargs: Any) -> dict[str, Any] | None:
    """TODO: 从 broker 弹出一条任务；当前返回 ``None`` 表示空队列。"""
    _ = (queue_name, kwargs)
    return None
