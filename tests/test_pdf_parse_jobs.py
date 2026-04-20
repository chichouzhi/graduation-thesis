from __future__ import annotations

import pytest

from app.task.pdf_parse_jobs import handle_pdf_parse_job, run
from app.use_cases.document_pdf_parse import PdfJobPayload, parse_pdf_and_plan_document_jobs


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
    jobs = parse_pdf_and_plan_document_jobs(payload)

    assert called_paths == ["/tmp/demo.pdf"]
    assert len(jobs) == 5  # extract + 2 summarize_chunk + aggregate + finalize
    assert jobs[0]["stage"] == "extract"
    assert jobs[1]["stage"] == "summarize_chunk"
    assert jobs[-1]["stage"] == "finalize"
    assert all(job["request_id"] == "req-1" for job in jobs)


def test_handle_pdf_parse_job_enqueues_document_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueued: list[dict[str, object]] = []

    def fake_planner(_: PdfJobPayload) -> tuple[dict[str, object], ...]:
        return (
            {"document_task_id": "dt-1", "user_id": "u-1", "storage_path": "/tmp/demo.pdf", "term_id": "term-1", "stage": "extract", "chunk_index": None, "max_chunks": 1},
            {"document_task_id": "dt-1", "user_id": "u-1", "storage_path": "/tmp/demo.pdf", "term_id": "term-1", "stage": "finalize", "chunk_index": None, "max_chunks": 1},
        )

    def fake_enqueue(payload: dict[str, object] | None = None, **_: object) -> dict[str, str]:
        assert payload is not None
        enqueued.append(payload)
        return {"job_id": "doc-job"}

    monkeypatch.setattr("app.task.pdf_parse_jobs.parse_pdf_and_plan_document_jobs", fake_planner)
    monkeypatch.setattr("app.task.pdf_parse_jobs.queue_mod.enqueue_document_jobs", fake_enqueue)

    jobs = handle_pdf_parse_job(_valid_pdf_payload())
    assert len(jobs) == 2
    assert enqueued == list(jobs)


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
