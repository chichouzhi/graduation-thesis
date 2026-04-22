"""§5 it-async-chat：无 worker 时 POST messages 返回 202 且受理耗时上界（本地队列为占位）。"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.chat.model import Conversation
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def test_it_async_chat_post_messages_202_under_800ms():
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="it-async-chat",
            role=UserRole.student,
            display_name="iac",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(user)
        term = Term(name="it-chat-term")
        db.session.add(term)
        db.session.commit()
        conv = Conversation(user_id=user.id, term_id=term.id, title="c")
        db.session.add(conv)
        db.session.commit()
        cid = conv.id

    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "it-async-chat", "password": "pw-123"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    t0 = time.monotonic()
    resp = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "async-it"},
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 202
    assert elapsed < 0.8
    body = resp.get_json()
    assert body.get("job_id")
    assert body.get("user_message", {}).get("role") == "user"
