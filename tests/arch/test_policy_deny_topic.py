"""R-POLICY-SVC / §5 it-policy-deny-topic — Topic 写路径触发入队前 Policy 拒绝时 429/503 且不入队。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app import create_app
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app_ctx():
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = User(
            username="policy-deny-topic",
            role=UserRole.teacher,
            display_name="pdt",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(teacher)
        term = Term(name="pd-topic-term")
        db.session.add(term)
        db.session.commit()
        topic = Topic(
            title="t0",
            summary="s",
            requirements="r",
            tech_keywords=[],
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.draft,
            portrait_json={"keywords": [], "extracted_at": None},
        )
        db.session.add(topic)
        db.session.commit()
        yield app, teacher, topic


def test_policy_deny_topic_no_enqueue_on_policy_denied(monkeypatch, app_ctx):
    app, teacher, topic = app_ctx
    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "policy-deny-topic", "password": "pw-123"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    class _Deny:
        def assert_can_enqueue(self, **_kwargs):
            raise PolicyDenied("depth", code=ErrorCode.POLICY_QUEUE_DEPTH)

    monkeypatch.setattr("app.topic.service.topic_service.get_policy_gateway", lambda: _Deny())
    spy = MagicMock()
    monkeypatch.setattr("app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs", spy)

    resp = client.patch(
        f"/api/v1/topics/{topic.id}",
        json={"title": "t1-changed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in {429, 503}
    assert resp.get_json()["error"]["code"] == "POLICY_QUEUE_DEPTH"
    spy.assert_not_called()
