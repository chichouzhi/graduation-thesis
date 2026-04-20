"""pdf_parse queue consumer: validate payload then fan out document jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.task import queue as queue_mod
from app.use_cases.document_pdf_parse import PdfJobPayload, parse_pdf_and_plan_document_jobs


def _default_writeback(document_task_id: str, patch: dict[str, Any]) -> None:
    from app.document.model import DocumentTask, DocumentTaskStatus
    from app.extensions import db

    task = db.session.get(DocumentTask, document_task_id)
    if task is None:
        raise ValueError(f"document task not found: {document_task_id}")

    status_raw = patch.get("status")
    if status_raw is not None:
        task.status = DocumentTaskStatus(str(status_raw))
        if task.status == DocumentTaskStatus.running:
            task.locked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        elif task.status in (DocumentTaskStatus.done, DocumentTaskStatus.failed):
            task.locked_at = None

    if "error_code" in patch:
        code_raw = patch.get("error_code")
        task.error_code = None if code_raw is None else str(code_raw)
    if "error_message" in patch:
        msg_raw = patch.get("error_message")
        task.error_message = None if msg_raw is None else str(msg_raw)

    db.session.commit()


def handle_pdf_parse_job(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    typed = PdfJobPayload.from_mapping(payload)
    jobs = parse_pdf_and_plan_document_jobs(typed)
    for job in jobs:
        queue_mod.enqueue_document_jobs(job)
    return jobs


def run(payload: dict[str, Any]) -> None:
    typed = PdfJobPayload.from_mapping(payload)
    _default_writeback(typed.document_task_id, {"status": "running"})
    try:
        handle_pdf_parse_job(payload)
    except Exception as exc:
        _default_writeback(
            typed.document_task_id,
            {
                "status": "failed",
                "error_code": "DOMAIN_ERROR",
                "error_message": str(exc),
            },
        )
        raise
