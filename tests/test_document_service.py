from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app import create_app
from app.adapter import storage as storage_mod
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.document.model import DocumentTask, DocumentTaskStatus
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
        ({"user_id": None, "term_id": "t1", "storage_path": "/tmp/a.pdf", "filename": "a.pdf"}, "user_id"),
        ({"user_id": "u1", "term_id": None, "storage_path": "/tmp/a.pdf", "filename": "a.pdf"}, "term_id"),
        ({"user_id": "u1", "term_id": "t1", "storage_path": "/tmp/a.pdf", "filename": "a.txt"}, "PDF"),
    ],
)
def test_create_document_task_rejects_missing_multipart_semantics(
    kwargs: dict[str, Any],
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
        raw_uid = call.get("user_id")
        if raw_uid is not None and str(raw_uid).strip():
            call["user_id"] = user.id
        raw_tid = call.get("term_id")
        if raw_tid is not None and str(raw_tid).strip():
            call["term_id"] = term.id
        with pytest.raises(ValueError, match=match):
            DocumentService().create_document_task(**call)


def test_create_document_task_rejects_empty_upload_bytes() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-u3", role=UserRole.student, display_name="u3")
        term = Term(name="2028")
        db.session.add_all([user, term])
        db.session.commit()
        with pytest.raises(ValueError, match="file must not be empty"):
            DocumentService().create_document_task(
                user_id=user.id,
                term_id=term.id,
                storage_path="",
                filename="a.pdf",
                file_bytes=b"",
            )


def test_create_document_task_put_bytes_persists_storage_path_row(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "document_store"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DOCUMENT_STORAGE_DIR", str(root))

    def capture_enqueue(payload: dict | None = None, **_kwargs: Any) -> dict[str, str]:
        return {"job_id": "doc-job-store-1"}

    pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-u4", role=UserRole.student, display_name="u4")
        term = Term(name="2029")
        db.session.add_all([user, term])
        db.session.commit()

        monkeypatch.setattr(
            "app.document.service.document_service.queue_mod.enqueue_pdf_parse",
            capture_enqueue,
        )

        DocumentService().create_document_task(
            user_id=user.id,
            term_id=term.id,
            storage_path="",
            filename="paper.pdf",
            file_bytes=pdf_bytes,
        )

        row = db.session.query(DocumentTask).one()
        assert row.storage_path.startswith(str(root.resolve()))
        assert Path(row.storage_path).is_file()
        assert storage_mod.get_bytes(row.storage_path) == pdf_bytes


def test_create_document_task_commits_before_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        "app.document.service.document_service.get_policy_gateway",
        lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
    )
    orig_commit = db.session.commit

    def wrapped_commit() -> None:
        events.append("commit")
        orig_commit()

    def capture_enqueue(payload: dict | None = None, **_kwargs: Any) -> dict[str, str]:
        assert isinstance(payload, dict)
        assert db.session.get(DocumentTask, payload["document_task_id"]) is not None
        events.append("enqueue")
        return {"job_id": "doc-order-1"}

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-order", role=UserRole.student, display_name="ord")
        term = Term(name="2031")
        db.session.add_all([user, term])
        db.session.commit()

        monkeypatch.setattr(db.session, "commit", wrapped_commit)
        monkeypatch.setattr(
            "app.document.service.document_service.queue_mod.enqueue_pdf_parse",
            capture_enqueue,
        )

        DocumentService().create_document_task(
            user_id=user.id,
            term_id=term.id,
            storage_path="/tmp/commit-before-enq.pdf",
            filename="commit-before-enq.pdf",
        )

    assert events.index("commit") < events.index("enqueue")


def test_create_document_task_policy_deny_skips_persist_and_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny(**_kwargs: Any) -> None:
        raise PolicyDenied("policy denied", code=ErrorCode.POLICY_QUEUE_DEPTH)

    monkeypatch.setattr(
        "app.document.service.document_service.get_policy_gateway",
        lambda: type("P", (), {"assert_can_enqueue": staticmethod(deny)}),
    )

    def enqueue_must_not_run(*_a: Any, **_k: Any) -> dict[str, str]:
        raise AssertionError("enqueue_pdf_parse must not be called when policy denies")

    monkeypatch.setattr(
        "app.document.service.document_service.queue_mod.enqueue_pdf_parse",
        enqueue_must_not_run,
    )

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-deny", role=UserRole.student, display_name="deny")
        term = Term(name="2032")
        db.session.add_all([user, term])
        db.session.commit()

        with pytest.raises(PolicyDenied):
            DocumentService().create_document_task(
                user_id=user.id,
                term_id=term.id,
                storage_path="/tmp/denied.pdf",
                filename="denied.pdf",
            )
        assert db.session.query(DocumentTask).count() == 0


def test_create_document_task_marks_failed_when_enqueue_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.document.service.document_service.get_policy_gateway",
        lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
    )

    def fail_enqueue(_payload: dict | None = None, **_kwargs: Any) -> dict[str, str]:
        raise RuntimeError("broker down")

    monkeypatch.setattr(
        "app.document.service.document_service.queue_mod.enqueue_pdf_parse",
        fail_enqueue,
    )

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-svc-fail", role=UserRole.student, display_name="fail")
        term = Term(name="2033")
        db.session.add_all([user, term])
        db.session.commit()

        with pytest.raises(PolicyDenied) as exc_info:
            DocumentService().create_document_task(
                user_id=user.id,
                term_id=term.id,
                storage_path="/tmp/enq-fail.pdf",
                filename="enq-fail.pdf",
            )

        assert exc_info.value.code == ErrorCode.QUEUE_UNAVAILABLE
        row = db.session.query(DocumentTask).one()
        assert row.status == DocumentTaskStatus.failed
        assert row.error_code == ErrorCode.QUEUE_UNAVAILABLE.value
        assert row.error_message is not None and "broker down" in row.error_message
