"""AG-034 / AG-035：``document_pipeline`` 幂等键、计划与 chunk 并行度。"""
from __future__ import annotations

import pytest
from app import create_app
from app.document.model import DocumentArtifact, DocumentArtifactType, DocumentTask
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term

from app.use_cases.document_pipeline import (
    DocumentChunkingPlan,
    DocumentJobStage,
    PlannedDocumentJob,
    assert_valid_stage_and_chunk,
    build_document_job_payloads_for_plan,
    chunk_summarize_waves,
    expand_default_document_job_plan,
    format_document_job_idempotency_key,
    parse_document_job_idempotency_key,
    planned_job_count,
    run_document_job_stage,
    resolve_document_chunk_max_parallel,
    validate_chunk_parallel_limit,
)


def test_idempotency_key_round_trip() -> None:
    k = format_document_job_idempotency_key(
        document_task_id="dt-1",
        stage=DocumentJobStage.SUMMARIZE_CHUNK,
        chunk_index=3,
    )
    assert k == "dt-1\x1fsummarize_chunk\x1f3"
    tid, st, ci = parse_document_job_idempotency_key(k)
    assert tid == "dt-1"
    assert st == DocumentJobStage.SUMMARIZE_CHUNK
    assert ci == 3


def test_idempotency_key_control_plane_null_chunk() -> None:
    k = format_document_job_idempotency_key(
        document_task_id="dt-2",
        stage=DocumentJobStage.AGGREGATE,
        chunk_index=None,
    )
    tid, st, ci = parse_document_job_idempotency_key(k)
    assert ci is None
    assert st == DocumentJobStage.AGGREGATE


def test_summarize_chunk_requires_index() -> None:
    with pytest.raises(ValueError, match="summarize_chunk"):
        format_document_job_idempotency_key(
            document_task_id="x",
            stage=DocumentJobStage.SUMMARIZE_CHUNK,
            chunk_index=None,
        )


def test_control_stage_rejects_chunk_index() -> None:
    with pytest.raises(ValueError, match="null"):
        format_document_job_idempotency_key(
            document_task_id="x",
            stage=DocumentJobStage.EXTRACT,
            chunk_index=0,
        )


def test_build_document_job_payloads_for_plan_matches_default_plan() -> None:
    plan = DocumentChunkingPlan(max_chunks=2)
    payloads = build_document_job_payloads_for_plan(
        plan,
        document_task_id="d1",
        user_id="u1",
        storage_path="/x.pdf",
        term_id="t1",
        request_id="r1",
    )
    assert len(payloads) == 3
    assert payloads[0]["stage"] == "extract" and payloads[0]["chunk_index"] is None
    assert payloads[1] == {
        "document_task_id": "d1",
        "user_id": "u1",
        "storage_path": "/x.pdf",
        "term_id": "t1",
        "stage": "summarize_chunk",
        "chunk_index": 0,
        "max_chunks": 2,
        "request_id": "r1",
    }
    assert payloads[2]["stage"] == "summarize_chunk"
    assert payloads[2]["chunk_index"] == 1


def test_expand_default_plan_three_chunks() -> None:
    plan = DocumentChunkingPlan(max_chunks=3)
    jobs = expand_default_document_job_plan(plan)
    assert planned_job_count(plan) == len(jobs) == 6
    assert jobs[0] == PlannedDocumentJob(DocumentJobStage.EXTRACT, None)
    assert jobs[1:4] == (
        PlannedDocumentJob(DocumentJobStage.SUMMARIZE_CHUNK, 0),
        PlannedDocumentJob(DocumentJobStage.SUMMARIZE_CHUNK, 1),
        PlannedDocumentJob(DocumentJobStage.SUMMARIZE_CHUNK, 2),
    )
    assert jobs[4] == PlannedDocumentJob(DocumentJobStage.AGGREGATE, None)
    assert jobs[5] == PlannedDocumentJob(DocumentJobStage.FINALIZE, None)


def test_chunking_plan_rejects_non_positive() -> None:
    with pytest.raises(ValueError, match="max_chunks"):
        expand_default_document_job_plan(DocumentChunkingPlan(max_chunks=0))


def test_assert_valid_stage_and_chunk() -> None:
    assert_valid_stage_and_chunk(DocumentJobStage.FINALIZE, None)
    with pytest.raises(ValueError):
        assert_valid_stage_and_chunk("finalize", 1)


def test_validate_chunk_parallel_limit() -> None:
    assert validate_chunk_parallel_limit(3) == 3
    with pytest.raises(ValueError, match="parallel"):
        validate_chunk_parallel_limit(0)


def test_resolve_document_chunk_max_parallel_override() -> None:
    assert resolve_document_chunk_max_parallel(override=2) == 2


def test_chunk_summarize_waves_five_by_two() -> None:
    assert chunk_summarize_waves(5, max_parallel=2) == (
        (0, 1),
        (2, 3),
        (4,),
    )


def test_chunk_summarize_waves_single_wave_when_under_cap() -> None:
    assert chunk_summarize_waves(3, max_parallel=10) == ((0, 1, 2),)


def test_run_document_job_stage_summarize_uses_extracted_chunk_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pipeline-user", role=UserRole.student, display_name="Pipe")
        term = Term(name="Task4 Pipeline")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="pipeline.pdf",
            storage_path="/tmp/pipeline.pdf",
        )
        db.session.add(task)
        db.session.commit()
        db.session.add(
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
            )
        )
        db.session.commit()

        captured_messages: list[list[dict[str, str]]] = []

        def fake_complete(messages: list[dict[str, str]], **_: object) -> dict[str, str]:
            captured_messages.append(messages)
            return {"content": "summary for page one"}

        monkeypatch.setattr("app.adapter.llm.complete", fake_complete)
        patch = run_document_job_stage(
            stage="summarize_chunk",
            chunk_index=1,
            document_task_id=task.id,
            storage_path="/tmp/pipeline.pdf",
            term_id=term.id,
            user_id=user.id,
            max_chunks=2,
        )

        assert captured_messages
        assert "page one" in captured_messages[0][0]["content"]
        assert "chunk 1" in captured_messages[0][0]["content"]
        assert patch["artifacts"] == [
            {
                "artifact_type": "chunk_summary",
                "stage": "summarize_chunk",
                "chunk_index": 1,
                "content_text": "summary for page one",
                "payload": {"chunk_text": "page one", "max_chunks": 2},
            }
        ]


def test_run_document_job_stage_aggregate_combines_chunk_summaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pipeline-aggregate-user", role=UserRole.student, display_name="Pipe Agg")
        term = Term(name="Task4 Pipeline Aggregate")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="aggregate.pdf",
            storage_path="/tmp/aggregate.pdf",
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

        captured_messages: list[list[dict[str, str]]] = []

        def fake_complete(messages: list[dict[str, str]], **_: object) -> dict[str, str]:
            captured_messages.append(messages)
            return {"content": "overall summary\n- point a\n- point b"}

        monkeypatch.setattr("app.adapter.llm.complete", fake_complete)
        patch = run_document_job_stage(
            stage="aggregate",
            chunk_index=None,
            document_task_id=task.id,
            storage_path="/tmp/aggregate.pdf",
            term_id=term.id,
            user_id=user.id,
            max_chunks=2,
        )

        assert captured_messages
        assert "summary zero" in captured_messages[0][0]["content"]
        assert "summary one" in captured_messages[0][0]["content"]
        assert patch == {
            "status": "running",
            "current_stage": "aggregate",
            "progress_patch": {"completed_chunks": 2, "total_chunks": 2},
            "artifacts": [
                {
                    "artifact_type": "aggregate_summary",
                    "stage": "aggregate",
                    "chunk_index": None,
                    "content_text": "overall summary\n- point a\n- point b",
                    "payload": {
                        "chunk_summaries": ["summary zero", "summary one"],
                        "max_chunks": 2,
                    },
                }
            ],
        }


def test_run_document_job_stage_aggregate_requires_all_chunk_summaries() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pipeline-aggregate-gap-user", role=UserRole.student, display_name="Pipe Gap")
        term = Term(name="Task4 Pipeline Aggregate Gap")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="aggregate-gap.pdf",
            storage_path="/tmp/aggregate-gap.pdf",
        )
        db.session.add(task)
        db.session.commit()
        db.session.add(
            DocumentArtifact(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.chunk_summary,
                stage="summarize_chunk",
                chunk_index=0,
                content_text="summary zero",
                payload_json={"chunk_text": "page zero", "max_chunks": 2},
            )
        )
        db.session.commit()

        with pytest.raises(ValueError, match="incomplete chunk_summary"):
            run_document_job_stage(
                stage="aggregate",
                chunk_index=None,
                document_task_id=task.id,
                storage_path="/tmp/aggregate-gap.pdf",
                term_id=term.id,
                user_id=user.id,
                max_chunks=2,
            )


def test_run_document_job_stage_finalize_projects_final_result() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        user = User(username="pipeline-finalize-user", role=UserRole.student, display_name="Pipe Final")
        term = Term(name="Task4 Pipeline Finalize")
        db.session.add_all([user, term])
        db.session.commit()
        task = DocumentTask(
            user_id=user.id,
            term_id=term.id,
            filename="finalize.pdf",
            storage_path="/tmp/finalize.pdf",
        )
        db.session.add(task)
        db.session.commit()
        db.session.add(
            DocumentArtifact(
                document_task_id=task.id,
                artifact_type=DocumentArtifactType.aggregate_summary,
                stage="aggregate",
                chunk_index=None,
                content_text="overall summary\n- point a\n- point b",
                payload_json={"chunk_summaries": ["summary zero", "summary one"], "max_chunks": 2},
            )
        )
        db.session.commit()

        patch = run_document_job_stage(
            stage="finalize",
            chunk_index=None,
            document_task_id=task.id,
            storage_path="/tmp/finalize.pdf",
            term_id=term.id,
            user_id=user.id,
            max_chunks=2,
        )

        assert patch == {
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
        }
