from __future__ import annotations

import io

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def _create_user(*, username: str, role: UserRole) -> User:
    user = User(
        username=username,
        role=role,
        display_name=username,
        password_hash=generate_password_hash("pass-123"),
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_term(name: str) -> Term:
    term = Term(name=name)
    db.session.add(term)
    db.session.commit()
    return term


def _login_and_get_token(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


def test_post_document_tasks_success_202() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="document-api-user", role=UserRole.student)
        term = _create_term("2046 春")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "document-api-user", "pass-123")
    resp = client.post(
        "/api/v1/document-tasks",
        data={
            "term_id": term_id,
            "file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "paper.pdf"),
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["term_id"] == term_id
    assert body["filename"] == "paper.pdf"
    assert body["status"] == "pending"


def test_post_document_tasks_validation_error_400_when_term_missing() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="document-api-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "document-api-bad", "pass-123")
    resp = client.post(
        "/api/v1/document-tasks",
        data={"file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "paper.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_document_tasks_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post(
        "/api/v1/document-tasks",
        data={"term_id": "x", "file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "paper.pdf")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_get_document_tasks_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="document-api-list", role=UserRole.student)
        term = _create_term("2047 春")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "document-api-list", "pass-123")
    create_resp = client.post(
        "/api/v1/document-tasks",
        data={
            "term_id": term_id,
            "file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "list-paper.pdf"),
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 202

    resp = client.get(
        "/api/v1/document-tasks?page=1&page_size=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["filename"] == "list-paper.pdf"


def test_get_document_tasks_invalid_pagination_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="document-api-list-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "document-api-list-bad", "pass-123")
    resp = client.get(
        "/api/v1/document-tasks?page=bad&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_document_tasks_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/document-tasks")
    assert resp.status_code == 401


def test_get_document_task_by_id_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="document-api-one", role=UserRole.student)
        term = _create_term("2048 春")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "document-api-one", "pass-123")
    create_resp = client.post(
        "/api/v1/document-tasks",
        data={
            "term_id": term_id,
            "file": (io.BytesIO(b"%PDF-1.4\n%%EOF"), "single-paper.pdf"),
        },
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 202
    task_id = create_resp.get_json()["id"]

    resp = client.get(f"/api/v1/document-tasks/{task_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == task_id
    assert body["filename"] == "single-paper.pdf"


def test_get_document_task_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="document-api-one-missing", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "document-api-one-missing", "pass-123")
    resp = client.get(
        "/api/v1/document-tasks/missing-task-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_document_task_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/document-tasks/some-task-id")
    assert resp.status_code == 401
