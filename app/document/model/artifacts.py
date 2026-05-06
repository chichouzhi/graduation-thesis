from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from app.extensions import db
from sqlalchemy import event


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DocumentArtifactType(str, enum.Enum):
    pdf_pages_text = "pdf_pages_text"
    chunk_summary = "chunk_summary"
    aggregate_summary = "aggregate_summary"
    final_result = "final_result"


def document_artifact_identity_key(
    artifact_type: DocumentArtifactType | str,
    stage: str,
    chunk_index: int | None,
) -> str:
    type_text = artifact_type.value if isinstance(artifact_type, DocumentArtifactType) else str(artifact_type)
    chunk_text = "" if chunk_index is None else str(int(chunk_index))
    return f"{type_text}\x1f{stage}\x1f{chunk_text}"


class DocumentArtifact(db.Model):
    __tablename__ = "document_artifacts"
    __table_args__ = (
        db.UniqueConstraint(
            "document_task_id",
            "artifact_key",
            name="uq_document_artifacts_task_artifact_key",
        ),
    )

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
    artifact_key = db.Column(db.String(160), nullable=False)
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


@event.listens_for(DocumentArtifact, "before_insert")
@event.listens_for(DocumentArtifact, "before_update")
def _sync_artifact_key(_mapper: object, _connection: object, target: DocumentArtifact) -> None:
    target.artifact_key = document_artifact_identity_key(
        target.artifact_type,
        target.stage,
        target.chunk_index,
    )


__all__ = ["DocumentArtifact", "DocumentArtifactType", "document_artifact_identity_key"]
