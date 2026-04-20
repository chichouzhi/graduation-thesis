from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Application, ApplicationFlowStatus, Assignment, ReconcileDispatchFailure
from app.selection.service.selection_service import SelectionService
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus


def _create_user(username: str, role: UserRole) -> User:
    user = User(username=username, role=role, display_name=username)
    db.session.add(user)
    db.session.commit()
    return user


def test_selection_student_flow_and_teacher_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="2026",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("sel-stu", UserRole.student)
        teacher = _create_user("sel-tea", UserRole.teacher)
        topic = Topic(
            title="T",
            summary="S",
            requirements="R",
            capacity=1,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        monkeypatch.setattr(
            "app.selection.service.selection_service.queue_mod.enqueue_reconcile_jobs",
            lambda payload=None, **kwargs: {"job_id": "rj-1"},
        )
        svc = SelectionService()
        app_row = svc.create_application_as_student(
            student.id, {"topic_id": topic.id, "term_id": term.id, "priority": 1}
        )
        assert app_row["status"] == "pending"

        listed = svc.list_applications_for_user(student.id)
        assert listed["total"] == 1

        patched = svc.update_application_priority_as_student(student.id, app_row["id"], {"priority": 2})
        assert patched is not None and patched["priority"] == 2

        decision = svc.teacher_accept_application(app_row["id"], "accept", teacher.id)
        assert decision["application"]["status"] == "accepted"
        assert decision["assignment"] is not None
        assert db.session.query(Assignment).count() == 1


def test_selection_withdraw_rule() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(name="2027", selection_start_at=now - timedelta(days=1), selection_end_at=now + timedelta(days=1))
        db.session.add(term)
        db.session.commit()
        student = _create_user("sel-stu-2", UserRole.student)
        teacher = _create_user("sel-tea-2", UserRole.teacher)
        topic = Topic(
            title="T2",
            summary="S2",
            requirements="R2",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        assert SelectionService().withdraw_application_as_student(student.id, row.id) is True
        assert db.session.get(Application, row.id).status == ApplicationFlowStatus.withdrawn
        with pytest.raises(PermissionError):
            SelectionService().withdraw_application_as_student(teacher.id, row.id)


def test_selection_accept_persists_reconcile_enqueue_failure_record(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="2028",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("sel-stu-3", UserRole.student)
        teacher = _create_user("sel-tea-3", UserRole.teacher)
        topic = Topic(
            title="T3",
            summary="S3",
            requirements="R3",
            capacity=1,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        app_row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(app_row)
        db.session.commit()

        def _raise_enqueue(*_args: object, **_kwargs: object) -> dict[str, str]:
            raise RuntimeError("broker down")

        monkeypatch.setattr("app.selection.service.selection_service.queue_mod.enqueue_reconcile_jobs", _raise_enqueue)

        result = SelectionService().teacher_accept_application(app_row.id, "accept", teacher.id)
        assert result["application"]["status"] == "accepted"
        failure = (
            ReconcileDispatchFailure.query.filter_by(application_id=app_row.id)
            .order_by(ReconcileDispatchFailure.created_at.desc())
            .first()
        )
        assert failure is not None
        assert "broker down" in failure.error_message
        assert failure.resolved_at is None


def test_selection_accept_resolves_existing_reconcile_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="2029",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("sel-stu-4", UserRole.student)
        teacher = _create_user("sel-tea-4", UserRole.teacher)
        topic = Topic(
            title="T4",
            summary="S4",
            requirements="R4",
            capacity=1,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        app_row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(app_row)
        db.session.commit()
        db.session.add(
            ReconcileDispatchFailure(
                application_id=app_row.id,
                term_id=term.id,
                teacher_id=teacher.id,
                error_message="old failure",
            )
        )
        db.session.commit()

        monkeypatch.setattr(
            "app.selection.service.selection_service.queue_mod.enqueue_reconcile_jobs",
            lambda *_args, **_kwargs: {"job_id": "ok"},
        )

        SelectionService().teacher_accept_application(app_row.id, "accept", teacher.id)
        latest = ReconcileDispatchFailure.query.filter_by(application_id=app_row.id).first()
        assert latest is not None
        assert latest.resolved_at is not None
