"""document_jobs consumer: validate payload, dispatch by stage, hook writeback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from flask import has_app_context

from app.common.error_envelope import ErrorCode
from app.task import queue as queue_mod
from app.use_cases.document_pipeline import DocumentJobStage, run_document_job_stage

WritebackFn = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class DocumentJobPayload:
    document_task_id: str
    user_id: str
    storage_path: str
    term_id: str
    stage: DocumentJobStage
    chunk_index: int | None = None
    max_chunks: int | None = None
    request_id: str | None = None
    dispatch_attempt: int | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "DocumentJobPayload":
        required = ("document_task_id", "user_id", "storage_path", "term_id")
        normalized: dict[str, str] = {}
        for key in required:
            raw = payload.get(key)
            text = str(raw).strip() if raw is not None else ""
            if not text:
                raise ValueError(f"DocumentJobPayload.{key} must be non-empty")
            normalized[key] = text

        stage = DocumentJobStage(str(payload.get("stage", "extract")))
        chunk_raw = payload.get("chunk_index")
        chunk_index = None if chunk_raw is None else int(chunk_raw)
        max_chunks_raw = payload.get("max_chunks")
        max_chunks = None if max_chunks_raw is None else int(max_chunks_raw)
        request_id_raw = payload.get("request_id")
        request_id = None if request_id_raw is None else str(request_id_raw).strip() or None
        dispatch_attempt_raw = payload.get("dispatch_attempt")
        dispatch_attempt = None if dispatch_attempt_raw is None else int(dispatch_attempt_raw)
        return cls(
            document_task_id=normalized["document_task_id"],
            user_id=normalized["user_id"],
            storage_path=normalized["storage_path"],
            term_id=normalized["term_id"],
            stage=stage,
            chunk_index=chunk_index,
            max_chunks=max_chunks,
            request_id=request_id,
            dispatch_attempt=dispatch_attempt,
        )


def _noop_writeback(_: str, __: dict[str, Any]) -> None:
    return None


def _task_is_terminal(document_task_id: str) -> bool:
    if not has_app_context():
        return False

    from app.document.model import DocumentTask, DocumentTaskStatus
    from app.extensions import db

    task = db.session.get(DocumentTask, document_task_id)
    if task is None:
        return False
    return task.status in (DocumentTaskStatus.done, DocumentTaskStatus.failed)


def _enqueue_followup_stage(
    *,
    document_task_id: str,
    user_id: str,
    storage_path: str,
    term_id: str,
    stage: DocumentJobStage,
    max_chunks: int | None,
    request_id: str | None,
) -> None:
    payload: dict[str, Any] = {
        "document_task_id": document_task_id,
        "user_id": user_id,
        "storage_path": storage_path,
        "term_id": term_id,
        "stage": stage.value,
        "chunk_index": None,
    }
    if max_chunks is not None:
        payload["max_chunks"] = int(max_chunks)
    if request_id is not None:
        payload["request_id"] = request_id
    queue_mod.enqueue_document_jobs(payload)


def _maybe_enqueue_followup_stage(
    typed: DocumentJobPayload,
    patch: dict[str, Any],
) -> None:
    if not has_app_context():
        return

    from app.document.model import DocumentTask, DocumentTaskStatus
    from app.extensions import db

    if patch.get("status") in ("done", "failed"):
        return

    task = db.session.get(DocumentTask, typed.document_task_id)
    if task is None:
        raise ValueError(f"document task not found: {typed.document_task_id}")
    if task.status in (DocumentTaskStatus.done, DocumentTaskStatus.failed):
        return

    progress = task.progress_json if isinstance(task.progress_json, dict) else {}
    total_chunks_raw = progress.get("total_chunks", typed.max_chunks)
    total_chunks = None if total_chunks_raw is None else int(total_chunks_raw)

    if typed.stage == DocumentJobStage.SUMMARIZE_CHUNK:
        completed_chunks_raw = progress.get("completed_chunks")
        completed_chunks = None if completed_chunks_raw is None else int(completed_chunks_raw)
        if total_chunks is None or completed_chunks is None or completed_chunks < total_chunks:
            return
        if task.current_stage != "summarize_chunks":
            return
        task.current_stage = "aggregate"
        db.session.commit()
        _enqueue_followup_stage(
            document_task_id=typed.document_task_id,
            user_id=typed.user_id,
            storage_path=typed.storage_path,
            term_id=typed.term_id,
            stage=DocumentJobStage.AGGREGATE,
            max_chunks=total_chunks,
            request_id=typed.request_id,
        )
        return

    if typed.stage == DocumentJobStage.AGGREGATE:
        if task.current_stage != "aggregate":
            return
        task.current_stage = "finalize"
        db.session.commit()
        _enqueue_followup_stage(
            document_task_id=typed.document_task_id,
            user_id=typed.user_id,
            storage_path=typed.storage_path,
            term_id=typed.term_id,
            stage=DocumentJobStage.FINALIZE,
            max_chunks=total_chunks,
            request_id=typed.request_id,
        )


def _default_writeback(document_task_id: str, patch: dict[str, Any]) -> None:
    from app.document.model import DocumentArtifact, DocumentArtifactType, DocumentTask, DocumentTaskStatus
    from app.extensions import db
    from sqlalchemy.exc import IntegrityError

    def _apply_once() -> None:
        task = db.session.get(DocumentTask, document_task_id)
        if task is None:
            raise ValueError(f"document task not found: {document_task_id}")
        if task.status in (DocumentTaskStatus.done, DocumentTaskStatus.failed):
            return

        status_raw = patch.get("status")
        if status_raw is not None:
            task.status = DocumentTaskStatus(str(status_raw))
            if task.status == DocumentTaskStatus.running:
                task.locked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            elif task.status in (DocumentTaskStatus.done, DocumentTaskStatus.failed):
                task.locked_at = None

        if "last_completed_chunk" in patch:
            v = patch.get("last_completed_chunk")
            task.last_completed_chunk = None if v is None else int(v)

        if "current_stage" in patch:
            stage_raw = patch.get("current_stage")
            task.current_stage = None if stage_raw is None else str(stage_raw)

        progress_patch = patch.get("progress_patch")
        if isinstance(progress_patch, dict):
            base_progress = dict(task.progress_json or {})
            base_progress.update(progress_patch)
            task.progress_json = base_progress

        result_patch = patch.get("result_patch")
        if isinstance(result_patch, dict):
            base = dict(task.result_json or {})
            base.update(result_patch)
            task.result_json = base

        artifacts = patch.get("artifacts")
        chunk_summary_total_chunks: int | None = None
        if isinstance(artifacts, list):
            for item in artifacts:
                if not isinstance(item, dict):
                    continue
                chunk_index = None if item.get("chunk_index") is None else int(item["chunk_index"])
                artifact_type = DocumentArtifactType(str(item["artifact_type"]))
                stage = str(item["stage"])
                if artifact_type == DocumentArtifactType.chunk_summary:
                    payload = item.get("payload")
                    if isinstance(payload, dict) and payload.get("max_chunks") is not None:
                        chunk_summary_total_chunks = int(payload["max_chunks"])
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

        if chunk_summary_total_chunks is not None:
            completed_chunks = (
                db.session.query(DocumentArtifact)
                .filter_by(
                    document_task_id=document_task_id,
                    artifact_type=DocumentArtifactType.chunk_summary,
                    stage="summarize_chunk",
                )
                .count()
            )
            task.progress_json = {
                "completed_chunks": int(completed_chunks),
                "total_chunks": int(chunk_summary_total_chunks),
            }

        if "error_code" in patch:
            code_raw = patch.get("error_code")
            task.error_code = None if code_raw is None else str(code_raw)
        if "error_message" in patch:
            msg_raw = patch.get("error_message")
            task.error_message = None if msg_raw is None else str(msg_raw)

        db.session.commit()

    for attempt in range(2):
        try:
            _apply_once()
            return
        except IntegrityError:
            db.session.rollback()
            if attempt == 1:
                raise


def handle_document_job(
    payload: dict[str, Any],
    *,
    writeback: WritebackFn = _noop_writeback,
) -> dict[str, Any]:
    typed = DocumentJobPayload.from_mapping(payload)
    patch = run_document_job_stage(
        stage=typed.stage,
        chunk_index=typed.chunk_index,
        document_task_id=typed.document_task_id,
        storage_path=typed.storage_path,
        term_id=typed.term_id,
        user_id=typed.user_id,
        max_chunks=typed.max_chunks,
        request_id=typed.request_id,
    )
    writeback(typed.document_task_id, patch)
    return patch


def run(payload: dict[str, Any]) -> None:
    typed = DocumentJobPayload.from_mapping(payload)
    if _task_is_terminal(typed.document_task_id):
        return
    _default_writeback(typed.document_task_id, {"status": "running"})
    try:
        patch = handle_document_job(payload, writeback=_default_writeback)
    except Exception as exc:
        _default_writeback(
            typed.document_task_id,
            {
                "status": "failed",
                "error_code": ErrorCode.DOMAIN_ERROR.value,
                "error_message": str(exc),
            },
        )
        raise

    final_status = patch.get("status")
    if final_status in ("done", "failed"):
        return
    if _task_is_terminal(typed.document_task_id):
        return
    try:
        _maybe_enqueue_followup_stage(typed, patch)
    except Exception as exc:
        _default_writeback(
            typed.document_task_id,
            {
                "status": "failed",
                "error_code": ErrorCode.QUEUE_UNAVAILABLE.value,
                "error_message": str(exc),
            },
        )
        raise
    return
