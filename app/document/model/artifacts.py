from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from app.extensions import db


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DocumentArtifactType(str, enum.Enum):
    pdf_pages_text = "pdf_pages_text"
    chunk_summary = "chunk_summary"
    aggregate_summary = "aggregate_summary"
    final_result = "final_result"


class DocumentArtifact(db.Model):
    __tablename__ = "document_artifacts"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_task_id = db.Column(
        db.String(36),
        db.ForeignKey("document_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type = db.Column(
        db.Enum(DocumentArtifactType, name="document_artifact_type", native_enum=False, length=32),
        nullable=False,
    )
    stage = db.Column(db.String(64), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=True)
    storage_uri = db.Column(db.String(512), nullable=True)
    payload_json = db.Column(db.JSON, nullable=True)
    content_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    document_task = db.relationship("DocumentTask", back_populates="artifacts")

    def to_reference(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "id": self.id,
            "artifact_type": self.artifact_type.value,
            "stage": self.stage,
            "chunk_index": self.chunk_index,
            "storage_uri": self.storage_uri,
        }
        body["payload"] = self.payload_json
        return body


__all__ = ["DocumentArtifact", "DocumentArtifactType"]
