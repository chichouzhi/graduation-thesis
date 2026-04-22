"""R-POLICY-SVC / §5 it-policy-deny-document — Policy 拒绝时 429/503 且不入队。"""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app import create_app
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app_ctx():
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="policy-deny-doc",
            role=UserRole.student,
            display_name="pdd",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(user)
        term = Term(name="pd-doc-term")
        db.session.add(term)
        db.session.commit()
        yield app, user, term


def test_policy_deny_document_no_enqueue_on_policy_denied(monkeypatch, app_ctx):
    app, user, term = app_ctx
    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "policy-deny-doc", "password": "pw-123"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]

    class _Deny:
        def assert_can_enqueue(self, **_kwargs):
            raise PolicyDenied("depth", code=ErrorCode.POLICY_QUEUE_DEPTH)

    monkeypatch.setattr("app.document.service.document_service.get_policy_gateway", lambda: _Deny())
    spy = MagicMock()
    monkeypatch.setattr("app.document.service.document_service.queue_mod.enqueue_pdf_parse", spy)

    resp = client.post(
        "/api/v1/document-tasks",
        data={
            "term_id": term.id,
            "file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "x.pdf"),
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in {429, 503}
    assert resp.get_json()["error"]["code"] == "POLICY_QUEUE_DEPTH"
    spy.assert_not_called()
