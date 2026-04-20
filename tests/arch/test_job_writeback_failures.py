"""it-job-writeback-failures：覆盖 chat/document/keyword 失败路径写回语义。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.task.chat_jobs import handle_chat_job
from app.task.document_jobs import run as run_document_job
from app.task.keyword_jobs import handle_keyword_job


def test_it_job_writeback_failures_chat_surfaces_error_with_writeback_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_build_messages(**kwargs: object) -> list[dict[str, str]]:
        return [{"role": "user", "content": str(kwargs["user_content"])}]

    def fake_run_turn(**kwargs: object) -> None:
        seen.update(kwargs)
        raise RuntimeError("llm down")

    monkeypatch.setattr("app.use_cases.chat_orchestration.build_messages", fake_build_messages)
    monkeypatch.setattr("app.use_cases.chat_orchestration.run_turn", fake_run_turn)

    payload = {
        "job_id": "job-1",
        "conversation_id": "conv-1",
        "user_message_id": "msg-u-1",
        "assistant_message_id": "msg-a-1",
        "term_id": "term-1",
        "user_id": "user-1",
        "content": "hello",
    }
    with pytest.raises(RuntimeError, match="llm down"):
        handle_chat_job(payload)

    assert seen["job_id"] == "job-1"
    assert seen["conversation_id"] == "conv-1"
    assert seen["user_message_id"] == "msg-u-1"
    assert seen["assistant_message_id"] == "msg-a-1"
    assert seen["term_id"] == "term-1"


def test_it_job_writeback_failures_document_sets_failed_and_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, dict[str, object]]] = []

    def fake_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        writes.append((document_task_id, patch))

    def boom(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("chunk llm timeout")

    monkeypatch.setattr("app.task.document_jobs._default_writeback", fake_writeback)
    monkeypatch.setattr("app.task.document_jobs.handle_document_job", boom)

    payload = {
        "document_task_id": "dt-1",
        "user_id": "u-1",
        "storage_path": "/tmp/doc.pdf",
        "term_id": "term-1",
        "stage": "summarize_chunk",
        "chunk_index": 0,
    }
    with pytest.raises(RuntimeError, match="chunk llm timeout"):
        run_document_job(payload)

    assert writes[0] == ("dt-1", {"status": "pending"})
    assert writes[1] == ("dt-1", {"status": "running"})
    assert writes[2][0] == "dt-1"
    assert writes[2][1]["status"] == "failed"
    assert writes[2][1]["error_code"] == "DOMAIN_ERROR"
    assert "chunk llm timeout" in str(writes[2][1]["error_message"])


def test_it_job_writeback_failures_keyword_sets_failed_and_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_payload: dict[str, object]) -> dict[str, str]:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("app.use_cases.topic_keywords.run_keyword_extraction_from_payload", boom)
    from app.extensions import db

    topic = SimpleNamespace(
        portrait_json=None,
        llm_keyword_job_id=None,
        llm_keyword_job_status=None,
    )
    session = SimpleNamespace(get=lambda _m, _i: topic, commit=MagicMock())
    monkeypatch.setattr(db, "session", session, raising=False)

    payload = {
        "keyword_job_id": "kj-1",
        "topic_id": "tp-1",
        "term_id": "tm-1",
        "text_snapshot": "snapshot",
        "requested_by_user_id": "u-1",
    }
    with pytest.raises(RuntimeError, match="provider unavailable"):
        handle_keyword_job(payload)

    assert topic.llm_keyword_job_id == "kj-1"
    assert topic.llm_keyword_job_status.value == "failed"
    assert topic.portrait_json["error_code"] == "DOMAIN_ERROR"
    assert "provider unavailable" in topic.portrait_json["error_message"]
