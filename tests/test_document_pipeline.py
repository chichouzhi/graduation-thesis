"""AG-034 / AG-035：``document_pipeline`` 幂等键、计划与 chunk 并行度。"""
from __future__ import annotations

import pytest

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
    planned = expand_default_document_job_plan(plan)
    assert len(payloads) == len(planned)
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
