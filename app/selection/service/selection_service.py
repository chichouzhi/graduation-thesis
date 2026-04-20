"""Selection service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import db
from app.identity.model import UserRole
from app.identity.service import IdentityService
from app.selection.model import (
    Application,
    ApplicationFlowStatus,
    Assignment,
    AssignmentStatus,
    ReconcileDispatchFailure,
)
from app.task import queue as queue_mod
from app.terms.model import Term
from app.topic.model import Topic

logger = logging.getLogger(__name__)

class SelectionService:
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    @staticmethod
    def _require_non_empty(name: str, value: str) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"{name} must be non-empty")
        return text

    @staticmethod
    def _in_selection_window(term: Term) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if term.selection_start_at is not None and now < term.selection_start_at:
            return False
        if term.selection_end_at is not None and now > term.selection_end_at:
            return False
        return True

    def create_application_as_student(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        uid = self._require_non_empty("user_id", user_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            raise ValueError("user not found")
        if user.role != UserRole.student:
            raise PermissionError("only student can create applications")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        topic_id = self._require_non_empty("topic_id", payload.get("topic_id", ""))
        term_id = self._require_non_empty("term_id", payload.get("term_id", ""))
        priority = int(payload.get("priority", 0))
        if priority not in (1, 2):
            raise ValueError("priority must be 1 or 2")
        topic = db.session.get(Topic, topic_id)
        if topic is None:
            raise ValueError("topic not found")
        if topic.term_id != term_id:
            raise ValueError("topic.term_id mismatch")
        term = db.session.get(Term, term_id)
        if term is None:
            raise ValueError("term not found")
        if not self._in_selection_window(term):
            raise PermissionError("selection window is closed")
        row = Application(
            student_id=uid,
            term_id=term_id,
            topic_id=topic_id,
            priority=priority,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise ValueError("application violates uniqueness constraints") from exc
        return row.to_application(topic_title=topic.title)

    def list_applications_for_user(
        self,
        user_id: str,
        *,
        term_id: str | None = None,
        topic_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be >= 1")
        uid = self._require_non_empty("user_id", user_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return {"items": [], "page": page, "page_size": page_size, "total": 0}
        q = Application.query
        if user.role == UserRole.student:
            q = q.filter_by(student_id=uid)
        elif user.role == UserRole.teacher:
            q = q.join(Topic, Topic.id == Application.topic_id).filter(Topic.teacher_id == uid)
        elif user.role != UserRole.admin:
            raise PermissionError("role cannot list applications")
        if term_id is not None:
            q = q.filter(Application.term_id == str(term_id).strip())
        if topic_id is not None:
            q = q.filter(Application.topic_id == str(topic_id).strip())
        q = q.order_by(Application.created_at.desc(), Application.id.desc())
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        items = [r.to_application(topic_title=(r.topic.title if r.topic is not None else None)) for r in rows]
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    def withdraw_application_as_student(self, user_id: str, application_id: str) -> bool:
        uid = self._require_non_empty("user_id", user_id)
        aid = self._require_non_empty("application_id", application_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return False
        if user.role != UserRole.student:
            raise PermissionError("only student can withdraw")
        row = Application.query.filter_by(id=aid, student_id=uid).one_or_none()
        if row is None:
            return False
        term = db.session.get(Term, row.term_id)
        if term is None or not self._in_selection_window(term):
            raise PermissionError("selection window is closed")
        if row.status != ApplicationFlowStatus.pending:
            raise ValueError("only pending application can be withdrawn")
        row.status = ApplicationFlowStatus.withdrawn
        db.session.commit()
        return True

    def update_application_priority_as_student(
        self, user_id: str, application_id: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        uid = self._require_non_empty("user_id", user_id)
        aid = self._require_non_empty("application_id", application_id)
        user = self._identity.load_user_by_id(uid)
        if user is None:
            return None
        if user.role != UserRole.student:
            raise PermissionError("only student can reprioritize")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        row = Application.query.filter_by(id=aid, student_id=uid).one_or_none()
        if row is None:
            return None
        term = db.session.get(Term, row.term_id)
        if term is None or not self._in_selection_window(term):
            raise PermissionError("selection window is closed")
        if row.status != ApplicationFlowStatus.pending:
            raise ValueError("only pending application can reprioritize")
        priority = int(payload.get("priority", 0))
        if priority not in (1, 2):
            raise ValueError("priority must be 1 or 2")
        row.priority = priority
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            raise ValueError("priority conflicts with existing application") from exc
        return row.to_application(topic_title=(row.topic.title if row.topic is not None else None))

    def teacher_accept_application(
        self, application_id: str, action: str, teacher_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        aid = self._require_non_empty("application_id", application_id)
        teacher_uid = self._require_non_empty("teacher_id", teacher_id)
        decided_action = self._require_non_empty("action", action)
        teacher = self._identity.load_user_by_id(teacher_uid)
        if teacher is None:
            raise ValueError("teacher not found")
        if teacher.role not in {UserRole.teacher, UserRole.admin}:
            raise PermissionError("only teacher/admin can decide application")
        row = Application.query.filter_by(id=aid).one_or_none()
        if row is None:
            raise ValueError("application not found")
        topic = db.session.get(Topic, row.topic_id)
        if topic is None:
            raise ValueError("topic not found")
        if teacher.role == UserRole.teacher and topic.teacher_id != teacher_uid:
            raise PermissionError("teacher can only decide own topic applications")
        if row.status != ApplicationFlowStatus.pending:
            raise ValueError("only pending application can be decided")

        assignment: Assignment | None = None
        if decided_action == "reject":
            row.status = ApplicationFlowStatus.rejected
            db.session.commit()
        elif decided_action == "accept":
            if topic.selected_count >= topic.capacity:
                raise PolicyDenied("topic capacity exceeded", code=ErrorCode.CAPACITY_EXCEEDED)
            assignment = Assignment(
                student_id=row.student_id,
                teacher_id=topic.teacher_id,
                topic_id=topic.id,
                term_id=row.term_id,
                application_id=row.id,
                status=AssignmentStatus.active,
                confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            row.status = ApplicationFlowStatus.accepted
            topic.selected_count += 1
            Application.query.filter(
                Application.student_id == row.student_id,
                Application.term_id == row.term_id,
                Application.id != row.id,
                Application.status == ApplicationFlowStatus.pending,
            ).update({"status": ApplicationFlowStatus.superseded}, synchronize_session=False)
            db.session.add(assignment)
            db.session.commit()
            try:
                queue_mod.enqueue_reconcile_jobs(
                    {
                        "reconcile_job_id": str(uuid.uuid4()),
                        "scope": "by_term",
                        "term_id": row.term_id,
                        "application_id": row.id,
                        "action": decided_action,
                        "teacher_id": teacher_uid,
                    },
                    policy_context={
                        "application_id": row.id,
                        "action": decided_action,
                        "teacher_id": teacher_uid,
                        "term_id": row.term_id,
                        **kwargs,
                    },
                )
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                ReconcileDispatchFailure.query.filter(
                    ReconcileDispatchFailure.application_id == row.id,
                    ReconcileDispatchFailure.resolved_at.is_(None),
                ).update({"resolved_at": now}, synchronize_session=False)
                db.session.commit()
            except Exception as exc:
                db.session.add(
                    ReconcileDispatchFailure(
                        application_id=row.id,
                        term_id=row.term_id,
                        teacher_id=teacher_uid,
                        error_message=str(exc),
                    )
                )
                db.session.commit()
                # Commit has succeeded: keep primary transaction result and surface degraded-state via logs.
                logger.warning(
                    "reconcile enqueue failed after accept commit",
                    extra={
                        "application_id": row.id,
                        "term_id": row.term_id,
                        "teacher_id": teacher_uid,
                        "error": str(exc),
                    },
                )
        else:
            raise ValueError("action must be accept or reject")

        return {
            "application": row.to_application(topic_title=topic.title),
            "assignment": (None if assignment is None else assignment.to_assignment(topic_title=topic.title)),
        }
