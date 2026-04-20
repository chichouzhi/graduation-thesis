"""Chat 域 ORM：``conversations`` / ``messages`` / ``chat_jobs`` 与 ``contract.yaml`` 对齐（AG-011 / AG-012 / AG-013）。"""
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


class ConversationContextType(str, enum.Enum):
    """与 ``contract.yaml`` → ``Conversation.context_type`` 一致。"""

    general = "general"
    topic = "topic"
    document = "document"


class MessageRole(str, enum.Enum):
    """与 ``contract.yaml`` → ``Message.role`` 一致。"""

    system = "system"
    user = "user"
    assistant = "assistant"


class MessageAsyncTaskStatus(str, enum.Enum):
    """与 ``contract.yaml`` → ``AsyncTaskStatus`` / 持久化列 ``delivery_status`` 一致。"""

    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Conversation(db.Model):
    """``conversations`` 表；``id`` 即 ``conversation_id``；``term_id`` 非空且索引（配额命名空间与 ``ChatJobPayload.term_id`` 同源）。"""

    __tablename__ = "conversations"

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
    title = db.Column(db.String(256), nullable=True)
    context_type = db.Column(
        db.Enum(ConversationContextType, name="conversation_context_type", native_enum=False, length=32),
        nullable=True,
    )
    context_ref_id = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    user = db.relationship("User", backref=db.backref("conversations", lazy=True))
    term = db.relationship("Term", backref=db.backref("conversations", lazy=True))
    messages = db.relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy=True,
    )
    chat_jobs = db.relationship(
        "ChatJob",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_conversation(self) -> dict[str, Any]:
        """``Conversation`` OpenAPI 组件形状（``date-time`` 为 UTC、``Z`` 后缀）。"""
        body: dict[str, Any] = {
            "id": self.id,
            "term_id": self.term_id,
            "title": self.title,
            "created_at": _dt_to_contract_iso(self.created_at) or "",
        }
        if self.context_type is not None:
            body["context_type"] = self.context_type.value
        else:
            body["context_type"] = None
        body["context_ref_id"] = self.context_ref_id
        if self.updated_at is not None:
            body["updated_at"] = _dt_to_contract_iso(self.updated_at)
        return body


class Message(db.Model):
    """``messages`` 表；``id`` 即 ``message_id``；assistant 占位允许 ``content`` 空串。

    对外 JSON 的 ``status`` 由列 ``delivery_status`` 映射（``user``/``system`` 为 ``null``）。
    """

    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(
        db.Enum(MessageRole, name="message_role", native_enum=False, length=16),
        nullable=False,
    )
    content = db.Column(db.Text, nullable=False, default="")
    delivery_status = db.Column(
        db.Enum(MessageAsyncTaskStatus, name="message_delivery_status", native_enum=False, length=16),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    conversation = db.relationship("Conversation", back_populates="messages")

    def to_message(self) -> dict[str, Any]:
        """``Message`` OpenAPI 组件形状（``status`` 对应库内 ``delivery_status``）。"""
        body: dict[str, Any] = {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "content": self.content,
            "created_at": _dt_to_contract_iso(self.created_at) or "",
        }
        if self.delivery_status is not None:
            body["status"] = self.delivery_status.value
        else:
            body["status"] = None
        if self.updated_at is not None:
            body["updated_at"] = _dt_to_contract_iso(self.updated_at)
        return body


class ChatJob(db.Model):
    """``chat_jobs`` 表；``job_id`` 即主键，与 ``ChatJobPayload.job_id`` / ``PostUserMessageResponse.job_id`` 一致。"""

    __tablename__ = "chat_jobs"
    __table_args__ = (
        db.Index("ix_chat_jobs_status_created_at", "status", "created_at"),
    )

    job_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_message_id = db.Column(
        db.String(36),
        db.ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    assistant_message_id = db.Column(
        db.String(36),
        db.ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(
        db.Enum(MessageAsyncTaskStatus, name="chat_job_status", native_enum=False, length=16),
        nullable=False,
        default=MessageAsyncTaskStatus.pending,
    )
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

    conversation = db.relationship("Conversation", back_populates="chat_jobs")
    user_message = db.relationship("Message", foreign_keys=[user_message_id])
    assistant_message = db.relationship("Message", foreign_keys=[assistant_message_id])

    def to_chat_job(self) -> dict[str, Any]:
        """``ChatJob`` OpenAPI 组件（``date-time`` 为 UTC、``Z`` 后缀）。"""
        body: dict[str, Any] = {
            "job_id": self.job_id,
            "conversation_id": self.conversation_id,
            "user_message_id": self.user_message_id,
            "assistant_message_id": self.assistant_message_id,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "created_at": _dt_to_contract_iso(self.created_at) or "",
            "updated_at": _dt_to_contract_iso(self.updated_at) or "",
        }
        body["error_code"] = self.error_code
        body["error_message"] = self.error_message
        body["max_attempts"] = self.max_attempts
        body["next_retry_at"] = _dt_to_contract_iso(self.next_retry_at)
        return body


__all__ = [
    "ChatJob",
    "Conversation",
    "ConversationContextType",
    "Message",
    "MessageAsyncTaskStatus",
    "MessageRole",
]
