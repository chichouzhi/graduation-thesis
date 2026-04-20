"""AG-012：``messages`` ORM；assistant 占位、``delivery_status`` 与契约 ``Message.status`` 对齐。"""
from __future__ import annotations

from sqlalchemy import inspect

from app import create_app
from app.chat.model import (
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
        username="u-msg-1",
        role=UserRole.student,
        display_name="Student",
    )


def _conversation() -> tuple[User, Term, Conversation]:
    u = _user()
    t = Term(name="2026 春")
    db.session.add_all([u, t])
    db.session.commit()
    c = Conversation(user_id=u.id, term_id=t.id, title="聊")
    db.session.add(c)
    db.session.commit()
    return u, t, c


def test_message_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        _, _, c = _conversation()

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

        loaded_u = db.session.get(Message, m_user.id)
        loaded_a = db.session.get(Message, m_asst.id)
        assert loaded_u is not None and loaded_a is not None

        bu = loaded_u.to_message()
        assert bu["id"] == loaded_u.id
        assert bu["conversation_id"] == c.id
        assert bu["role"] == "user"
        assert bu["content"] == "你好"
        assert bu["status"] is None
        assert bu["created_at"].endswith("Z")

        ba = loaded_a.to_message()
        assert ba["role"] == "assistant"
        assert ba["content"] == ""
        assert ba["status"] == "pending"
        assert "updated_at" in ba and ba["updated_at"].endswith("Z")


def test_messages_conversation_id_column_is_indexed() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        insp = inspect(db.engine)
        indexes = insp.get_indexes("messages")
        column_sets = [tuple(idx.get("column_names") or ()) for idx in indexes]
        assert any("conversation_id" in cols for cols in column_sets)


def test_delete_conversation_cascades_messages() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        _, _, c = _conversation()
        m = Message(
            conversation_id=c.id,
            role=MessageRole.user,
            content="x",
        )
        db.session.add(m)
        db.session.commit()
        mid = m.id

        db.session.delete(c)
        db.session.commit()
        assert db.session.get(Message, mid) is None


def test_assistant_requires_delivery_status_for_placeholder_contract_path() -> None:
    """Worker/API 序列化层保证 assistant 异步路径有 ``status``；ORM 允许写入 pending 占位。"""
    app = create_app()
    with app.app_context():
        db.create_all()
        _, _, c = _conversation()
        m = Message(
            conversation_id=c.id,
            role=MessageRole.assistant,
            content="",
            delivery_status=MessageAsyncTaskStatus.pending,
        )
        db.session.add(m)
        db.session.commit()
        assert db.session.get(Message, m.id) is not None
