"""AG-011：``conversations`` ORM；``term_id`` 非空、索引与契约字段对齐。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect

from app import create_app
from app.chat.model import Conversation, ConversationContextType
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def _user() -> User:
    return User(
        username="u-conv-1",
        role=UserRole.student,
        display_name="Student",
    )


def test_conversation_persists_non_null_term_id_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = _user()
        t = Term(name="2026 春")
        db.session.add_all([u, t])
        db.session.commit()

        c = Conversation(
            user_id=u.id,
            term_id=t.id,
            title="讨论",
            context_type=ConversationContextType.topic,
            context_ref_id="topic-uuid-1",
        )
        db.session.add(c)
        db.session.commit()

        loaded = db.session.get(Conversation, c.id)
        assert loaded is not None
        assert loaded.term_id == t.id
        assert loaded.user_id == u.id

        body = loaded.to_conversation()
        assert body["id"] == loaded.id
        assert body["term_id"] == t.id
        assert body["title"] == "讨论"
        assert body["context_type"] == "topic"
        assert body["context_ref_id"] == "topic-uuid-1"
        assert body["created_at"].endswith("Z")
        assert "updated_at" in body and body["updated_at"].endswith("Z")


def test_conversation_term_id_column_is_indexed() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        insp = inspect(db.engine)
        indexes = insp.get_indexes("conversations")
        column_sets = [tuple(idx.get("column_names") or ()) for idx in indexes]
        assert any("term_id" in cols for cols in column_sets)


def test_conversation_requires_term_id() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = _user()
        db.session.add(u)
        db.session.commit()

        c = Conversation(user_id=u.id, term_id=None)  # type: ignore[arg-type]
        db.session.add(c)
        with pytest.raises(Exception):
            db.session.commit()


def test_conversation_term_fk_restrict_prevents_term_delete_when_referenced() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = _user()
        t = Term(name="届")
        db.session.add_all([u, t])
        db.session.commit()
        c = Conversation(user_id=u.id, term_id=t.id)
        db.session.add(c)
        db.session.commit()

        db.session.delete(t)
        with pytest.raises(Exception):
            db.session.commit()
