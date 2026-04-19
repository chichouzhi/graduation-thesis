"""队列与 Worker 契约：enqueue 须可观测；run_once 须返回处理计数（便于集成测断言）。"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.contract


def test_enqueue_returns_job_reference() -> None:
    from app.task import enqueue

    ret = enqueue(
        "chat_jobs",
        {
            "conversation_id": "c1",
            "user_id": "u1",
            "content": "x",
            "term_id": "t1",
        },
    )
    assert ret is not None, "enqueue 不得静默返回 None；须返回 job 句柄（dict 或对象）以便客户端追踪"
    job_id = ret.get("job_id") if isinstance(ret, dict) else getattr(ret, "job_id", None)
    assert job_id is not None and str(job_id).strip() != "", "enqueue 必须返回 job_id"


def test_worker_run_once_returns_processed_count() -> None:
    from app.worker import run_once

    n = run_once()
    assert isinstance(n, int), "run_once 须返回本 tick 处理的任务条数（int，可为 0）"
    assert n >= 0
