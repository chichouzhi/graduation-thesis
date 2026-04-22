"""§5 it-async-document：multipart 缺 term_id → 400；含 term_id → 202。"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def test_it_async_document_missing_term_id_400():
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="it-async-doc",
            role=UserRole.student,
            display_name="iad",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "it-async-doc", "password": "pw-123"},
    )
    token = login.get_json()["access_token"]
    resp = client.post(
        "/api/v1/document-tasks",
        data={"file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "a.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_it_async_document_post_202_under_800ms():
    import time

    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = User(
            username="it-async-doc2",
            role=UserRole.student,
            display_name="iad2",
            password_hash=generate_password_hash("pw-123"),
        )
        db.session.add(user)
        term = Term(name="it-doc-term")
        db.session.add(term)
        db.session.commit()
        tid = term.id

    client = app.test_client()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "it-async-doc2", "password": "pw-123"},
    )
    token = login.get_json()["access_token"]
    t0 = time.monotonic()
    resp = client.post(
        "/api/v1/document-tasks",
        data={"term_id": tid, "file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "b.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert time.monotonic() - t0 < 0.8
    assert resp.status_code == 202
    assert resp.get_json().get("term_id") == tid
