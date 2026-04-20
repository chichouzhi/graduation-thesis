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


def test_enqueue_pdf_parse_targets_contract_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``enqueue_pdf_parse`` 须委托 ``enqueue`` 且队列为契约 ``pdf_parse``。"""
    seen: list[tuple[str, dict | None]] = []

    def capture_enqueue(
        queue_name: str,
        payload: dict | None = None,
        **kwargs: object,
    ) -> dict[str, str]:
        seen.append((queue_name, payload))
        return {"job_id": "pdf-job-1"}

    monkeypatch.setattr("app.task.queue.enqueue", capture_enqueue)
    from app.task import enqueue_pdf_parse

    payload = {
        "document_task_id": "dt-1",
        "user_id": "u1",
        "storage_path": "/tmp/x.pdf",
        "term_id": "t1",
    }
    assert enqueue_pdf_parse(payload) == {"job_id": "pdf-job-1"}
    assert seen == [("pdf_parse", payload)]


def test_enqueue_document_jobs_targets_contract_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``enqueue_document_jobs`` 须委托 ``enqueue`` 且队列为契约 ``document_jobs``。"""
    seen: list[tuple[str, dict | None]] = []

    def capture_enqueue(
        queue_name: str,
        payload: dict | None = None,
        **kwargs: object,
    ) -> dict[str, str]:
        seen.append((queue_name, payload))
        return {"job_id": "doc-job-1"}

    monkeypatch.setattr("app.task.queue.enqueue", capture_enqueue)
    from app.task import enqueue_document_jobs

    payload = {
        "document_task_id": "dt-1",
        "user_id": "u1",
        "storage_path": "/tmp/x.pdf",
        "term_id": "t1",
        "stage": "extract",
        "filename": "x.pdf",
    }
    assert enqueue_document_jobs(payload) == {"job_id": "doc-job-1"}
    assert seen == [("document_jobs", payload)]


def test_enqueue_keyword_jobs_targets_contract_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``enqueue_keyword_jobs`` 须委托 ``enqueue`` 且队列为契约 ``keyword_jobs``。"""
    seen: list[tuple[str, dict | None]] = []

    def capture_enqueue(
        queue_name: str,
        payload: dict | None = None,
        **kwargs: object,
    ) -> dict[str, str]:
        seen.append((queue_name, payload))
        return {"job_id": "kw-job-1"}

    monkeypatch.setattr("app.task.queue.enqueue", capture_enqueue)
    from app.task import enqueue_keyword_jobs

    payload = {
        "keyword_job_id": "kj-1",
        "topic_id": "top-1",
        "term_id": "t1",
        "text_snapshot": "hello",
        "requested_by_user_id": "u1",
    }
    assert enqueue_keyword_jobs(payload) == {"job_id": "kw-job-1"}
    assert seen == [("keyword_jobs", payload)]


def test_enqueue_reconcile_jobs_requires_policy_context() -> None:
    from app.task import enqueue_reconcile_jobs

    payload = {
        "reconcile_job_id": "rj-1",
        "scope": "full_table",
        "application_id": "app-1",
        "action": "accept",
        "teacher_id": "t1",
    }
    with pytest.raises(ValueError, match="policy_context is required"):
        enqueue_reconcile_jobs(payload)


def test_enqueue_reconcile_jobs_runs_policy_when_policy_context_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy_calls: list[dict[str, object]] = []

    def capture_policy(*, queue: str, **context: object) -> None:
        policy_calls.append({"queue": queue, **context})

    monkeypatch.setattr("app.task.queue.PolicyGateway.assert_can_enqueue", capture_policy)

    seen: list[tuple[str, dict | None]] = []

    def capture_enqueue(
        queue_name: str,
        payload: dict | None = None,
        **kwargs: object,
    ) -> dict[str, str]:
        seen.append((queue_name, payload))
        return {"job_id": "rec-job-2"}

    monkeypatch.setattr("app.task.queue.enqueue", capture_enqueue)
    from app.task import enqueue_reconcile_jobs

    payload = {
        "reconcile_job_id": "rj-2",
        "scope": "full_table",
        "application_id": "app-2",
        "action": "accept",
        "teacher_id": "t2",
    }
    assert enqueue_reconcile_jobs(
        payload,
        policy_context={"application_id": "app-2", "action": "accept", "teacher_id": "t2"},
    ) == {"job_id": "rec-job-2"}
    assert policy_calls == [
        {
            "queue": "reconcile_jobs",
            "application_id": "app-2",
            "action": "accept",
            "teacher_id": "t2",
        }
    ]
    assert seen == [("reconcile_jobs", payload)]


def test_worker_run_once_returns_processed_count() -> None:
    from app.worker import run_once

    n = run_once()
    assert isinstance(n, int), "run_once 须返回本 tick 处理的任务条数（int，可为 0）"
    assert n >= 0
