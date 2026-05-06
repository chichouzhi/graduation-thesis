from __future__ import annotations

from typing import Any

from app import create_app
from app.chat.model import ChatJob, Conversation, Message, MessageAsyncTaskStatus
from app.chat.service import ChatService
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


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


def test_run_once_uses_current_app_broker_config_when_env_missing(monkeypatch) -> None:
    app = create_app()
    app.config["BROKER_URL"] = "redis://app-config-broker"
    seen_urls: list[str] = []

    class _Redis:
        def lpop(self, _key: str) -> bytes | None:
            return None

    def fake_redis_client_from_url(broker_url=None):
        seen_urls.append(str(broker_url))
        return _Redis()

    monkeypatch.setattr("app.task.queue._redis_client_from_url", fake_redis_client_from_url)
    monkeypatch.delenv("BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr("app.worker._queue_cursor", 0)

    from app.worker import run_once

    with app.app_context():
        assert run_once() == 0

    assert seen_urls == [
        "redis://app-config-broker",
        "redis://app-config-broker",
        "redis://app-config-broker",
        "redis://app-config-broker",
        "redis://app-config-broker",
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


def test_run_once_completes_chat_job_writeback(monkeypatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(
            username="worker-runtime-user",
            role=UserRole.student,
            display_name="worker-runtime-user",
            password_hash="x",
        )
        term = Term(name="worker-runtime-term")
        db.session.add_all([user, term])
        db.session.commit()
        conversation = Conversation(user_id=user.id, term_id=term.id, title="worker-runtime-conv")
        db.session.add(conversation)
        db.session.commit()

        monkeypatch.setattr(
            "app.adapter.llm.complete",
            lambda messages, **_: {
                "content": "worker final answer",
                "usage": {"total_tokens": 7},
                "model": "gpt-4o-mini",
                "provider_request_id": "provider-worker-1",
            },
        )
        monkeypatch.setattr(
            "app.chat.service.chat_service.get_policy_gateway",
            lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
        )

        accepted = ChatService().send_user_message(conversation.id, "hello worker", user.id)

        from app.worker import run_once

        assert run_once() == 1
        db.session.expire_all()
        job = db.session.get(ChatJob, accepted["job_id"])
        assistant = db.session.get(Message, accepted["assistant_message"]["id"])
        assert job is not None
        assert assistant is not None
        assert job.status == MessageAsyncTaskStatus.done
        assert job.started_at is not None
        assert job.finished_at is not None
        assert job.provider_request_id == "provider-worker-1"
        assert job.model_name == "gpt-4o-mini"
        assert job.usage_json == {"total_tokens": 7}
        assert assistant.delivery_status == MessageAsyncTaskStatus.done
        assert assistant.content == "worker final answer"
