from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.chat.model import ChatJob, Conversation, Message, MessageAsyncTaskStatus, MessageRole
from app.extensions import db
from app.identity.model import User, UserRole
from app.task.chat_jobs import ChatJobPayload, handle_chat_job
from app.terms.model import Term
from app.use_cases.chat_orchestration import run_turn


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


def test_handle_chat_job_skips_llm_for_terminal_job(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        job = db.session.get(ChatJob, seeded["job_id"])
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert job is not None
        assert assistant is not None
        job.status = MessageAsyncTaskStatus.done
        job.started_at = job.created_at
        job.finished_at = job.updated_at
        job.provider_request_id = "provider-req-existing"
        job.model_name = "gpt-4o-mini"
        job.usage_json = {"total_tokens": 3}
        assistant.delivery_status = MessageAsyncTaskStatus.done
        assistant.content = "cached answer"
        db.session.commit()

        def _fail_complete(_messages: list[dict[str, str]], **_kwargs: Any) -> dict[str, Any]:
            raise AssertionError("llm.complete must not be called for terminal jobs")

        monkeypatch.setattr("app.adapter.llm.complete", _fail_complete)

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
        reloaded_job = db.session.get(ChatJob, seeded["job_id"])
        reloaded_assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert reloaded_job is not None
        assert reloaded_assistant is not None
        assert reloaded_job.status == MessageAsyncTaskStatus.done
        assert reloaded_job.provider_request_id == "provider-req-existing"
        assert reloaded_job.usage_json == {"total_tokens": 3}
        assert reloaded_assistant.delivery_status == MessageAsyncTaskStatus.done
        assert reloaded_assistant.content == "cached answer"


def test_handle_chat_job_marks_failed_when_message_rows_do_not_match_job(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        second_conversation = Conversation(
            user_id=seeded["user_id"],
            term_id=seeded["term_id"],
            title="worker-chat-mismatch",
        )
        db.session.add(second_conversation)
        db.session.commit()

        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert assistant is not None
        assistant.conversation_id = second_conversation.id
        db.session.commit()

        monkeypatch.setattr("app.adapter.llm.complete", lambda *_args, **_kwargs: {"content": "unused"})

        with pytest.raises(ValueError, match="same conversation"):
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
        remapped_assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert job is not None
        assert remapped_assistant is not None
        assert job.status == MessageAsyncTaskStatus.failed
        assert job.finished_at is not None
        assert "same conversation" in (job.error_message or "")
        assert remapped_assistant.delivery_status == MessageAsyncTaskStatus.failed


def test_handle_chat_job_rolls_back_and_persists_failed_state_when_final_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            },
        )

        orig_commit = db.session.commit
        orig_rollback = db.session.rollback
        commit_calls = {"count": 0}
        rollback_calls: list[str] = []

        def flaky_commit() -> None:
            commit_calls["count"] += 1
            if commit_calls["count"] == 2:
                raise RuntimeError("persist final state failed")
            orig_commit()

        def tracked_rollback() -> None:
            rollback_calls.append("rollback")
            orig_rollback()

        monkeypatch.setattr(db.session, "commit", flaky_commit)
        monkeypatch.setattr(db.session, "rollback", tracked_rollback)

        with pytest.raises(RuntimeError, match="persist final state failed"):
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
        assert rollback_calls == ["rollback"]
        assert job is not None
        assert assistant is not None
        assert job.status == MessageAsyncTaskStatus.failed
        assert job.finished_at is not None
        assert job.error_message == "persist final state failed"
        assert assistant.delivery_status == MessageAsyncTaskStatus.failed


def test_run_turn_marks_existing_job_failed_when_message_rows_are_mismatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert assistant is not None
        other_conversation = Conversation(
            user_id=seeded["user_id"],
            term_id=seeded["term_id"],
            title="other-conversation",
        )
        db.session.add(other_conversation)
        db.session.commit()
        assistant.conversation_id = other_conversation.id
        db.session.commit()

        def _should_not_call_llm(_messages: list[dict[str, str]], **_kwargs: Any) -> dict[str, Any]:
            raise AssertionError("LLM should not be called when persistence rows are mismatched")

        monkeypatch.setattr("app.adapter.llm.complete", _should_not_call_llm)

        with pytest.raises(ValueError, match="chat job message rows do not belong to the same conversation"):
            run_turn(
                conversation_id=seeded["conversation_id"],
                messages=[{"role": "user", "content": "hello"}],
                term_id=seeded["term_id"],
                job_id=seeded["job_id"],
                user_message_id=seeded["user_message_id"],
                assistant_message_id=seeded["assistant_message_id"],
                user_id=seeded["user_id"],
            )

        db.session.expire_all()
        job = db.session.get(ChatJob, seeded["job_id"])
        assert job is not None
        assert job.status == MessageAsyncTaskStatus.failed
        assert job.finished_at is not None
        assert "same conversation" in (job.error_message or "")


def test_run_turn_marks_job_failed_when_claim_commit_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        original_commit = db.session.commit
        original_rollback = db.session.rollback
        commit_calls: list[str] = []
        rollback_calls: list[str] = []

        def _flaky_commit() -> None:
            commit_calls.append("commit")
            if len(commit_calls) == 1:
                raise SQLAlchemyError("claim write failed")
            original_commit()

        def _wrapped_rollback() -> None:
            rollback_calls.append("rollback")
            original_rollback()

        def _should_not_call_llm(_messages: list[dict[str, str]], **_kwargs: Any) -> dict[str, Any]:
            raise AssertionError("LLM should not be called when claim persistence fails")

        monkeypatch.setattr(db.session, "commit", _flaky_commit)
        monkeypatch.setattr(db.session, "rollback", _wrapped_rollback)
        monkeypatch.setattr("app.adapter.llm.complete", _should_not_call_llm)

        with pytest.raises(SQLAlchemyError, match="claim write failed"):
            run_turn(
                conversation_id=seeded["conversation_id"],
                messages=[{"role": "user", "content": "hello"}],
                term_id=seeded["term_id"],
                job_id=seeded["job_id"],
                user_message_id=seeded["user_message_id"],
                assistant_message_id=seeded["assistant_message_id"],
                user_id=seeded["user_id"],
            )

        db.session.expire_all()
        job = db.session.get(ChatJob, seeded["job_id"])
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert rollback_calls
        assert job is not None and job.status == MessageAsyncTaskStatus.failed
        assert assistant is not None and assistant.delivery_status == MessageAsyncTaskStatus.failed
        assert job.started_at is not None
        assert "claim write failed" in (job.error_message or "")


def test_run_turn_rolls_back_and_marks_failed_when_done_writeback_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        original_commit = db.session.commit
        original_rollback = db.session.rollback
        commit_calls: list[str] = []
        rollback_calls: list[str] = []
        llm_calls: list[str] = []

        def _flaky_commit() -> None:
            commit_calls.append("commit")
            if len(commit_calls) == 2:
                raise SQLAlchemyError("done write failed")
            original_commit()

        def _wrapped_rollback() -> None:
            rollback_calls.append("rollback")
            original_rollback()

        def _success(_messages: list[dict[str, str]], **_kwargs: Any) -> dict[str, Any]:
            llm_calls.append("llm")
            return {
                "content": "worker answer",
                "usage": {"total_tokens": 12},
                "model": "gpt-4o-mini",
                "provider_request_id": "req-provider-1",
            }

        monkeypatch.setattr(db.session, "commit", _flaky_commit)
        monkeypatch.setattr(db.session, "rollback", _wrapped_rollback)
        monkeypatch.setattr("app.adapter.llm.complete", _success)

        with pytest.raises(SQLAlchemyError, match="done write failed"):
            run_turn(
                conversation_id=seeded["conversation_id"],
                messages=[{"role": "user", "content": "hello"}],
                term_id=seeded["term_id"],
                job_id=seeded["job_id"],
                user_message_id=seeded["user_message_id"],
                assistant_message_id=seeded["assistant_message_id"],
                user_id=seeded["user_id"],
            )

        db.session.expire_all()
        job = db.session.get(ChatJob, seeded["job_id"])
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert llm_calls == ["llm"]
        assert rollback_calls
        assert job is not None and job.status == MessageAsyncTaskStatus.failed
        assert assistant is not None and assistant.delivery_status == MessageAsyncTaskStatus.failed
        assert "done write failed" in (job.error_message or "")


@pytest.mark.parametrize("terminal_status", [MessageAsyncTaskStatus.done, MessageAsyncTaskStatus.failed])
def test_run_turn_skips_llm_for_terminal_jobs(
    terminal_status: MessageAsyncTaskStatus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seeded = _seed_chat_job_rows()
        job = db.session.get(ChatJob, seeded["job_id"])
        assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert job is not None
        assert assistant is not None
        job.status = terminal_status
        job.started_at = job.created_at
        job.finished_at = job.updated_at
        assistant.delivery_status = terminal_status
        assistant.content = "existing answer"
        db.session.commit()

        llm_calls: list[str] = []

        def _should_not_call_llm(_messages: list[dict[str, str]], **_kwargs: Any) -> dict[str, Any]:
            llm_calls.append("llm")
            return {"content": "unexpected"}

        monkeypatch.setattr("app.adapter.llm.complete", _should_not_call_llm)

        run_turn(
            conversation_id=seeded["conversation_id"],
            messages=[{"role": "user", "content": "hello"}],
            term_id=seeded["term_id"],
            job_id=seeded["job_id"],
            user_message_id=seeded["user_message_id"],
            assistant_message_id=seeded["assistant_message_id"],
            user_id=seeded["user_id"],
        )

        db.session.expire_all()
        loaded_job = db.session.get(ChatJob, seeded["job_id"])
        loaded_assistant = db.session.get(Message, seeded["assistant_message_id"])
        assert llm_calls == []
        assert loaded_job is not None and loaded_job.status == terminal_status
        assert loaded_assistant is not None and loaded_assistant.content == "existing answer"
