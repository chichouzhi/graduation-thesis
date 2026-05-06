"""队列与 Worker 契约：enqueue 须可观测；run_once 须返回处理计数（便于集成测断言）。"""
from __future__ import annotations

import pytest

from app import create_app


pytestmark = pytest.mark.contract


def test_enqueue_returns_job_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Redis:
        def rpush(self, _key: str, _value: str) -> int:
            return 1

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

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


def test_enqueue_serializes_payload_to_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    pushed: list[tuple[str, str]] = []

    class _Redis:
        def rpush(self, key: str, value: str) -> int:
            pushed.append((key, value))
            return 1

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import enqueue

    ret = enqueue("chat_jobs", {"conversation_id": "c1", "job_id": "job-1"}, broker_url="redis://broker")

    assert ret == {"job_id": "job-1"}
    assert pushed and pushed[0][0] == "chat_jobs"
    assert '"conversation_id": "c1"' in pushed[0][1]


def test_pop_job_deserializes_payload_from_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Redis:
        def lpop(self, key: str) -> bytes | None:
            assert key == "pdf_parse"
            return b'{"document_task_id":"dt-1","term_id":"t-1"}'

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import pop_job

    assert pop_job("pdf_parse", broker_url="redis://broker") == {
        "document_task_id": "dt-1",
        "term_id": "t-1",
    }


def test_pop_job_raises_when_decoded_payload_is_not_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Redis:
        def lpop(self, _key: str) -> bytes | None:
            return b'["not","a","mapping"]'

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import pop_job

    with pytest.raises(ValueError, match="mapping"):
        pop_job("chat_jobs", broker_url="redis://broker")


def test_enqueue_and_pop_job_fall_back_to_local_memory_when_broker_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.task.queue._LOCAL_QUEUE_BACKLOG", {}, raising=False)

    from app.task.queue import enqueue, pop_job

    assert enqueue("chat_jobs", {"conversation_id": "c1", "job_id": "job-1"}) == {"job_id": "job-1"}
    assert pop_job("chat_jobs") == {"conversation_id": "c1", "job_id": "job-1"}
    assert pop_job("chat_jobs") is None


def test_enqueue_uses_current_app_broker_url_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    pushed: list[tuple[str, str]] = []
    app = create_app()
    app.config["BROKER_URL"] = "redis://app-config-broker"

    class _Redis:
        def rpush(self, key: str, value: str) -> int:
            pushed.append((key, value))
            return 1

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import enqueue

    with app.app_context():
        ret = enqueue("chat_jobs", {"conversation_id": "c-app", "job_id": "job-app"})

    assert ret == {"job_id": "job-app"}
    assert pushed and pushed[0][0] == "chat_jobs"
    assert '"conversation_id": "c-app"' in pushed[0][1]


def test_pop_job_uses_current_app_redis_url_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    app.config["BROKER_URL"] = ""
    app.config["REDIS_URL"] = "redis://app-redis-url"

    class _Redis:
        def lpop(self, key: str) -> bytes | None:
            assert key == "pdf_parse"
            return b'{"document_task_id":"dt-app","term_id":"t-app"}'

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import pop_job

    with app.app_context():
        assert pop_job("pdf_parse") == {
            "document_task_id": "dt-app",
            "term_id": "t-app",
        }


def test_local_fallback_queue_state_is_isolated_per_app_instance() -> None:
    app_one = create_app()
    app_two = create_app()

    from app.task.queue import enqueue, pop_job

    with app_one.app_context():
        assert enqueue("chat_jobs", {"conversation_id": "app-one", "job_id": "job-one"}) == {
            "job_id": "job-one"
        }

    with app_two.app_context():
        assert pop_job("chat_jobs") is None

    with app_one.app_context():
        assert pop_job("chat_jobs") == {"conversation_id": "app-one", "job_id": "job-one"}
        assert pop_job("chat_jobs") is None


def test_app_config_none_broker_values_fall_back_to_local_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    app.config["BROKER_URL"] = None
    app.config["REDIS_URL"] = None

    def fail_redis_client(_broker_url=None):
        raise AssertionError("redis client should not be used when app config broker values are None")

    monkeypatch.setattr("app.task.queue._redis_client_from_url", fail_redis_client)

    from app.task.queue import enqueue, pop_job

    with app.app_context():
        assert enqueue("chat_jobs", {"conversation_id": "c-none", "job_id": "job-none"}) == {
            "job_id": "job-none"
        }
        assert pop_job("chat_jobs") == {"conversation_id": "c-none", "job_id": "job-none"}
        assert pop_job("chat_jobs") is None


def test_enqueue_rejects_unknown_queue_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Redis:
        def rpush(self, _key: str, _value: str) -> int:
            raise AssertionError("should not write for invalid queues")

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import enqueue

    with pytest.raises(ValueError, match="unknown queue"):
        enqueue("not_a_contract_queue", {"job_id": "job-1"})


def test_pop_job_rejects_unknown_queue_name(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Redis:
        def lpop(self, _key: str) -> bytes | None:
            raise AssertionError("should not read for invalid queues")

    monkeypatch.setattr("app.task.queue._redis_client_from_url", lambda broker_url=None: _Redis())

    from app.task.queue import pop_job

    with pytest.raises(ValueError, match="unknown queue"):
        pop_job("not_a_contract_queue", broker_url="redis://broker")


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

    class _GatewaySpy:
        @staticmethod
        def assert_can_enqueue(*, queue: str, **context: object) -> None:
            policy_calls.append({"queue": queue, **context})

    monkeypatch.setattr("app.extensions.get_policy_gateway", lambda: _GatewaySpy())

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
