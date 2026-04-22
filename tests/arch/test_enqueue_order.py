"""§5 it-enqueue-order：Chat 受理路径 ``commit`` 先于 ``enqueue_chat_jobs``。"""
from __future__ import annotations

from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.chat.model import Conversation, Message, MessageAsyncTaskStatus, MessageRole
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def test_it_enqueue_order_commit_before_enqueue_chat(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="it-enq-order",
            role=UserRole.student,
            display_name="ieo",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(user)
        term = Term(name="enq-term")
        db.session.add(term)
        db.session.commit()
        conv = Conversation(user_id=user.id, term_id=term.id, title="c")
        db.session.add(conv)
        db.session.commit()
        cid = conv.id

    seq: list[str] = []
    orig_commit = db.session.commit

    def track_commit() -> None:
        seq.append("commit")
        orig_commit()

    def track_enqueue(*_a, **_k):
        seq.append("enqueue")
        return {"job_id": "stub-job"}

    monkeypatch.setattr(db.session, "commit", track_commit)
    monkeypatch.setattr("app.chat.service.chat_service.queue_mod.enqueue_chat_jobs", track_enqueue)

    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "it-enq-order", "password": "pw-123"},
    )
    token = login.get_json()["access_token"]
    resp = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "order-check"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    assert "enqueue" in seq
    assert "commit" in seq
    assert seq.index("enqueue") > seq.index("commit")


def test_it_enqueue_order_compensates_on_enqueue_failure(monkeypatch):
    """入队抛错后：ChatJob / assistant Message 标为 failed，HTTP 503（QUEUE_UNAVAILABLE）。"""
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="it-enq-fail",
            role=UserRole.student,
            display_name="ief",
            password_hash=generate_password_hash("pw-456"),
        )
        db.session.add(user)
        term = Term(name="enq-fail-term")
        db.session.add(term)
        db.session.commit()
        conv = Conversation(user_id=user.id, term_id=term.id, title="cf")
        db.session.add(conv)
        db.session.commit()
        cid = conv.id

    def boom_enqueue(*_a, **_k):
        raise RuntimeError("broker down")

    monkeypatch.setattr("app.chat.service.chat_service.queue_mod.enqueue_chat_jobs", boom_enqueue)

    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "it-enq-fail", "password": "pw-456"},
    )
    token = login.get_json()["access_token"]
    resp = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "will-fail-enqueue"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 503
    body = resp.get_json()
    assert body.get("error", {}).get("code") == "QUEUE_UNAVAILABLE"

    with app.app_context():
        from app.chat.model import ChatJob

        jobs = ChatJob.query.all()
        assert len(jobs) == 1
        assert jobs[0].status == MessageAsyncTaskStatus.failed
        assistants = Message.query.filter_by(role=MessageRole.assistant).all()
        assert len(assistants) == 1
        assert assistants[0].delivery_status == MessageAsyncTaskStatus.failed
