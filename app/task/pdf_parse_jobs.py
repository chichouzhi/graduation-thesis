"""pdf_parse queue consumer: validate payload then fan out document jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.task import queue as queue_mod
from app.use_cases.document_pdf_parse import PdfJobPayload, parse_pdf_and_plan_document_jobs


def _default_writeback(document_task_id: str, patch: dict[str, Any]) -> None:
    from app.document.model import DocumentArtifact, DocumentArtifactType, DocumentTask, DocumentTaskStatus
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

    result_patch = patch.get("result_patch")
    if isinstance(result_patch, dict):
        base = dict(task.result_json or {})
        base.update(result_patch)
        task.result_json = base

    artifacts = patch.get("artifacts")
    if isinstance(artifacts, list):
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            chunk_index = None if item.get("chunk_index") is None else int(item["chunk_index"])
            artifact_type = DocumentArtifactType(str(item["artifact_type"]))
            stage = str(item["stage"])
            artifacts_found = (
                db.session.query(DocumentArtifact)
                .filter_by(
                    document_task_id=document_task_id,
                    artifact_type=artifact_type,
                    stage=stage,
                    chunk_index=chunk_index,
                )
                .order_by(
                    DocumentArtifact.updated_at.desc(),
                    DocumentArtifact.created_at.desc(),
                    DocumentArtifact.id.desc(),
                )
                .all()
            )
            artifact = artifacts_found[0] if artifacts_found else None
            for duplicate in artifacts_found[1:]:
                db.session.delete(duplicate)
            if artifact is None:
                artifact = DocumentArtifact(
                    document_task_id=document_task_id,
                    artifact_type=artifact_type,
                    stage=stage,
                    chunk_index=chunk_index,
                )
            artifact.storage_uri = None if item.get("storage_uri") is None else str(item.get("storage_uri"))
            artifact.payload_json = item.get("payload")
            artifact.content_text = None if item.get("content_text") is None else str(item.get("content_text"))
            db.session.add(artifact)

    db.session.commit()


def handle_pdf_parse_job(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    typed = PdfJobPayload.from_mapping(payload)
    plan = parse_pdf_and_plan_document_jobs(typed)
    # ADR：先持久化最小「可分块中间态」元数据，再按 document_pipeline 计划入队 document_jobs。
    _default_writeback(
        typed.document_task_id,
        {
            "result_patch": plan.parsed_meta_for_result_json,
            "artifacts": [plan.extracted_text_artifact_payload],
        },
    )
    for job in plan.document_job_payloads:
        queue_mod.enqueue_document_jobs(job)
    return plan.document_job_payloads


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
