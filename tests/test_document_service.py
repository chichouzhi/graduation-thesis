from __future__ import annotations

from typing import Any

import pytest

from app import create_app
from app.document.service.document_service import DocumentService
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def test_create_document_task_enqueues_with_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def capture_enqueue(payload: dict | None = None, **_kwargs: Any) -> dict[str, str]:
        assert isinstance(payload, dict)
        seen.update(payload)
        return {"job_id": "doc-job-1"}

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-u1", role=UserRole.student, display_name="u1")
        term = Term(name="2026")
        db.session.add_all([user, term])
        db.session.commit()

        monkeypatch.setattr("app.document.service.document_service.queue_mod.enqueue_pdf_parse", capture_enqueue)

        body = DocumentService().create_document_task(
            user_id=user.id,
            term_id=term.id,
            storage_path="/tmp/a.pdf",
            filename="a.pdf",
        )

        assert seen["user_id"] == user.id
        assert seen["term_id"] == term.id
        assert seen["storage_path"] == "/tmp/a.pdf"
        assert seen["stage"] == "pdf_extract"
        assert body["status"] == "pending"
        assert body["filename"] == "a.pdf"


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"user_id": " ", "term_id": "term-1", "storage_path": "/tmp/a.pdf", "filename": "a.pdf"}, "user_id"),
        ({"user_id": "u1", "term_id": " ", "storage_path": "/tmp/a.pdf", "filename": "a.pdf"}, "term_id"),
        ({"user_id": "u1", "term_id": "t1", "storage_path": " ", "filename": "a.pdf"}, "storage_path"),
        ({"user_id": "u1", "term_id": "t1", "storage_path": "/tmp/a.pdf", "filename": " "}, "filename"),
    ],
)
def test_create_document_task_rejects_missing_multipart_semantics(
    kwargs: dict[str, str],
    match: str,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-u2", role=UserRole.student, display_name="u2")
        term = Term(name="2027")
        db.session.add_all([user, term])
        db.session.commit()
        call = dict(kwargs)
        if call["user_id"].strip():
            call["user_id"] = user.id
        if call["term_id"].strip():
            call["term_id"] = term.id
        with pytest.raises(ValueError, match=match):
            DocumentService().create_document_task(**call)
