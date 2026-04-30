from __future__ import annotations

import pytest
from app import create_app
from app.document.model import DocumentArtifact, DocumentArtifactType, DocumentTask
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from sqlalchemy.exc import IntegrityError

from app.task.pdf_parse_jobs import handle_pdf_parse_job, run
from app.use_cases.document_pdf_parse import PdfJobPayload, PdfParseSuccessPlan, parse_pdf_and_plan_document_jobs


def _valid_pdf_payload() -> dict[str, str]:
    return {
        "document_task_id": "dt-1",
        "user_id": "u-1",
        "storage_path": "/tmp/demo.pdf",
        "term_id": "term-1",
        "stage": "pdf_extract",
        "request_id": "req-1",
    }


def test_pdf_job_payload_requires_non_empty_fields() -> None:
    payload = _valid_pdf_payload()
    payload["document_task_id"] = ""
    with pytest.raises(ValueError, match="document_task_id"):
        PdfJobPayload.from_mapping(payload)


def test_pdf_job_payload_stage_must_be_pdf_extract() -> None:
    payload = _valid_pdf_payload()
    payload["stage"] = "extract"
    with pytest.raises(ValueError, match="pdf_extract"):
        PdfJobPayload.from_mapping(payload)


def test_parse_pdf_and_plan_document_jobs_hooks_adapter_and_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called_paths: list[str] = []

    def fake_parse_document(path: str) -> dict[str, object]:
        called_paths.append(path)
        return {
            "page_count": 2,
            "pages": [{"page_index": 0, "text": "a"}, {"page_index": 1, "text": "b"}],
            "full_text": "a\n\nb",
        }

    monkeypatch.setattr("app.use_cases.document_pdf_parse.parse_document", fake_parse_document)
    payload = PdfJobPayload.from_mapping(_valid_pdf_payload())
    plan = parse_pdf_and_plan_document_jobs(payload)
    jobs = plan.document_job_payloads

    assert called_paths == ["/tmp/demo.pdf"]
    assert len(jobs) == 5  # extract + 2 summarize_chunk + aggregate + finalize
    assert jobs[0]["stage"] == "extract"
    assert jobs[1]["stage"] == "summarize_chunk"
    assert jobs[-1]["stage"] == "finalize"
    assert all(job["request_id"] == "req-1" for job in jobs)
    assert plan.parsed_meta_for_result_json["pdf_parse_outline"]["max_chunks"] == 2
    assert plan.parsed_meta_for_result_json["pdf_parse_outline"]["page_text_char_counts"] == [1, 1]
    assert plan.extracted_text_artifact_payload["artifact_type"] == "pdf_pages_text"
    assert plan.extracted_text_artifact_payload["payload"]["pages"][1]["text"] == "b"
    assert plan.extracted_text_artifact_payload["content_text"] == "a\n\nb"


def test_handle_pdf_parse_job_enqueues_document_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueued: list[dict[str, object]] = []
    writebacks: list[tuple[str, dict[str, object]]] = []
    events: list[str] = []

    def fake_planner(_: PdfJobPayload) -> PdfParseSuccessPlan:
        payloads = (
            {
                "document_task_id": "dt-1",
                "user_id": "u-1",
                "storage_path": "/tmp/demo.pdf",
                "term_id": "term-1",
                "stage": "extract",
                "chunk_index": None,
                "max_chunks": 1,
            },
            {
                "document_task_id": "dt-1",
                "user_id": "u-1",
                "storage_path": "/tmp/demo.pdf",
                "term_id": "term-1",
                "stage": "finalize",
                "chunk_index": None,
                "max_chunks": 1,
            },
        )
        return PdfParseSuccessPlan(
            document_job_payloads=payloads,
            parsed_meta_for_result_json={"pdf_parse_outline": {"page_count": 1, "max_chunks": 1, "page_text_char_counts": [9]}},
            extracted_text_artifact_payload={
                "artifact_type": "pdf_pages_text",
                "stage": "pdf_extract",
                "chunk_index": None,
                "content_text": "page text",
                "payload": {"pages": [{"page_index": 0, "text": "page text"}]},
            },
        )

    def fake_enqueue(payload: dict[str, object] | None = None, **_: object) -> dict[str, str]:
        assert payload is not None
        events.append("enqueue")
        enqueued.append(payload)
        return {"job_id": "doc-job"}

    def capture_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        events.append("writeback_meta")
        writebacks.append((document_task_id, patch))

    monkeypatch.setattr("app.task.pdf_parse_jobs.parse_pdf_and_plan_document_jobs", fake_planner)
    monkeypatch.setattr("app.task.pdf_parse_jobs.queue_mod.enqueue_document_jobs", fake_enqueue)
    monkeypatch.setattr("app.task.pdf_parse_jobs._default_writeback", capture_writeback)

    jobs = handle_pdf_parse_job(_valid_pdf_payload())
    assert len(jobs) == 2
    assert enqueued == list(jobs)
    assert writebacks == [
        (
            "dt-1",
            {
                "result_patch": {"pdf_parse_outline": {"page_count": 1, "max_chunks": 1, "page_text_char_counts": [9]}},
                "artifacts": [
                    {
                        "artifact_type": "pdf_pages_text",
                        "stage": "pdf_extract",
                        "chunk_index": None,
                        "content_text": "page text",
                        "payload": {"pages": [{"page_index": 0, "text": "page text"}]},
                    }
                ],
            },
        )
    ]
    assert events == ["writeback_meta", "enqueue", "enqueue"]


def test_pdf_parse_writeback_persists_extracted_text_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pdf-task-user", role=UserRole.student, display_name="PDF")
        term = Term(name="Task4 PDF")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="paper.pdf",
            storage_path="/tmp/paper.pdf",
        )
        db.session.add(task)
        db.session.commit()

        def fake_enqueue(payload: dict[str, object] | None = None, **_: object) -> dict[str, str]:
            assert payload is not None
            return {"job_id": "doc-job"}

        def fake_planner(_: PdfJobPayload) -> PdfParseSuccessPlan:
            return PdfParseSuccessPlan(
                document_job_payloads=(
                    {
                        "document_task_id": task.id,
                        "user_id": user.id,
                        "storage_path": "/tmp/paper.pdf",
                        "term_id": term.id,
                        "stage": "extract",
                        "chunk_index": None,
                        "max_chunks": 2,
                    },
                ),
                parsed_meta_for_result_json={
                    "pdf_parse_outline": {"page_count": 2, "max_chunks": 2, "page_text_char_counts": [5, 4]}
                },
                extracted_text_artifact_payload={
                    "artifact_type": "pdf_pages_text",
                    "stage": "pdf_extract",
                    "chunk_index": None,
                    "content_text": "alpha\n\nbeta",
                    "payload": {
                        "pages": [
                            {"page_index": 0, "text": "alpha"},
                            {"page_index": 1, "text": "beta"},
                        ]
                    },
                },
            )

        monkeypatch.setattr("app.task.pdf_parse_jobs.parse_pdf_and_plan_document_jobs", fake_planner)
        monkeypatch.setattr("app.task.pdf_parse_jobs.queue_mod.enqueue_document_jobs", fake_enqueue)

        handle_pdf_parse_job(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/paper.pdf",
                "term_id": term.id,
                "stage": "pdf_extract",
            }
        )

        artifact = db.session.query(DocumentArtifact).filter_by(document_task_id=task.id).one()
        assert artifact.artifact_type == DocumentArtifactType.pdf_pages_text
        assert artifact.stage == "pdf_extract"
        assert artifact.chunk_index is None
        assert artifact.content_text == "alpha\n\nbeta"
        assert artifact.payload_json == {
            "pages": [
                {"page_index": 0, "text": "alpha"},
                {"page_index": 1, "text": "beta"},
            ]
        }


def test_pdf_parse_writeback_updates_existing_artifact_in_place() -> None:
    from app.task.pdf_parse_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pdf-task-dup", role=UserRole.student, display_name="PDF Dup")
        term = Term(name="Task4 PDF Duplicate")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="dup.pdf",
            storage_path="/tmp/dup.pdf",
        )
        db.session.add(task)
        db.session.commit()
        db.session.add_all(
            [
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.pdf_pages_text,
                    stage="pdf_extract",
                    chunk_index=None,
                    content_text="old-1",
                ),
            ]
        )
        db.session.commit()

        _default_writeback(
            task.id,
            {
                "artifacts": [
                    {
                        "artifact_type": "pdf_pages_text",
                        "stage": "pdf_extract",
                        "chunk_index": None,
                        "content_text": "newest",
                        "payload": {"pages": [{"page_index": 0, "text": "newest"}]},
                    }
                ]
            },
        )

        artifacts = (
            db.session.query(DocumentArtifact)
            .filter_by(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.pdf_pages_text,
                stage="pdf_extract",
                chunk_index=None,
            )
            .order_by(DocumentArtifact.created_at.asc(), DocumentArtifact.id.asc())
            .all()
        )
        assert len(artifacts) == 1
        assert artifacts[0].content_text == "newest"


def test_pdf_parse_writeback_retries_once_after_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.task.pdf_parse_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pdf-task-retry", role=UserRole.student, display_name="PDF Retry")
        term = Term(name="Task4 PDF Retry")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="retry.pdf",
            storage_path="/tmp/retry.pdf",
        )
        db.session.add(task)
        db.session.commit()

        orig_commit = db.session.commit
        seen = {"calls": 0}

        def flaky_commit() -> None:
            seen["calls"] += 1
            if seen["calls"] == 1:
                raise IntegrityError("insert", {}, Exception("duplicate artifact"))
            orig_commit()

        monkeypatch.setattr(db.session, "commit", flaky_commit)

        _default_writeback(
            task.id,
            {
                "artifacts": [
                    {
                        "artifact_type": "pdf_pages_text",
                        "stage": "pdf_extract",
                        "chunk_index": None,
                        "content_text": "newest",
                        "payload": {"pages": [{"page_index": 0, "text": "newest"}]},
                    }
                ]
            },
        )

        artifacts = (
            db.session.query(DocumentArtifact)
            .filter_by(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.pdf_pages_text,
                stage="pdf_extract",
                chunk_index=None,
            )
            .all()
        )
        assert seen["calls"] == 2
        assert len(artifacts) == 1
        assert artifacts[0].content_text == "newest"


def test_run_writes_failed_status_when_pdf_parse_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, dict[str, object]]] = []

    def fake_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        writes.append((document_task_id, patch))

    def boom(_payload: dict[str, object]) -> tuple[dict[str, object], ...]:
        raise RuntimeError("pdf parse timeout")

    monkeypatch.setattr("app.task.pdf_parse_jobs._default_writeback", fake_writeback)
    monkeypatch.setattr("app.task.pdf_parse_jobs.handle_pdf_parse_job", boom)

    with pytest.raises(RuntimeError, match="pdf parse timeout"):
        run(_valid_pdf_payload())

    assert writes[0] == ("dt-1", {"status": "running"})
    assert writes[1][0] == "dt-1"
    assert writes[1][1]["status"] == "failed"
    assert writes[1][1]["error_code"] == "DOMAIN_ERROR"
    assert "pdf parse timeout" in str(writes[1][1]["error_message"])
