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

    from app.worker import run_once

    n = run_once(broker_url="redis://worker-broker")
    assert n == 1
    assert pop_calls == [("chat_jobs", "redis://worker-broker")]
    assert handled == [{"conversation_id": "c-1", "term_id": "t-1"}]


def test_run_once_returns_zero_when_queue_empty(monkeypatch) -> None:
    def fake_pop_job(_queue_name: str, **_kwargs: Any) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)

    from app.worker import run_once

    assert run_once(broker_url="redis://worker-broker") == 0


def test_run_once_reads_broker_url_from_environment(monkeypatch) -> None:
    seen_urls: list[str] = []

    def fake_pop_job(_queue_name: str, **kwargs: Any) -> dict[str, Any] | None:
        seen_urls.append(str(kwargs.get("broker_url", "")))
        return None

    monkeypatch.setattr("app.task.queue.pop_job", fake_pop_job)
    monkeypatch.setenv("BROKER_URL", "redis://env-broker")
    monkeypatch.delenv("REDIS_URL", raising=False)

    from app.worker import run_once

    assert run_once() == 0
    assert seen_urls == ["redis://env-broker"]
