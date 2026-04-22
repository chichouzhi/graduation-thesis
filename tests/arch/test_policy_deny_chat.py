"""R-POLICY-SVC / §5 it-policy-deny-chat — Policy 拒绝时 429/503 且不入队。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.chat.model import Conversation
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


@pytest.fixture()
def app_ctx():
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="policy-deny-chat",
            role=UserRole.student,
            display_name="pdc",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(user)
        term = Term(name="pd-term")
        db.session.add(term)
        db.session.commit()
        conv = Conversation(user_id=user.id, term_id=term.id, title="c1")
        db.session.add(conv)
        db.session.commit()
        yield app, user, conv


def test_policy_deny_chat_no_enqueue_on_policy_denied(monkeypatch, app_ctx):
    app, user, conv = app_ctx
    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "policy-deny-chat", "password": "pw-123"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    class _Deny:
        def assert_can_enqueue(self, **_kwargs):
            raise PolicyDenied("depth", code=ErrorCode.POLICY_QUEUE_DEPTH)

    monkeypatch.setattr("app.chat.service.chat_service.get_policy_gateway", lambda: _Deny())
    spy = MagicMock()
    monkeypatch.setattr("app.chat.service.chat_service.queue_mod.enqueue_chat_jobs", spy)

    resp = client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        json={"content": "hello policy"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in {429, 503}
    assert resp.get_json()["error"]["code"] == "POLICY_QUEUE_DEPTH"
    spy.assert_not_called()
