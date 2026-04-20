"""PDF parse orchestration shared by ``pdf_parse_jobs`` workers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapter.pdf import parse_document
from app.use_cases.document_pipeline import (
    DocumentChunkingPlan,
    expand_default_document_job_plan,
)

_PDF_EXTRACT_STAGE = "pdf_extract"


@dataclass(frozen=True, slots=True)
class PdfJobPayload:
    """Typed payload for ``pdf_parse`` queue consumer."""

    document_task_id: str
    user_id: str
    storage_path: str
    term_id: str
    stage: str = _PDF_EXTRACT_STAGE
    request_id: str | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "PdfJobPayload":
        required = ("document_task_id", "user_id", "storage_path", "term_id")
        normalized: dict[str, str] = {}
        for key in required:
            val = payload.get(key)
            text = str(val).strip() if val is not None else ""
            if not text:
                raise ValueError(f"PdfJobPayload.{key} must be non-empty")
            normalized[key] = text

        stage = str(payload.get("stage", _PDF_EXTRACT_STAGE)).strip()
        if stage != _PDF_EXTRACT_STAGE:
            raise ValueError("PdfJobPayload.stage must be 'pdf_extract'")

        request_id_raw = payload.get("request_id")
        request_id = None if request_id_raw is None else str(request_id_raw).strip() or None
        return cls(
            document_task_id=normalized["document_task_id"],
            user_id=normalized["user_id"],
            storage_path=normalized["storage_path"],
            term_id=normalized["term_id"],
            stage=stage,
            request_id=request_id,
        )


def parse_pdf_and_plan_document_jobs(payload: PdfJobPayload) -> tuple[dict[str, Any], ...]:
    """Parse PDF and generate ``document_jobs`` payloads via document pipeline."""
    parsed = parse_document(payload.storage_path)
    pages = parsed.get("pages")
    if isinstance(pages, list):
        max_chunks = len(pages)
    else:
        max_chunks = int(parsed.get("page_count", 0))
    if max_chunks < 1:
        raise ValueError("parsed pdf must contain at least one page")

    plan = DocumentChunkingPlan(max_chunks=max_chunks)
    jobs = []
    for item in expand_default_document_job_plan(plan):
        job_payload: dict[str, Any] = {
            "document_task_id": payload.document_task_id,
            "user_id": payload.user_id,
            "storage_path": payload.storage_path,
            "term_id": payload.term_id,
            "stage": item.stage.value,
            "chunk_index": item.chunk_index,
            "max_chunks": max_chunks,
        }
        if payload.request_id is not None:
            job_payload["request_id"] = payload.request_id
        jobs.append(job_payload)
    return tuple(jobs)
