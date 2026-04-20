"""Document 域 ORM：``document_tasks`` 与 ``contract.yaml`` → ``DocumentTask`` 对齐（AG-014）。"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from app.extensions import db


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt_to_contract_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class DocumentTaskType(str, enum.Enum):
    """与 ``contract.yaml`` → ``DocumentTask.task_type`` 一致。"""

    summary = "summary"
    conclusions = "conclusions"
    compare = "compare"


class DocumentLanguage(str, enum.Enum):
    """与 ``contract.yaml`` → ``DocumentTask.language`` 一致。"""

    zh = "zh"
    en = "en"


class DocumentTaskStatus(str, enum.Enum):
    """与 ``contract.yaml`` → ``AsyncTaskStatus`` / ``DocumentTask.status`` 一致。"""

    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class DocumentTask(db.Model):
    """``document_tasks`` 表；``id`` 即 ``document_task_id``；``term_id`` 非空（与 ``PdfJobPayload`` / ``DocumentJobPayload`` 同源）。"""

    __tablename__ = "document_tasks"
    __table_args__ = (
        db.Index("ix_document_tasks_user_status_created", "user_id", "status", "created_at"),
        db.Index("ix_document_tasks_status_created_at", "status", "created_at"),
        db.Index("ix_document_tasks_status_locked_at", "status", "locked_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term_id = db.Column(
        db.String(36),
        db.ForeignKey("terms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(512), nullable=False)
    task_type = db.Column(
        db.Enum(DocumentTaskType, name="document_task_type", native_enum=False, length=32),
        nullable=False,
        default=DocumentTaskType.summary,
    )
    language = db.Column(
        db.Enum(DocumentLanguage, name="document_language", native_enum=False, length=8),
        nullable=False,
        default=DocumentLanguage.zh,
    )
    status = db.Column(
        db.Enum(DocumentTaskStatus, name="document_task_status", native_enum=False, length=16),
        nullable=False,
        default=DocumentTaskStatus.pending,
    )
    locked_at = db.Column(db.DateTime, nullable=True)
    last_completed_chunk = db.Column(db.Integer, nullable=True)
    result_json = db.Column(db.JSON, nullable=True)
    result_storage_uri = db.Column(db.String(512), nullable=True)
    error_code = db.Column(db.String(128), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=True)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    user = db.relationship("User", backref=db.backref("document_tasks", lazy=True))
    term = db.relationship("Term", backref=db.backref("document_tasks", lazy=True))

    def to_document_task(self) -> dict[str, Any]:
        """``DocumentTask`` OpenAPI 组件（``result`` 来自 ``result_json``；``date-time`` 为 UTC、``Z`` 后缀）。"""
        result: dict[str, Any] | None = None
        if self.result_json is not None:
            result = {
                "summary": self.result_json.get("summary"),
                "bullet_points": self.result_json.get("bullet_points"),
                "raw_model": self.result_json.get("raw_model"),
            }
        body: dict[str, Any] = {
            "id": self.id,
            "term_id": self.term_id,
            "status": self.status.value,
            "filename": self.filename,
            "task_type": self.task_type.value,
            "language": self.language.value,
            "locked_at": _dt_to_contract_iso(self.locked_at),
            "last_completed_chunk": self.last_completed_chunk,
            "created_at": _dt_to_contract_iso(self.created_at) or "",
            "updated_at": _dt_to_contract_iso(self.updated_at) or "",
            "result": result,
            "result_storage_uri": self.result_storage_uri,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_attempts": self.max_attempts,
            "next_retry_at": _dt_to_contract_iso(self.next_retry_at),
        }
        return body


__all__ = [
    "DocumentLanguage",
    "DocumentTask",
    "DocumentTaskStatus",
    "DocumentTaskType",
]
