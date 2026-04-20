"""AG-013：``chat_jobs`` ORM；``job_id``、重试、``error_*``、列表索引与契约 ``ChatJob`` 对齐。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect

from app import create_app
from app.chat.model import (
    ChatJob,
    Conversation,
    Message,
    MessageAsyncTaskStatus,
    MessageRole,
)
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def _user() -> User:
    return User(
        username="u-cj-1",
        role=UserRole.student,
        display_name="Student",
    )


def _conversation_with_messages() -> tuple[Conversation, Message, Message]:
    u = _user()
    t = Term(name="2026 春")
    db.session.add_all([u, t])
    db.session.commit()
    c = Conversation(user_id=u.id, term_id=t.id, title="聊")
    db.session.add(c)
    db.session.commit()
    m_user = Message(
        conversation_id=c.id,
        role=MessageRole.user,
        content="你好",
        delivery_status=None,
    )
    m_asst = Message(
        conversation_id=c.id,
        role=MessageRole.assistant,
        content="",
        delivery_status=MessageAsyncTaskStatus.pending,
    )
    db.session.add_all([m_user, m_asst])
    db.session.commit()
    return c, m_user, m_asst


def test_chat_job_persists_retry_and_errors_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        c, mu, ma = _conversation_with_messages()
        nxt = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)

        job = ChatJob(
            job_id="job-test-1",
            conversation_id=c.id,
            user_message_id=mu.id,
            assistant_message_id=ma.id,
            status=MessageAsyncTaskStatus.running,
            error_code=None,
            error_message=None,
            retry_count=1,
            max_attempts=3,
            next_retry_at=nxt,
        )
        db.session.add(job)
        db.session.commit()

        loaded = db.session.get(ChatJob, "job-test-1")
        assert loaded is not None
        assert loaded.retry_count == 1
        assert loaded.max_attempts == 3
        assert loaded.next_retry_at == nxt

        body = loaded.to_chat_job()
        assert body["job_id"] == "job-test-1"
        assert body["conversation_id"] == c.id
        assert body["user_message_id"] == mu.id
        assert body["assistant_message_id"] == ma.id
        assert body["status"] == "running"
        assert body["retry_count"] == 1
        assert body["error_code"] is None
        assert body["error_message"] is None
        assert body["max_attempts"] == 3
        assert body["next_retry_at"] == "2026-05-01T12:00:00Z"
        assert body["created_at"].endswith("Z")
        assert body["updated_at"].endswith("Z")

        loaded.error_code = "LLM_RATE_LIMITED"
        loaded.error_message = "upstream"
        db.session.commit()
        body2 = db.session.get(ChatJob, "job-test-1")
        assert body2 is not None
        out = body2.to_chat_job()
        assert out["error_code"] == "LLM_RATE_LIMITED"
        assert out["error_message"] == "upstream"


def test_chat_jobs_status_created_at_composite_index_exists() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        insp = inspect(db.engine)
        indexes = insp.get_indexes("chat_jobs")
        column_sets = [tuple(idx.get("column_names") or ()) for idx in indexes]
        assert ("status", "created_at") in column_sets


def test_delete_conversation_cascades_chat_jobs() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        c, mu, ma = _conversation_with_messages()
        job = ChatJob(
            job_id="job-cascade-1",
            conversation_id=c.id,
            user_message_id=mu.id,
            assistant_message_id=ma.id,
            status=MessageAsyncTaskStatus.pending,
        )
        db.session.add(job)
        db.session.commit()
        jid = job.job_id

        db.session.delete(c)
        db.session.commit()
        assert db.session.get(ChatJob, jid) is None
