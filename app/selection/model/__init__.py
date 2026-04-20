"""Selection 域 ORM：``applications``（AG-017）、``assignments`` 真源（AG-018）与 ``contract.yaml`` 对齐。

唯一约束（applications）：``(student_id, term_id, topic_id)``、``(student_id, term_id, priority)``；
状态枚举 ``ApplicationFlowStatus`` 与 ``AsyncTaskStatus`` 独立。

``assignments``：``application_id`` 可空外键指向 ``applications.id``（与 ``Assignment.application_id`` 契约一致）。
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from app.extensions import db


class ApplicationFlowStatus(str, enum.Enum):
    """志愿填报生命周期；对齐 ``contract.yaml`` → ``ApplicationFlowStatus``。"""

    pending = "pending"
    withdrawn = "withdrawn"
    accepted = "accepted"
    rejected = "rejected"
    superseded = "superseded"


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt_to_contract_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class Application(db.Model):
    """``applications`` 表；``id`` 即 ``application_id``。"""

    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "term_id",
            "topic_id",
            name="uq_applications_student_term_topic",
        ),
        db.UniqueConstraint(
            "student_id",
            "term_id",
            "priority",
            name="uq_applications_student_term_priority",
        ),
        db.CheckConstraint("priority IN (1, 2)", name="ck_applications_priority"),
        db.Index("ix_applications_term_student", "term_id", "student_id"),
        db.Index("ix_applications_topic_status", "topic_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(
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
    topic_id = db.Column(
        db.String(36),
        db.ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    priority = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum(ApplicationFlowStatus, name="application_flow_status", native_enum=False, length=16),
        nullable=False,
        default=ApplicationFlowStatus.pending,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    student = db.relationship("User", backref=db.backref("applications", lazy=True))
    term = db.relationship("Term", backref=db.backref("applications", lazy=True))
    topic = db.relationship("Topic", backref=db.backref("applications", lazy=True))

    def to_application(self, *, topic_title: str | None = None) -> dict[str, Any]:
        """``Application`` OpenAPI 组件（``topic_title`` 由调用方从 ``Topic`` 注入）。"""
        body: dict[str, Any] = {
            "id": self.id,
            "topic_id": self.topic_id,
            "student_id": self.student_id,
            "term_id": self.term_id,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": _dt_to_contract_iso(self.created_at) or "",
        }
        if topic_title is not None:
            body["topic_title"] = topic_title
        if self.updated_at is not None:
            body["updated_at"] = _dt_to_contract_iso(self.updated_at)
        return body


class AssignmentStatus(str, enum.Enum):
    """指导关系生命周期；对齐 ``contract.yaml`` → ``Assignment.status``。"""

    active = "active"
    cancelled = "cancelled"


class Assignment(db.Model):
    """``assignments`` 表；``id`` 即 ``assignment_id``；``application_id`` 可空。"""

    __tablename__ = "assignments"
    __table_args__ = (
        db.Index("ix_assignments_term_student", "term_id", "student_id"),
        db.Index("ix_assignments_term_teacher", "term_id", "teacher_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    topic_id = db.Column(
        db.String(36),
        db.ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    term_id = db.Column(
        db.String(36),
        db.ForeignKey("terms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    application_id = db.Column(
        db.String(36),
        db.ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = db.Column(
        db.Enum(AssignmentStatus, name="assignment_status", native_enum=False, length=16),
        nullable=False,
        default=AssignmentStatus.active,
    )
    confirmed_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship(
        "User",
        foreign_keys=[student_id],
        backref=db.backref("assignments_as_student", lazy=True),
    )
    teacher = db.relationship(
        "User",
        foreign_keys=[teacher_id],
        backref=db.backref("assignments_as_teacher", lazy=True),
    )
    topic = db.relationship("Topic", backref=db.backref("assignments", lazy=True))
    term = db.relationship("Term", backref=db.backref("assignments", lazy=True))
    application = db.relationship(
        "Application",
        backref=db.backref("assignments", lazy=True),
        foreign_keys=[application_id],
    )

    def to_assignment(
        self,
        *,
        student_name: str | None = None,
        topic_title: str | None = None,
    ) -> dict[str, Any]:
        """``Assignment`` OpenAPI 组件（``student_name`` / ``topic_title`` 由调用方注入）。"""
        body: dict[str, Any] = {
            "id": self.id,
            "student_id": self.student_id,
            "teacher_id": self.teacher_id,
            "topic_id": self.topic_id,
            "term_id": self.term_id,
            "application_id": self.application_id,
            "status": self.status.value,
        }
        if student_name is not None:
            body["student_name"] = student_name
        if topic_title is not None:
            body["topic_title"] = topic_title
        body["confirmed_at"] = _dt_to_contract_iso(self.confirmed_at)
        return body


class ReconcileDispatchFailure(db.Model):
    """``reconcile_dispatch_failures`` 表；记录 accept 后 reconcile 入队失败，供后续补偿扫描。"""

    __tablename__ = "reconcile_dispatch_failures"
    __table_args__ = (
        db.Index("ix_reconcile_dispatch_failures_term_created", "term_id", "created_at"),
        db.Index("ix_reconcile_dispatch_failures_unresolved", "resolved_at", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = db.Column(
        db.String(36),
        db.ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term_id = db.Column(
        db.String(36),
        db.ForeignKey("terms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teacher_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    error_message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    resolved_at = db.Column(db.DateTime, nullable=True)

    application = db.relationship(
        "Application",
        backref=db.backref("reconcile_dispatch_failures", lazy=True),
        foreign_keys=[application_id],
    )
    term = db.relationship("Term", backref=db.backref("reconcile_dispatch_failures", lazy=True))
    teacher = db.relationship(
        "User",
        backref=db.backref("reconcile_dispatch_failures", lazy=True),
        foreign_keys=[teacher_id],
    )


__all__ = [
    "Application",
    "ApplicationFlowStatus",
    "Assignment",
    "AssignmentStatus",
    "ReconcileDispatchFailure",
]
