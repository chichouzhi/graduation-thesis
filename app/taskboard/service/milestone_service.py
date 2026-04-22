"""Milestone service: student CRUD and teacher scoped reads."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.extensions import db
from app.identity.model import UserRole
from app.identity.service import IdentityService
from app.selection.model import Assignment, AssignmentStatus
from app.taskboard.model import Milestone, MilestoneStatus


class MilestoneService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _require_non_empty(name: str, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{name} must be non-empty")
        return text

    @staticmethod
    def _parse_date(value: str | None) -> date:
        if value is None:
            raise ValueError("date is required")
        text = str(value).strip()
        if not text:
            raise ValueError("date must be non-empty")
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("date must be YYYY-MM-DD") from exc

    @staticmethod
    def _parse_status(value: str | None) -> MilestoneStatus:
        if value is None:
            raise ValueError("status is required")
        text = str(value).strip()
        if not text:
            raise ValueError("status must be non-empty")
        try:
            return MilestoneStatus(text)
        except ValueError as exc:
            raise ValueError("status must be one of: todo, doing, done") from exc

    def _require_guidance(self, teacher_id: str, student_id: str) -> None:
        exists = (
            Assignment.query.filter_by(
                teacher_id=teacher_id,
                student_id=student_id,
                status=AssignmentStatus.active,
            )
            .limit(1)
            .first()
        )
        if exists is None:
            raise PermissionError("teacher has no active guidance relationship with student")

    def list_milestones_for_user(
        self,
        user_id: str,
        *,
        student_id: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        if from_date is not None and to_date is not None and from_date > to_date:
            raise ValueError("from_date must be <= to_date")
        uid = self._require_non_empty("user_id", user_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return {"items": [], "page": page, "page_size": page_size, "total": 0}

        if user.role == UserRole.student:
            target_student_id = uid
        elif user.role in {UserRole.teacher, UserRole.admin}:
            if student_id is None:
                target_student_id = uid if user.role == UserRole.student else ""
                if not target_student_id:
                    raise ValueError("student_id is required for teacher/admin listing")
            else:
                target_student_id = self._require_non_empty("student_id", student_id)
            if user.role == UserRole.teacher:
                self._require_guidance(uid, target_student_id)
        else:
            raise PermissionError("role cannot list milestones")

        q = Milestone.query.filter_by(student_id=target_student_id)
        if from_date is not None:
            q = q.filter(Milestone.end_date >= from_date)
        if to_date is not None:
            q = q.filter(Milestone.start_date <= to_date)
        q = q.order_by(
            Milestone.sort_order.asc(),
            Milestone.id.asc(),
        )
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {"items": [m.to_milestone() for m in rows], "page": page, "page_size": page_size, "total": total}

    def create_milestone_as_student(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        uid = self._require_non_empty("user_id", user_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            raise ValueError("user not found")
        if user.role != UserRole.student:
            raise PermissionError("only student can create milestone")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")

        title = self._require_non_empty("title", str(payload.get("title", "")))
        description = payload.get("description")
        start_date = self._parse_date(payload.get("start_date"))
        end_date = self._parse_date(payload.get("end_date"))
        status = self._parse_status(payload.get("status"))
        sort_order = int(payload.get("sort_order", 0))

        row = Milestone(
            student_id=uid,
            title=title,
            description=(None if description is None else str(description)),
            start_date=start_date,
            end_date=end_date,
            status=status,
            sort_order=sort_order,
        )
        db.session.add(row)
        db.session.commit()
        return row.to_milestone()

    def update_milestone_as_student(self, user_id: str, milestone_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        uid = self._require_non_empty("user_id", user_id)
        mid = self._require_non_empty("milestone_id", milestone_id)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return None
        if user.role != UserRole.student:
            raise PermissionError("only student can update milestone")

        row = Milestone.query.filter_by(id=mid, student_id=uid).one_or_none()
        if row is None:
            return None

        if "title" in payload:
            row.title = self._require_non_empty("title", str(payload["title"]))
        if "description" in payload:
            row.description = None if payload["description"] is None else str(payload["description"])
        if "start_date" in payload:
            row.start_date = self._parse_date(None if payload["start_date"] is None else str(payload["start_date"]))
        if "end_date" in payload:
            row.end_date = self._parse_date(None if payload["end_date"] is None else str(payload["end_date"]))
        if "status" in payload:
            row.status = self._parse_status(None if payload["status"] is None else str(payload["status"]))
        if "sort_order" in payload:
            row.sort_order = int(payload["sort_order"])

        db.session.commit()
        return row.to_milestone()

    def delete_milestone_as_student(self, user_id: str, milestone_id: str) -> bool:
        uid = self._require_non_empty("user_id", user_id)
        mid = self._require_non_empty("milestone_id", milestone_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return False
        if user.role != UserRole.student:
            raise PermissionError("only student can delete milestone")
        row = Milestone.query.filter_by(id=mid, student_id=uid).one_or_none()
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    def get_milestone_for_user(self, user_id: str, milestone_id: str) -> dict[str, Any] | None:
        uid = self._require_non_empty("user_id", user_id)
        mid = self._require_non_empty("milestone_id", milestone_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return None
        row = Milestone.query.filter_by(id=mid).one_or_none()
        if row is None:
            return None
        if user.role == UserRole.student:
            if row.student_id != uid:
                return None
            return row.to_milestone()
        if user.role == UserRole.teacher:
            self._require_guidance(uid, row.student_id)
            return row.to_milestone()
        if user.role == UserRole.admin:
            return row.to_milestone()
        return None
