from __future__ import annotations

from typing import Any

import pytest

from app import create_app
from app.chat.model import ChatJob, Conversation, Message, MessageAsyncTaskStatus, MessageRole
from app.extensions import db
from app.identity.model import User, UserRole
from app.task.chat_jobs import ChatJobPayload, handle_chat_job
from app.terms.model import Term


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


def _seed_chat_job_rows() -> dict[str, str]:
    user = User(
        username="worker-chat-user",
        role=UserRole.student,
        display_name="worker-chat-user",
        password_hash="x",
    )
    term = Term(name="worker-chat-term")
    db.session.add_all([user, term])
    db.session.commit()

    conversation = Conversation(user_id=user.id, term_id=term.id, title="worker-chat")
    db.session.add(conversation)
    db.session.commit()

    user_message = Message(
        id="msg-user-1",
        conversation_id=conversation.id,
        role=MessageRole.user,
        content="请帮我总结本周任务",
        delivery_status=None,
    )
    assistant_message = Message(
        id="msg-assistant-1",
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content="",
        delivery_status=MessageAsyncTaskStatus.pending,
    )
    job = ChatJob(
        job_id="job-worker-1",
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        status=MessageAsyncTaskStatus.pending,
    )
    db.session.add_all([user_message, assistant_message, job])
    db.session.commit()
    return {
        "job_id": job.job_id,
        "conversation_id": conversation.id,
        "user_message_id": user_message.id,
        "assistant_message_id": assistant_message.id,
        "term_id": term.id,
        "user_id": user.id,
    }


def test_handle_chat_job_persists_done_state_and_runtime_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        monkeypatch.setattr(
            "app.adapter.llm.complete",
            lambda messages, **_: {
                "content": "worker answer",
                "usage": {"total_tokens": 12},
                "model": "gpt-4o-mini",
                "provider_request_id": "req-provider-1",
            },
        )

        handle_chat_job(
            _payload(
                job_id=seeded["job_id"],
                conversation_id=seeded["conversation_id"],
                user_message_id=seeded["user_message_id"],
                assistant_message_id=seeded["assistant_message_id"],
                term_id=seeded["term_id"],
                user_id=seeded["user_id"],
            )
        )

        db.session.expire_all()
        job = db.session.get(ChatJob, seeded["job_id"])
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert job is not None
        assert assistant is not None
        assert job.status == MessageAsyncTaskStatus.done
        assert job.started_at is not None
        assert job.finished_at is not None
        assert job.provider_request_id == "req-provider-1"
        assert job.model_name == "gpt-4o-mini"
        assert job.usage_json == {"total_tokens": 12}
        assert assistant.delivery_status == MessageAsyncTaskStatus.done
        assert assistant.content == "worker answer"


def test_handle_chat_job_persists_failed_state_when_llm_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()

        def _boom(_messages: list[dict[str, str]], **_kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("llm exploded")

        monkeypatch.setattr("app.adapter.llm.complete", _boom)

        with pytest.raises(RuntimeError, match="llm exploded"):
            handle_chat_job(
                _payload(
                    job_id=seeded["job_id"],
                    conversation_id=seeded["conversation_id"],
                    user_message_id=seeded["user_message_id"],
                    assistant_message_id=seeded["assistant_message_id"],
                    term_id=seeded["term_id"],
                    user_id=seeded["user_id"],
                )
            )

        db.session.expire_all()
        job = db.session.get(ChatJob, seeded["job_id"])
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert job is not None
        assert assistant is not None
        assert job.status == MessageAsyncTaskStatus.failed
        assert job.started_at is not None
        assert job.finished_at is not None
        assert job.error_message == "llm exploded"
        assert assistant.delivery_status == MessageAsyncTaskStatus.failed
