"""Document service."""

from __future__ import annotations

import uuid
from typing import Any

from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.document.model import DocumentLanguage, DocumentTask, DocumentTaskStatus, DocumentTaskType
from app.extensions import db, get_policy_gateway
from app.identity.service import IdentityService
from app.terms.model import Term
from app.adapter import storage as storage_mod
from app.task import queue as queue_mod


class DocumentService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _require_non_empty(name: str, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{name} must be non-empty")
        return text

    @staticmethod
    def _parse_task_type(value: str | None) -> DocumentTaskType:
        text = "summary" if value is None else str(value).strip()
        if not text:
            raise ValueError("task_type must be non-empty")
        try:
            return DocumentTaskType(text)
        except ValueError as exc:
            raise ValueError("task_type must be one of: summary, conclusions, compare") from exc

    @staticmethod
    def _parse_language(value: str | None) -> DocumentLanguage:
        text = "zh" if value is None else str(value).strip()
        if not text:
            raise ValueError("language must be non-empty")
        try:
            return DocumentLanguage(text)
        except ValueError as exc:
            raise ValueError("language must be one of: zh, en") from exc

    def _resolve_storage_path(
        self,
        *,
        user_id: str,
        filename: str,
        storage_path: str | None,
        file_bytes: bytes | None,
    ) -> str:
        if file_bytes is not None:
            rel_key = f"{user_id}/{uuid.uuid4()}-{filename}"
            return storage_mod.put_bytes(file_bytes, rel_key=rel_key)
        return self._require_non_empty("storage_path", storage_path or "")

    def create_document_task(
        self, user_id: str, term_id: str, storage_path: str, filename: str, **kwargs: Any
    ) -> dict[str, Any]:
        normalized_user_id = self._require_non_empty("user_id", user_id)
        normalized_term_id = self._require_non_empty("term_id", term_id)
        normalized_filename = self._require_non_empty("filename", filename)
        task_type = self._parse_task_type(kwargs.pop("task_type", None))
        language = self._parse_language(kwargs.pop("language", None))
        file_bytes = kwargs.pop("file_bytes", None)
        if file_bytes is not None and not isinstance(file_bytes, bytes):
            raise ValueError("file_bytes must be bytes when provided")
        normalized_storage_path = self._resolve_storage_path(
            user_id=normalized_user_id,
            filename=normalized_filename,
            storage_path=storage_path,
            file_bytes=file_bytes,
        )

        identity = getattr(self, "_identity", IdentityService())
        if identity.load_user_by_id(normalized_user_id) is None:
            raise ValueError("user not found")
        if db.session.get(Term, normalized_term_id) is None:
            raise ValueError("term not found")

        policy_gateway = get_policy_gateway()
        policy_gateway.assert_can_enqueue(
            queue=queue_mod.PDF_PARSE,
            user_id=normalized_user_id,
            term_id=normalized_term_id,
        )

        task_row = DocumentTask(
            id=str(uuid.uuid4()),
            user_id=normalized_user_id,
            term_id=normalized_term_id,
            filename=normalized_filename,
            storage_path=normalized_storage_path,
            task_type=task_type,
            language=language,
            status=DocumentTaskStatus.pending,
        )
        db.session.add(task_row)
        db.session.commit()

        try:
            queue_mod.enqueue_pdf_parse(
                {
                    "document_task_id": task_row.id,
                    "user_id": normalized_user_id,
                    "storage_path": normalized_storage_path,
                    "term_id": normalized_term_id,
                    "stage": "pdf_extract",
                    **kwargs,
                }
            )
        except Exception as exc:
            task_row.status = DocumentTaskStatus.failed
            task_row.error_code = ErrorCode.QUEUE_UNAVAILABLE.value
            task_row.error_message = str(exc)
            db.session.commit()
            raise PolicyDenied("pdf_parse queue is unavailable", code=ErrorCode.QUEUE_UNAVAILABLE) from exc

        return task_row.to_document_task()
