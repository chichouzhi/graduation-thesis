"""Taskboard 域 ORM：``milestones`` 与 ``contract.yaml`` → ``Milestone`` 对齐（AG-019）。

``sort_order``：持久化整型，默认 ``0``；**列表排序策略（写死）**：``ORDER BY sort_order ASC``，同序时 ``id ASC``（由服务层/查询落实）。

``is_overdue``：**非列**，序列化时按固定规则计算——``status != done`` 且 ``end_date`` 非空且 **UTC 日历日** 已晚于 ``end_date`` 则为 ``True``；否则 ``False``（含 ``end_date`` 为空）。
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from typing import Any

from app.extensions import db


class MilestoneStatus(str, enum.Enum):
    """与 ``contract.yaml`` → ``Milestone.status`` 一致：todo | doing | done。"""

    todo = "todo"
    doing = "doing"
    done = "done"


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt_to_contract_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_to_contract(d: date | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def compute_is_overdue(
    status: MilestoneStatus,
    end_date: date | None,
    *,
    today_utc: date | None = None,
) -> bool:
    """``is_overdue`` 单一真规则（写死）：未完成且已过 ``end_date``（按 UTC 日期）。"""
    if status == MilestoneStatus.done or end_date is None:
        return False
    day = today_utc if today_utc is not None else datetime.now(timezone.utc).date()
    return day > end_date


class Milestone(db.Model):
    """``milestones`` 表；``id`` 即 ``milestone_id``；``student_id`` 指向 ``users.id``。"""

    __tablename__ = "milestones"
    __table_args__ = (db.Index("ix_milestones_student_sort", "student_id", "sort_order"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(512), nullable=False)
    description = db.Column(db.String(4096), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(MilestoneStatus, name="milestone_status", native_enum=False, length=16),
        nullable=False,
        default=MilestoneStatus.todo,
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_naive_utc_now,
        onupdate=_naive_utc_now,
    )

    student = db.relationship("User", backref=db.backref("milestones", lazy=True))

    def to_milestone(self) -> dict[str, Any]:
        """``Milestone`` OpenAPI 组件（含派生 ``is_overdue``）。"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "title": self.title,
            "description": self.description,
            "start_date": _date_to_contract(self.start_date),
            "end_date": _date_to_contract(self.end_date),
            "status": self.status.value,
            "sort_order": self.sort_order,
            "is_overdue": compute_is_overdue(self.status, self.end_date),
            "created_at": _dt_to_contract_iso(self.created_at) or "",
            "updated_at": _dt_to_contract_iso(self.updated_at),
        }


__all__ = ["Milestone", "MilestoneStatus", "compute_is_overdue"]
