from __future__ import annotations

import pytest
from app import create_app
from app.document.model import DocumentArtifact, DocumentArtifactType, DocumentTask, DocumentTaskStatus
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from sqlalchemy.exc import IntegrityError

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


def test_run_keeps_non_terminal_document_stage_running(
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
    assert writes[0] == ("dt-1", {"status": "running"})
    assert writes[1] == ("dt-1", {"status": "running", "last_completed_chunk": 1})
    assert len(writes) == 2


def test_run_preserves_finalize_terminal_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[str, dict[str, object]]] = []

    def fake_writeback(document_task_id: str, patch: dict[str, object]) -> None:
        writes.append((document_task_id, patch))

    monkeypatch.setattr("app.task.document_jobs._default_writeback", fake_writeback)
    monkeypatch.setattr(
        "app.task.document_jobs.handle_document_job",
        lambda payload, writeback: (
            writeback(payload["document_task_id"], {"status": "done", "current_stage": "finalize"}) or {"status": "done", "current_stage": "finalize"}
        ),
    )

    payload = dict(_base_payload())
    payload["stage"] = "finalize"
    payload["chunk_index"] = None

    run(payload)
    assert writes[0] == ("dt-1", {"status": "running"})
    assert writes[1] == ("dt-1", {"status": "done", "current_stage": "finalize"})
    assert len(writes) == 2


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
    assert writes[0] == ("dt-1", {"status": "running"})
    assert writes[1][0] == "dt-1"
    assert writes[1][1]["status"] == "failed"
    assert writes[1][1]["error_code"] == "DOMAIN_ERROR"
    assert len(writes) == 2


def test_run_skips_failed_document_task(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-skip-failed", role=UserRole.student, display_name="Skip Failed")
        term = Term(name="Task4 Jobs Skip Failed")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="skip.pdf",
            storage_path="/tmp/skip.pdf",
            status=DocumentTaskStatus.failed,
            current_stage="summarize_chunks",
            error_code="QUEUE_UNAVAILABLE",
            error_message="broker down",
        )
        db.session.add(task)
        db.session.commit()

        called = {"count": 0}

        def should_not_run(*_args: object, **_kwargs: object) -> dict[str, object]:
            called["count"] += 1
            return {"status": "running"}

        monkeypatch.setattr("app.task.document_jobs.handle_document_job", should_not_run)

        run(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/skip.pdf",
                "term_id": term.id,
                "stage": "summarize_chunk",
                "chunk_index": 0,
                "max_chunks": 1,
            }
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert called["count"] == 0
        assert task.status == DocumentTaskStatus.failed
        assert task.error_code == "QUEUE_UNAVAILABLE"


def test_document_job_writeback_keeps_terminal_status_immutable() -> None:
    from app.task.document_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-terminal", role=UserRole.student, display_name="Terminal")
        term = Term(name="Task4 Jobs Terminal")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="terminal.pdf",
            storage_path="/tmp/terminal.pdf",
            status=DocumentTaskStatus.failed,
            current_stage="summarize_chunks",
            progress_json={"completed_chunks": 0, "total_chunks": 2},
            error_code="QUEUE_UNAVAILABLE",
            error_message="broker down",
        )
        db.session.add(task)
        db.session.commit()

        _default_writeback(
            task.id,
            {
                "status": "running",
                "current_stage": "aggregate",
                "progress_patch": {"completed_chunks": 2, "total_chunks": 2},
                "last_completed_chunk": 1,
            },
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert task.status == DocumentTaskStatus.failed
        assert task.current_stage == "summarize_chunks"
        assert task.progress_json == {"completed_chunks": 0, "total_chunks": 2}
        assert task.last_completed_chunk is None


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
        assert task.status == DocumentTaskStatus.running
        assert task.last_completed_chunk == 1
        assert len(artifacts) == 2
        assert [artifact.chunk_index for artifact in artifacts] == [0, 1]
        assert [artifact.content_text for artifact in artifacts] == ["summary first", "summary second"]


def test_document_job_writeback_updates_existing_artifact_in_place() -> None:
    from app.task.document_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-dup", role=UserRole.student, display_name="Dup")
        term = Term(name="Task4 Jobs Duplicate")
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
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                    chunk_index=0,
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
                        "artifact_type": "chunk_summary",
                        "stage": "summarize_chunk",
                        "chunk_index": 0,
                        "content_text": "newest",
                        "payload": {"chunk_text": "page"},
                    }
                ]
            },
        )

        artifacts = (
            db.session.query(DocumentArtifact)
            .filter_by(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.chunk_summary,
                stage="summarize_chunk",
                chunk_index=0,
            )
            .order_by(DocumentArtifact.created_at.asc(), DocumentArtifact.id.asc())
            .all()
        )
        assert len(artifacts) == 1
        assert artifacts[0].content_text == "newest"


def test_document_job_writeback_retries_once_after_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.task.document_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-retry", role=UserRole.student, display_name="Retry")
        term = Term(name="Task4 Jobs Retry")
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
                        "artifact_type": "chunk_summary",
                        "stage": "summarize_chunk",
                        "chunk_index": 0,
                        "content_text": "newest",
                        "payload": {"chunk_text": "page"},
                    }
                ]
            },
        )

        artifacts = (
            db.session.query(DocumentArtifact)
            .filter_by(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.chunk_summary,
                stage="summarize_chunk",
                chunk_index=0,
            )
            .all()
        )
        assert seen["calls"] == 2
        assert len(artifacts) == 1
        assert artifacts[0].content_text == "newest"


def test_document_job_writeback_updates_stage_progress_and_final_result() -> None:
    from app.task.document_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-final", role=UserRole.student, display_name="Final")
        term = Term(name="Task4 Jobs Final")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="final.pdf",
            storage_path="/tmp/final.pdf",
        )
        db.session.add(task)
        db.session.commit()

        _default_writeback(
            task.id,
            {
                "status": "done",
                "current_stage": "finalize",
                "progress_patch": {"completed_chunks": 2, "total_chunks": 2},
                "result_patch": {
                    "summary": "overall summary",
                    "bullet_points": ["point a", "point b"],
                    "raw_model": "overall summary\n- point a\n- point b",
                },
                "artifacts": [
                    {
                        "artifact_type": "final_result",
                        "stage": "finalize",
                        "chunk_index": None,
                        "content_text": "overall summary\n- point a\n- point b",
                        "payload": {
                            "summary": "overall summary",
                            "bullet_points": ["point a", "point b"],
                            "raw_model": "overall summary\n- point a\n- point b",
                        },
                    }
                ],
            },
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert task.status == DocumentTaskStatus.done
        assert task.current_stage == "finalize"
        assert task.progress_json == {"completed_chunks": 2, "total_chunks": 2}
        assert task.result_json == {
            "summary": "overall summary",
            "bullet_points": ["point a", "point b"],
            "raw_model": "overall summary\n- point a\n- point b",
        }
        artifacts = (
            db.session.query(DocumentArtifact)
            .filter_by(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.final_result,
                stage="finalize",
                chunk_index=None,
            )
            .all()
        )
        assert len(artifacts) == 1
        assert artifacts[0].payload_json == {
            "summary": "overall summary",
            "bullet_points": ["point a", "point b"],
            "raw_model": "overall summary\n- point a\n- point b",
        }


def test_document_job_writeback_counts_completed_chunks_from_saved_artifacts() -> None:
    from app.task.document_jobs import _default_writeback

    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-progress", role=UserRole.student, display_name="Progress")
        term = Term(name="Task4 Jobs Progress")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="progress.pdf",
            storage_path="/tmp/progress.pdf",
        )
        db.session.add(task)
        db.session.commit()

        _default_writeback(
            task.id,
            {
                "status": "running",
                "current_stage": "summarize_chunks",
                "progress_patch": {"completed_chunks": 3, "total_chunks": 3},
                "artifacts": [
                    {
                        "artifact_type": "chunk_summary",
                        "stage": "summarize_chunk",
                        "chunk_index": 2,
                        "content_text": "summary two",
                        "payload": {"chunk_text": "page two", "max_chunks": 3},
                    }
                ],
            },
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert task.progress_json == {"completed_chunks": 1, "total_chunks": 3}


def test_run_enqueues_aggregate_after_last_chunk_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueued: list[dict[str, object]] = []
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-chain", role=UserRole.student, display_name="Chain")
        term = Term(name="Task4 Jobs Chain")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="chain.pdf",
            storage_path="/tmp/chain.pdf",
            status=DocumentTaskStatus.running,
            current_stage="summarize_chunks",
            progress_json={"completed_chunks": 1, "total_chunks": 2},
        )
        db.session.add(task)
        db.session.commit()
        db.session.add_all(
            [
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.pdf_pages_text,
                    stage="pdf_extract",
                    content_text="page zero\n\npage one",
                    payload_json={
                        "pages": [
                            {"page_index": 0, "text": "page zero"},
                            {"page_index": 1, "text": "page one"},
                        ]
                    },
                ),
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                    chunk_index=0,
                    content_text="summary zero",
                    payload_json={"chunk_text": "page zero", "max_chunks": 2},
                ),
            ]
        )
        db.session.commit()

        monkeypatch.setattr(
            "app.adapter.llm.complete",
            lambda _messages, **_kwargs: {"content": "summary one"},
        )
        monkeypatch.setattr(
            "app.task.document_jobs.queue_mod.enqueue_document_jobs",
            lambda payload=None, **_kwargs: enqueued.append(dict(payload or {})) or {"job_id": "doc-job"},
        )

        run(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/chain.pdf",
                "term_id": term.id,
                "stage": "summarize_chunk",
                "chunk_index": 1,
                "max_chunks": 2,
            }
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert task.status == DocumentTaskStatus.running
        assert task.current_stage == "aggregate"
        assert enqueued == [
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/chain.pdf",
                "term_id": term.id,
                "stage": "aggregate",
                "chunk_index": None,
                "max_chunks": 2,
            }
        ]


def test_run_enqueues_finalize_after_aggregate_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueued: list[dict[str, object]] = []
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-finalize-chain", role=UserRole.student, display_name="Final Chain")
        term = Term(name="Task4 Jobs Finalize Chain")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="aggregate.pdf",
            storage_path="/tmp/aggregate.pdf",
            status=DocumentTaskStatus.running,
            current_stage="aggregate",
            progress_json={"completed_chunks": 2, "total_chunks": 2},
        )
        db.session.add(task)
        db.session.commit()
        db.session.add_all(
            [
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                    chunk_index=0,
                    content_text="summary zero",
                    payload_json={"chunk_text": "page zero", "max_chunks": 2},
                ),
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                    chunk_index=1,
                    content_text="summary one",
                    payload_json={"chunk_text": "page one", "max_chunks": 2},
                ),
            ]
        )
        db.session.commit()

        monkeypatch.setattr(
            "app.adapter.llm.complete",
            lambda _messages, **_kwargs: {"content": "overall summary\n- point a"},
        )
        monkeypatch.setattr(
            "app.task.document_jobs.queue_mod.enqueue_document_jobs",
            lambda payload=None, **_kwargs: enqueued.append(dict(payload or {})) or {"job_id": "doc-job"},
        )

        run(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/aggregate.pdf",
                "term_id": term.id,
                "stage": "aggregate",
                "chunk_index": None,
                "max_chunks": 2,
            }
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert task.status == DocumentTaskStatus.running
        assert task.current_stage == "finalize"
        assert enqueued == [
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/aggregate.pdf",
                "term_id": term.id,
                "stage": "finalize",
                "chunk_index": None,
                "max_chunks": 2,
            }
        ]


def test_run_marks_failed_when_followup_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-followup-fail", role=UserRole.student, display_name="Followup Fail")
        term = Term(name="Task4 Jobs Followup Fail")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="followup.pdf",
            storage_path="/tmp/followup.pdf",
            status=DocumentTaskStatus.running,
            current_stage="summarize_chunks",
            progress_json={"completed_chunks": 0, "total_chunks": 1},
        )
        db.session.add(task)
        db.session.commit()
        db.session.add(
            DocumentArtifact(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.pdf_pages_text,
                stage="pdf_extract",
                content_text="page zero",
                payload_json={"pages": [{"page_index": 0, "text": "page zero"}]},
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            "app.adapter.llm.complete",
            lambda _messages, **_kwargs: {"content": "summary zero"},
        )

        def boom_enqueue(*_args: object, **_kwargs: object) -> dict[str, str]:
            raise RuntimeError("broker down")

        monkeypatch.setattr("app.task.document_jobs.queue_mod.enqueue_document_jobs", boom_enqueue)

        with pytest.raises(RuntimeError, match="broker down"):
            run(
                {
                    "document_task_id": task.id,
                    "user_id": user.id,
                    "storage_path": "/tmp/followup.pdf",
                    "term_id": term.id,
                    "stage": "summarize_chunk",
                    "chunk_index": 0,
                    "max_chunks": 1,
                }
            )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert task.status == DocumentTaskStatus.failed
        assert task.error_code == "QUEUE_UNAVAILABLE"
        assert task.error_message is not None and "broker down" in task.error_message


def test_run_skips_stale_summarize_chunk_after_task_advanced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="doc-job-stale-summarize", role=UserRole.student, display_name="Stale Summarize")
        term = Term(name="Task4 Jobs Stale Summarize")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="stale.pdf",
            storage_path="/tmp/stale.pdf",
            status=DocumentTaskStatus.running,
            current_stage="aggregate",
            progress_json={"completed_chunks": 2, "total_chunks": 2},
        )
        db.session.add(task)
        db.session.commit()
        db.session.add_all(
            [
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.pdf_pages_text,
                    stage="pdf_extract",
                    content_text="page zero\n\npage one",
                    payload_json={
                        "pages": [
                            {"page_index": 0, "text": "page zero"},
                            {"page_index": 1, "text": "page one"},
                        ]
                    },
                ),
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                    chunk_index=0,
                    content_text="summary zero",
                    payload_json={"chunk_text": "page zero", "max_chunks": 2},
                ),
                DocumentArtifact(
                    document_task_id=task.id,
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                    chunk_index=1,
                    content_text="summary one",
                    payload_json={"chunk_text": "page one", "max_chunks": 2},
                ),
            ]
        )
        db.session.commit()

        called = {"count": 0}

        def should_not_run(*_args: object, **_kwargs: object) -> dict[str, object]:
            called["count"] += 1
            return {"status": "running"}

        monkeypatch.setattr("app.task.document_jobs.handle_document_job", should_not_run)

        run(
            {
                "document_task_id": task.id,
                "user_id": user.id,
                "storage_path": "/tmp/stale.pdf",
                "term_id": term.id,
                "stage": "summarize_chunk",
                "chunk_index": 1,
                "max_chunks": 2,
            }
        )

        task = db.session.get(DocumentTask, task.id)
        assert task is not None
        assert called["count"] == 0
        assert task.status == DocumentTaskStatus.running
        assert task.current_stage == "aggregate"
        assert task.progress_json == {"completed_chunks": 2, "total_chunks": 2}
