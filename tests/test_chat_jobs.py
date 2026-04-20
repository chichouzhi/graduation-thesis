from __future__ import annotations

from typing import Any

import pytest

from app.task.chat_jobs import ChatJobPayload, handle_chat_job


def _payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "job_id": "job-1",
        "conversation_id": "conv-1",
        "user_message_id": "um-1",
        "assistant_message_id": "am-1",
        "term_id": "term-1",
        "user_id": "user-1",
        "content": "请帮我总结本周任务",
        "client_request_id": "cr-1",
        "seq": 1,
        "request_id": "req-1",
    }
    base.update(overrides)
    return base


def test_chat_job_payload_requires_contract_fields() -> None:
    with pytest.raises(ValueError, match="ChatJobPayload.job_id must be non-empty"):
        ChatJobPayload.from_mapping(_payload(job_id=""))


def test_chat_job_payload_requires_content() -> None:
    with pytest.raises(ValueError, match="ChatJobPayload.content must be non-empty"):
        ChatJobPayload.from_mapping(_payload(content="  "))


def test_handle_chat_job_dispatches_with_real_payload_content(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_build: dict[str, Any] = {}
    seen_run: dict[str, Any] = {}

    def fake_build_messages(**kwargs: Any) -> list[dict[str, str]]:
        seen_build.update(kwargs)
        return [{"role": "user", "content": kwargs["user_content"]}]

    def fake_run_turn(**kwargs: Any) -> None:
        seen_run.update(kwargs)

    monkeypatch.setattr("app.use_cases.chat_orchestration.build_messages", fake_build_messages)
    monkeypatch.setattr("app.use_cases.chat_orchestration.run_turn", fake_run_turn)

    payload = _payload(content="真实消息")
    handle_chat_job(payload)

    assert seen_build["user_content"] == "真实消息"
    assert seen_build["term_id"] == "term-1"
    assert seen_run["conversation_id"] == "conv-1"
    assert seen_run["term_id"] == "term-1"
    assert seen_run["messages"] == [{"role": "user", "content": "真实消息"}]
