"""PDF parse orchestration shared by ``pdf_parse_jobs`` workers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapter.pdf import parse_document
from app.use_cases.document_pipeline import (
    DocumentChunkingPlan,
    build_document_job_payloads_for_plan,
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


@dataclass(frozen=True, slots=True)
class PdfParseSuccessPlan:
    """``pdf_parse`` 成功路径：UC 决策出的 ``document_jobs`` 载荷 + 可落库的最小解析轮廓（ADR）。"""

    document_job_payloads: tuple[dict[str, Any], ...]
    parsed_meta_for_result_json: dict[str, Any]


def _parsed_meta_for_writeback(parsed: dict[str, Any], *, max_chunks: int) -> dict[str, Any]:
    """写入 ``result_json`` 的 ``pdf_parse_outline``（不含全文，避免撑爆 JSON 列）。"""
    pages = parsed.get("pages") if isinstance(parsed.get("pages"), list) else []
    page_count = int(parsed.get("page_count", max_chunks))
    return {
        "pdf_parse_outline": {
            "page_count": page_count,
            "max_chunks": int(max_chunks),
            "page_text_char_counts": [len(str(p.get("text", ""))) for p in pages],
        }
    }


def parse_pdf_and_plan_document_jobs(payload: PdfJobPayload) -> PdfParseSuccessPlan:
    """解析 PDF，经 ``document_pipeline`` 生成默认 ``document_jobs`` 入队计划（无 LLM）。"""
    parsed = parse_document(payload.storage_path)
    pages = parsed.get("pages")
    if isinstance(pages, list):
        max_chunks = len(pages)
    else:
        max_chunks = int(parsed.get("page_count", 0))
    if max_chunks < 1:
        raise ValueError("parsed pdf must contain at least one page")

    plan = DocumentChunkingPlan(max_chunks=max_chunks)
    payloads = build_document_job_payloads_for_plan(
        plan,
        document_task_id=payload.document_task_id,
        user_id=payload.user_id,
        storage_path=payload.storage_path,
        term_id=payload.term_id,
        request_id=payload.request_id,
    )
    meta = _parsed_meta_for_writeback(parsed, max_chunks=max_chunks)
    return PdfParseSuccessPlan(document_job_payloads=payloads, parsed_meta_for_result_json=meta)
