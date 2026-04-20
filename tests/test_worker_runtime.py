from __future__ import annotations

from typing import Any


def test_run_once_registers_chat_jobs_and_dispatches(monkeypatch) -> None:
    pop_calls: list[tuple[str, str]] = []
    handled: list[dict[str, Any]] = []

    def fake_pop_job(queue_name: str, **kwargs: Any) -> dict[str, Any] | None:
        pop_calls.append((queue_name, str(kwargs.get("broker_url", ""))))
        return {"conversation_id": "c-1", "term_id": "t-1"}

    def fake_chat_handler(payload: dict[str, Any]) -> None:
        handled.append(payload)

    monkeypatch.setattr("app.worker._chat_jobs_handler", fake_chat_handler)
    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    n = run_once(broker_url="redis://worker-broker")
    assert n == 1
    assert pop_calls == [("chat_jobs", "redis://worker-broker")]
    assert handled == [{"conversation_id": "c-1", "term_id": "t-1"}]


def test_run_once_returns_zero_when_queue_empty(monkeypatch) -> None:
    def fake_pop_job(_queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 0


def test_run_once_reads_broker_url_from_environment(monkeypatch) -> None:
    seen_urls: list[str] = []

    def fake_pop_job(_queue_name: str, **kwargs: Any) -> dict[str, Any] | None:
        seen_urls.append(str(kwargs.get("broker_url", "")))
        return None

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._queue_cursor", 0)
    monkeypatch.setenv("BROKER_URL", "redis://env-broker")
    monkeypatch.delenv("REDIS_URL", raising=False)

    from app.worker import run_once

    assert run_once() == 0
    assert seen_urls == [
        "redis://env-broker",
        "redis://env-broker",
        "redis://env-broker",
        "redis://env-broker",
        "redis://env-broker",
    ]


def test_run_once_dispatches_pdf_parse_when_chat_queue_empty(monkeypatch) -> None:
    pop_calls: list[str] = []
    handled: list[dict[str, Any]] = []

    def fake_pop_job(queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        pop_calls.append(queue_name)
        if queue_name == "pdf_parse":
            return {"document_task_id": "dt-1"}
        return None

    def fake_pdf_handler(payload: dict[str, Any]) -> None:
        handled.append(payload)

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._pdf_parse_handler", fake_pdf_handler)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 1
    assert pop_calls == ["chat_jobs", "pdf_parse"]
    assert handled == [{"document_task_id": "dt-1"}]


def test_run_once_dispatches_document_jobs_after_pdf_parse(monkeypatch) -> None:
    pop_calls: list[str] = []
    handled: list[dict[str, Any]] = []

    def fake_pop_job(queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        pop_calls.append(queue_name)
        if queue_name == "document_jobs":
            return {"document_task_id": "dt-2", "stage": "extract"}
        return None

    def fake_document_handler(payload: dict[str, Any]) -> None:
        handled.append(payload)

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._document_jobs_handler", fake_document_handler)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 1
    assert pop_calls == ["chat_jobs", "pdf_parse", "document_jobs"]
    assert handled == [{"document_task_id": "dt-2", "stage": "extract"}]


def test_run_once_dispatches_keyword_jobs_after_document_queues(monkeypatch) -> None:
    pop_calls: list[str] = []
    handled: list[dict[str, Any]] = []

    def fake_pop_job(queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        pop_calls.append(queue_name)
        if queue_name == "keyword_jobs":
            return {"keyword_job_id": "kj-1", "topic_id": "top-1"}
        return None

    def fake_keyword_handler(payload: dict[str, Any]) -> None:
        handled.append(payload)

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._keyword_jobs_handler", fake_keyword_handler)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 1
    assert pop_calls == ["chat_jobs", "pdf_parse", "document_jobs", "keyword_jobs"]
    assert handled == [{"keyword_job_id": "kj-1", "topic_id": "top-1"}]


def test_run_once_dispatches_reconcile_jobs_last(monkeypatch) -> None:
    pop_calls: list[str] = []
    handled: list[dict[str, Any]] = []

    def fake_pop_job(queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        pop_calls.append(queue_name)
        if queue_name == "reconcile_jobs":
            return {"reconcile_job_id": "rj-1", "scope": "full_table"}
        return None

    def fake_reconcile_handler(payload: dict[str, Any]) -> None:
        handled.append(payload)

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._reconcile_jobs_handler", fake_reconcile_handler)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 1
    assert pop_calls == [
        "chat_jobs",
        "pdf_parse",
        "document_jobs",
        "keyword_jobs",
        "reconcile_jobs",
    ]
    assert handled == [{"reconcile_job_id": "rj-1", "scope": "full_table"}]


def test_run_once_rotates_start_queue_between_ticks(monkeypatch) -> None:
    calls: list[str] = []

    def fake_pop_job(queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        calls.append(queue_name)
        return None

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._queue_cursor", 0)
    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 0
    assert run_once(broker_url="redis://worker-broker") == 0
    assert calls[:2] == ["chat_jobs", "pdf_parse"]


def test_run_once_continues_when_handler_raises(monkeypatch) -> None:
    pop_calls: list[str] = []
    handled: list[dict[str, Any]] = []

    def fake_pop_job(queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        pop_calls.append(queue_name)
        if queue_name == "chat_jobs":
            return {"conversation_id": "c-1"}
        if queue_name == "pdf_parse":
            return {"document_task_id": "dt-1"}
        return None

    def bad_chat_handler(_payload: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    def good_pdf_handler(payload: dict[str, Any]) -> None:
        handled.append(payload)

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setattr("app.worker._chat_jobs_handler", bad_chat_handler)
    monkeypatch.setattr("app.worker._pdf_parse_handler", good_pdf_handler)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 1
    assert pop_calls[:2] == ["chat_jobs", "pdf_parse"]
    assert handled == [{"document_task_id": "dt-1"}]
