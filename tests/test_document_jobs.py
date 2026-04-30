from __future__ import annotations

import pytest
from app import create_app
from app.document.model import DocumentArtifact, DocumentArtifactType, DocumentTask, DocumentTaskStatus
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term

from app.task.document_jobs import DocumentJobPayload, handle_document_job, run


def _base_payload() -> dict[str, object]:
    return {
        "document_task_id": "dt-1",
        "user_id": "u-1",
        "storage_path": "/tmp/doc.pdf",
        "term_id": "term-1",
        "stage": "summarize_chunk",
        "chunk_index": 0,
        "max_chunks": 3,
        "request_id": "req-1",
    }


def test_document_job_payload_requires_fields() -> None:
    payload = _base_payload()
    payload["term_id"] = " "
    with pytest.raises(ValueError, match="term_id"):
        DocumentJobPayload.from_mapping(payload)


def test_document_job_payload_stage_enum_validates() -> None:
    payload = _base_payload()
    payload["stage"] = "unknown"
    with pytest.raises(ValueError):
        DocumentJobPayload.from_mapping(payload)


def test_handle_document_job_dispatches_stage_to_use_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, object]] = []

    def fake_run_stage(**kwargs: object) -> dict[str, object]:
        seen.append(dict(kwargs))
        return {"status": "running", "last_completed_chunk": 0}

    writebacks: list[tuple[str, dict[str, object]]] = []

    def capture_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        writebacks.append((document_task_id, patch))

    monkeypatch.setattr("app.task.document_jobs.run_document_job_stage", fake_run_stage)
    patch = handle_document_job(_base_payload(), writeback=capture_writeback)

    assert patch == {"status": "running", "last_completed_chunk": 0}
    assert seen and seen[0]["stage"].value == "summarize_chunk"
    assert seen[0]["chunk_index"] == 0
    assert writebacks == [("dt-1", {"status": "running", "last_completed_chunk": 0})]


def test_run_document_job_stage_summarize_calls_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.use_cases.document_pipeline import run_document_job_stage

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-jobs-llm", role=UserRole.student, display_name="LLM")
        term = Term(name="Task4 Jobs LLM")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="doc.pdf",
            storage_path="/tmp/doc.pdf",
        )
        db.session.add(task)
        db.session.commit()
        db.session.add(
            DocumentArtifact(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.pdf_pages_text,
                stage="pdf_extract",
                content_text="first page\n\nsecond page",
                payload_json={
                    "pages": [
                        {"page_index": 0, "text": "first page"},
                        {"page_index": 1, "text": "second page"},
                    ]
                },
            )
        )
        db.session.commit()

        captured_messages: list[list[dict[str, str]]] = []

        def fake_complete(messages: list[dict[str, str]], **_: object) -> dict[str, str]:
            captured_messages.append(messages)
            return {"content": "summary text"}

        monkeypatch.setattr("app.adapter.llm.complete", fake_complete)
        patch = run_document_job_stage(
            stage="summarize_chunk",
            chunk_index=1,
            document_task_id=task.id,
            storage_path="/tmp/doc.pdf",
            term_id=term.id,
            user_id=user.id,
            max_chunks=4,
        )
        assert captured_messages
        assert "second page" in captured_messages[0][0]["content"]
        assert patch["last_completed_chunk"] == 1
        assert patch["artifacts"][0]["content_text"] == "summary text"


def test_run_writes_default_statuses_and_last_completed_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, dict[str, object]]] = []

    def fake_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        writes.append((document_task_id, patch))

    monkeypatch.setattr("app.task.document_jobs._default_writeback", fake_writeback)
    monkeypatch.setattr(
        "app.task.document_jobs.handle_document_job",
        lambda payload, writeback: (
            writeback(payload["document_task_id"], {"status": "running", "last_completed_chunk": 1}) or {"status": "running", "last_completed_chunk": 1}
        ),
    )
    run(_base_payload())
    assert writes[0] == ("dt-1", {"status": "pending"})
    assert writes[1] == ("dt-1", {"status": "running"})
    assert writes[2] == ("dt-1", {"status": "running", "last_completed_chunk": 1})
    assert writes[3] == ("dt-1", {"status": "done"})


def test_run_writes_failed_when_handler_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    writes: list[tuple[str, dict[str, object]]] = []

    def fake_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        writes.append((document_task_id, patch))

    monkeypatch.setattr("app.task.document_jobs._default_writeback", fake_writeback)

    def _boom(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("llm timeout")

    monkeypatch.setattr("app.task.document_jobs.handle_document_job", _boom)
    with pytest.raises(RuntimeError, match="llm timeout"):
        run(_base_payload())
    assert writes[0] == ("dt-1", {"status": "pending"})
    assert writes[1] == ("dt-1", {"status": "running"})
    assert writes[2][0] == "dt-1"
    assert writes[2][1]["status"] == "failed"
    assert writes[2][1]["error_code"] == "DOMAIN_ERROR"


def test_document_job_writeback_persists_chunk_summaries_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-user", role=UserRole.student, display_name="Doc")
        term = Term(name="Task4 Jobs")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="job.pdf",
            storage_path="/tmp/job.pdf",
            status=DocumentTaskStatus.pending,
        )
        db.session.add(task)
        db.session.commit()
        db.session.add(
            DocumentArtifact(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.pdf_pages_text,
                stage="pdf_extract",
                content_text="first page\n\nsecond page",
                payload_json={
                    "pages": [
                        {"page_index": 0, "text": "first page"},
                        {"page_index": 1, "text": "second page"},
                    ]
                },
            )
        )
        db.session.commit()

        def fake_complete(messages: list[dict[str, str]], **_: object) -> dict[str, str]:
            text = messages[0]["content"]
            if "first page" in text:
                return {"content": "summary first"}
            return {"content": "summary second"}

        monkeypatch.setattr("app.adapter.llm.complete", fake_complete)

        run(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/job.pdf",
                "term_id": term.id,
                "stage": "summarize_chunk",
                "chunk_index": 0,
                "max_chunks": 2,
            }
        )
        run(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/job.pdf",
                "term_id": term.id,
                "stage": "summarize_chunk",
                "chunk_index": 1,
                "max_chunks": 2,
            }
        )

        task = db.session.get(DocumentTask, task.id)
        artifacts = (
            db.session.query(DocumentArtifact)
            .filter_by(document_task_id=task.id, artifact_type=DocumentArtifactType.chunk_summary)
            .order_by(DocumentArtifact.chunk_index.asc())
            .all()
        )
        assert task is not None
        assert task.last_completed_chunk == 1
        assert len(artifacts) == 2
        assert [artifact.chunk_index for artifact in artifacts] == [0, 1]
        assert [artifact.content_text for artifact in artifacts] == ["summary first", "summary second"]
