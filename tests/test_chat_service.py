from __future__ import annotations

import pytest

from app import create_app
from app.chat.model import (
    ChatJob,
    Conversation,
    ConversationContextType,
    Message,
    MessageAsyncTaskStatus,
    MessageRole,
)
from app.common.policy import PolicyDenied
from app.chat.service import ChatService
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def _create_user(*, username: str) -> User:
    user = User(username=username, role=UserRole.student, display_name=username, password_hash="x")
    db.session.add(user)
    db.session.commit()
    return user


def _create_term(name: str = "2026 春") -> Term:
    term = Term(name=name)
    db.session.add(term)
    db.session.commit()
    return term


def _create_conversation(
    *,
    user_id: str,
    term_id: str,
    title: str,
    context_type: ConversationContextType | None = None,
    context_ref_id: str | None = None,
) -> Conversation:
    conv = Conversation(
        user_id=user_id,
        term_id=term_id,
        title=title,
        context_type=context_type,
        context_ref_id=context_ref_id,
    )
    db.session.add(conv)
    db.session.commit()
    return conv


def _create_message(*, conversation_id: str, role: MessageRole, content: str) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    db.session.add(msg)
    db.session.commit()
    return msg


def test_list_conversations_for_user_returns_paginated_current_user_rows() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-1")
        other = _create_user(username="u-chat-2")
        term = _create_term()
        _create_conversation(user_id=user.id, term_id=term.id, title="c-1")
        _create_conversation(user_id=user.id, term_id=term.id, title="c-2")
        _create_conversation(user_id=other.id, term_id=term.id, title="other")

        payload = ChatService().list_conversations_for_user(user.id, page=1, page_size=10)
        titles = [item["title"] for item in payload["items"]]
        assert set(titles) == {"c-1", "c-2"}
        assert payload["page"] == 1
        assert payload["page_size"] == 10
        assert payload["total"] == 2


def test_list_conversations_for_user_empty_when_user_missing() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        payload = ChatService().list_conversations_for_user("missing-user")
        assert payload == {"items": [], "page": 1, "page_size": 20, "total": 0}


def test_list_conversations_for_user_rejects_invalid_pagination() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        _create_user(username="u-chat-3")
        svc = ChatService()

        with pytest.raises(ValueError, match="page must be >= 1"):
            svc.list_conversations_for_user("x", page=0)
        with pytest.raises(ValueError, match="page_size must be >= 1"):
            svc.list_conversations_for_user("x", page_size=0)


def test_create_conversation_for_user_requires_term_id_and_persists() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-create")
        term = _create_term("2027 春")
        svc = ChatService()

        created = svc.create_conversation_for_user(
            user.id,
            {
                "term_id": term.id,
                "title": "新会话",
                "context_type": "topic",
                "context_ref_id": "topic-1",
            },
        )
        assert created["term_id"] == term.id
        assert created["title"] == "新会话"
        assert created["context_type"] == "topic"
        assert created["context_ref_id"] == "topic-1"

        with pytest.raises(ValueError, match="term_id is required"):
            svc.create_conversation_for_user(user.id, {"title": "missing-term"})


def test_create_conversation_for_user_rejects_invalid_context_type() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-create-2")
        term = _create_term("2027 秋")
        svc = ChatService()

        with pytest.raises(ValueError, match="context_type must be one of"):
            svc.create_conversation_for_user(
                user.id,
                {"term_id": term.id, "context_type": "invalid"},
            )


def test_get_conversation_for_user_reads_current_user_metadata() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-meta-1")
        other = _create_user(username="u-chat-meta-2")
        term = _create_term("2028 春")
        mine = _create_conversation(user_id=user.id, term_id=term.id, title="mine")
        _create_conversation(user_id=other.id, term_id=term.id, title="other")
        svc = ChatService()

        payload = svc.get_conversation_for_user(user.id, mine.id)
        assert payload is not None
        assert payload["id"] == mine.id
        assert payload["title"] == "mine"
        assert payload["term_id"] == term.id


def test_get_conversation_for_user_returns_none_when_not_visible() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-meta-3")
        other = _create_user(username="u-chat-meta-4")
        term = _create_term("2028 秋")
        others_conv = _create_conversation(user_id=other.id, term_id=term.id, title="other")
        svc = ChatService()

        assert svc.get_conversation_for_user(user.id, others_conv.id) is None
        assert svc.get_conversation_for_user(user.id, "missing-id") is None
        with pytest.raises(ValueError, match="conversation_id must be non-empty"):
            svc.get_conversation_for_user(user.id, "   ")


def test_archive_conversation_for_user_hides_conversation_from_reads() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-archive")
        term = _create_term("2029 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="to-archive")
        svc = ChatService()

        assert svc.archive_conversation_for_user(user.id, conv.id) is True
        assert svc.get_conversation_for_user(user.id, conv.id) is None
        payload = svc.list_conversations_for_user(user.id)
        assert payload["items"] == []
        assert payload["total"] == 0


def test_archive_conversation_for_user_returns_false_for_missing_or_other_owner() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-archive-2")
        other = _create_user(username="u-chat-archive-3")
        term = _create_term("2029 秋")
        other_conv = _create_conversation(user_id=other.id, term_id=term.id, title="other")
        svc = ChatService()

        assert svc.archive_conversation_for_user(user.id, "missing-id") is False
        assert svc.archive_conversation_for_user(user.id, other_conv.id) is False
        with pytest.raises(ValueError, match="conversation_id must be non-empty"):
            svc.archive_conversation_for_user(user.id, "  ")


def test_list_messages_for_conversation_supports_pagination_and_cursors() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-msg-1")
        term = _create_term("2030 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="msg")
        m1 = _create_message(conversation_id=conv.id, role=MessageRole.user, content="u1")
        m2 = _create_message(conversation_id=conv.id, role=MessageRole.assistant, content="a1")
        m3 = _create_message(conversation_id=conv.id, role=MessageRole.user, content="u2")
        svc = ChatService()

        full_payload = svc.list_messages_for_conversation(user.id, conv.id, page=1, page_size=10, order="asc")
        ordered_ids = [item["id"] for item in full_payload["items"]]
        assert set(ordered_ids) == {m1.id, m2.id, m3.id}

        page_payload = svc.list_messages_for_conversation(user.id, conv.id, page=1, page_size=2, order="asc")
        assert page_payload["total"] == 3
        assert [item["id"] for item in page_payload["items"]] == ordered_ids[:2]

        after_payload = svc.list_messages_for_conversation(
            user.id,
            conv.id,
            after_message_id=ordered_ids[0],
            order="asc",
        )
        assert [item["id"] for item in after_payload["items"]] == ordered_ids[1:]


def test_list_messages_for_conversation_rejects_conflicting_cursors() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-msg-2")
        term = _create_term("2030 秋")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="msg2")
        m1 = _create_message(conversation_id=conv.id, role=MessageRole.user, content="u")
        m2 = _create_message(conversation_id=conv.id, role=MessageRole.assistant, content="a")
        svc = ChatService()

        with pytest.raises(ValueError, match="mutually exclusive"):
            svc.list_messages_for_conversation(
                user.id,
                conv.id,
                after_message_id=m1.id,
                before_message_id=m2.id,
            )


def test_send_user_message_calls_chat_orchestration_build_only(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-send-1")
        term = _create_term("2031 春")
        conv = _create_conversation(
            user_id=user.id,
            term_id=term.id,
            title="send",
            context_type=ConversationContextType.topic,
            context_ref_id="topic-42",
        )
        seen_build: dict[str, object] = {}
        seen_payload: dict[str, object] = {}

        def fake_build_messages(**kwargs: object) -> list[dict[str, str]]:
            seen_build.update(kwargs)
            return [
                {"role": "system", "content": "s"},
                {"role": "assistant", "content": "h1"},
                {"role": "user", "content": "new"},
            ]

        def fake_enqueue(payload: dict | None = None, **_kwargs: object) -> dict[str, str]:
            assert isinstance(payload, dict)
            seen_payload.update(payload)
            return {"job_id": "job-1"}

        def fail_run_turn(**_kwargs: object) -> None:
            raise AssertionError("run_turn must not be called in service send path")

        monkeypatch.setattr("app.use_cases.chat_orchestration.build_messages", fake_build_messages)
        monkeypatch.setattr("app.use_cases.chat_orchestration.run_turn", fail_run_turn)
        monkeypatch.setattr("app.task.queue.enqueue_chat_jobs", fake_enqueue)
        policy_calls: list[dict[str, object]] = []

        class _Policy:
            @staticmethod
            def assert_can_enqueue(*, queue: str, **context: object) -> None:
                policy_calls.append({"queue": queue, **context})

        monkeypatch.setattr("app.chat.service.chat_service.get_policy_gateway", lambda: _Policy)

        ChatService().send_user_message(conv.id, "new", user.id)

        assert seen_build["user_content"] == "new"
        assert seen_build["term_id"] == term.id
        assert seen_build["context_type"] == "topic"
        assert seen_build["context_ref_id"] == "topic-42"
        assert seen_payload["term_id"] == term.id
        assert seen_payload["history"] == [{"role": "assistant", "content": "h1"}]
        assert seen_payload["context_type"] == "topic"
        assert seen_payload["context_ref_id"] == "topic-42"
        assert policy_calls == [
            {
                "queue": "chat_jobs",
                "conversation_id": conv.id,
                "user_id": user.id,
                "term_id": term.id,
            }
        ]
        job = db.session.get(ChatJob, seen_payload["job_id"])
        assert job is not None
        assert job.status == MessageAsyncTaskStatus.pending
        mu = db.session.get(Message, seen_payload["user_message_id"])
        ma = db.session.get(Message, seen_payload["assistant_message_id"])
        assert mu is not None and mu.content == "new" and mu.delivery_status is None
        assert ma is not None and ma.content == "" and ma.delivery_status == MessageAsyncTaskStatus.pending


def test_send_user_message_commits_before_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-send-2")
        term = _create_term("2031 秋")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="send2")
        events: list[str] = []

        monkeypatch.setattr(
            "app.use_cases.chat_orchestration.build_messages",
            lambda **_kwargs: [{"role": "system", "content": "s"}, {"role": "user", "content": "x"}],
        )
        monkeypatch.setattr(
            "app.chat.service.chat_service.get_policy_gateway",
            lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
        )
        orig_commit = db.session.commit

        def wrapped_commit() -> None:
            events.append("commit")
            orig_commit()

        def capture_enqueue(payload: dict | None = None, **_kwargs: object) -> dict[str, str]:
            assert isinstance(payload, dict)
            assert db.session.get(ChatJob, payload["job_id"]) is not None
            events.append("enqueue")
            return {"job_id": str(payload["job_id"])}

        monkeypatch.setattr(db.session, "commit", wrapped_commit)
        monkeypatch.setattr("app.task.queue.enqueue_chat_jobs", capture_enqueue)

        ChatService().send_user_message(conv.id, "x", user.id)

        assert "commit" in events and "enqueue" in events
        assert events.index("commit") < events.index("enqueue")


def test_send_user_message_marks_failed_when_enqueue_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = _create_user(username="u-chat-send-fail")
        term = _create_term("2032 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="send-fail")

        monkeypatch.setattr(
            "app.use_cases.chat_orchestration.build_messages",
            lambda **_kwargs: [{"role": "system", "content": "s"}, {"role": "user", "content": "x"}],
        )
        monkeypatch.setattr(
            "app.chat.service.chat_service.get_policy_gateway",
            lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
        )

        def fail_enqueue(_payload: dict | None = None, **_kwargs: object) -> dict[str, str]:
            raise RuntimeError("redis down")

        monkeypatch.setattr("app.task.queue.enqueue_chat_jobs", fail_enqueue)

        with pytest.raises(PolicyDenied) as ex:
            ChatService().send_user_message(conv.id, "x", user.id)
        assert ex.value.code.value == "QUEUE_UNAVAILABLE"

        failed_jobs = (
            ChatJob.query.filter_by(conversation_id=conv.id, status=MessageAsyncTaskStatus.failed)
            .order_by(ChatJob.created_at.desc(), ChatJob.job_id.desc())
            .all()
        )
        assert failed_jobs
        job = failed_jobs[0]
        assert job.error_code == "QUEUE_UNAVAILABLE"
        assert "redis down" in (job.error_message or "")
        user_msg = db.session.get(Message, job.user_message_id)
        assert user_msg is not None
        assert user_msg.content == "x"
        assert user_msg.delivery_status is None
        assistant = db.session.get(Message, job.assistant_message_id)
        assert assistant is not None
        assert assistant.delivery_status == MessageAsyncTaskStatus.failed
