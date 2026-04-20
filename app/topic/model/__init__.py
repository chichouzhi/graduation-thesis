"""Topic 域 ORM：``topics`` 表（AG-015）与契约 ``Topic`` 对齐。

画像持久化（**AG-016**）：采用 ``topics.portrait_json``（``db.JSON``），等价于
``spec/execution_plan.md`` 阶段 1 所述「``topic_portraits`` 或内嵌画像列」之外键方案；
序列化时映射为 OpenAPI ``Topic.portrait``（``contract.yaml``）。
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from app.extensions import db


class TopicPortraitStored(TypedDict, total=False):
    """``portrait_json`` 列允许写入的契约子集（关键词 + 可选抽取时间 ISO 字符串）。"""

    keywords: list[str]
    extracted_at: str | None


def contract_portrait_from_json(portrait_json: dict[str, Any] | None) -> dict[str, Any] | None:
    """将库内 JSON 列转为 ``Topic.portrait`` 响应形状（缺省键显式为 ``null``/省略由调用方一致化）。"""
    if portrait_json is None:
        return None
    return {
        "keywords": portrait_json.get("keywords"),
        "extracted_at": portrait_json.get("extracted_at"),
    }


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt_to_contract_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TopicStatus(str, enum.Enum):
    """课题业务生命周期（与 ``AsyncTaskStatus`` 独立）；对齐 ``contract.yaml`` → ``Topic.status``。"""

    draft = "draft"
    pending_review = "pending_review"
    published = "published"
    rejected = "rejected"
    closed = "closed"


class TopicKeywordJobStatus(str, enum.Enum):
    """``Topic.llm_keyword_job_status``；与 ``contract.yaml`` → ``AsyncTaskStatus`` 取值一致。"""

    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Topic(db.Model):
    """``topics`` 表；``id`` 即 ``topic_id``；``term_id`` / ``teacher_id`` 与契约外键语义一致。"""

    __tablename__ = "topics"
    __table_args__ = (
        db.Index("ix_topics_term_status", "term_id", "status"),
        db.Index("ix_topics_teacher_term", "teacher_id", "term_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(512), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    requirements = db.Column(db.Text, nullable=False, default="")
    tech_keywords = db.Column(db.JSON, nullable=True)
    capacity = db.Column(db.Integer, nullable=False)
    selected_count = db.Column(db.Integer, nullable=False, default=0)
    teacher_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    term_id = db.Column(
        db.String(36),
        db.ForeignKey("terms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.Enum(TopicStatus, name="topic_status", native_enum=False, length=32),
        nullable=False,
        default=TopicStatus.draft,
    )
    portrait_json = db.Column(db.JSON, nullable=True)
    llm_keyword_job_id = db.Column(db.String(36), nullable=True)
    llm_keyword_job_status = db.Column(
        db.Enum(TopicKeywordJobStatus, name="topic_keyword_job_status", native_enum=False, length=16),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    teacher = db.relationship("User", backref=db.backref("topics_authored", lazy=True))
    term = db.relationship("Term", backref=db.backref("topics", lazy=True))

    def to_topic(self) -> dict[str, Any]:
        """``Topic`` OpenAPI 组件（``portrait`` 来自 ``portrait_json``；时间戳 UTC、``Z`` 后缀）。"""
        portrait = contract_portrait_from_json(self.portrait_json)
        body: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "requirements": self.requirements,
            "tech_keywords": self.tech_keywords if self.tech_keywords is not None else [],
            "capacity": self.capacity,
            "selected_count": self.selected_count,
            "teacher_id": self.teacher_id,
            "term_id": self.term_id,
            "status": self.status.value,
            "portrait": portrait,
            "llm_keyword_job_id": self.llm_keyword_job_id,
            "llm_keyword_job_status": (
                self.llm_keyword_job_status.value if self.llm_keyword_job_status is not None else None
            ),
            "created_at": _dt_to_contract_iso(self.created_at) or "",
            "updated_at": _dt_to_contract_iso(self.updated_at) or "",
        }
        return body


__all__ = [
    "Topic",
    "TopicKeywordJobStatus",
    "TopicPortraitStored",
    "TopicStatus",
    "contract_portrait_from_json",
]
