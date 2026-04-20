"""AG-018：``assignments`` 真源 ORM、``application_id`` 外键与 ``AssignmentStatus``。"""
from __future__ import annotations

from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import (
    Application,
    ApplicationFlowStatus,
    Assignment,
    AssignmentStatus,
)
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus


def _seed_accepted_application() -> tuple[User, User, Term, Topic, Application]:
    teacher = User(
        username="t_asg",
        role=UserRole.teacher,
        display_name="教师指导",
    )
    student = User(
        username="s_asg",
        role=UserRole.student,
        display_name="学生指导",
    )
    term = Term(name="2026 指导")
    db.session.add_all([teacher, student, term])
    db.session.commit()

    topic = Topic(
        title="毕设课题",
        summary="",
        requirements="",
        capacity=3,
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
        status=ApplicationFlowStatus.accepted,
    )
    db.session.add(app_row)
    db.session.commit()
    return teacher, student, term, topic, app_row


def test_assignment_persists_with_application_fk_and_maps_to_contract() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        teacher, student, term, topic, app_row = _seed_accepted_application()

        row = Assignment(
            student_id=student.id,
            teacher_id=teacher.id,
            topic_id=topic.id,
            term_id=term.id,
            application_id=app_row.id,
            status=AssignmentStatus.active,
        )
        db.session.add(row)
        db.session.commit()

        loaded = db.session.get(Assignment, row.id)
        assert loaded is not None
        assert loaded.application_id == app_row.id
        assert loaded.status == AssignmentStatus.active

        body = loaded.to_assignment(student_name=student.display_name, topic_title=topic.title)
        assert body["id"] == loaded.id
        assert body["student_id"] == student.id
        assert body["student_name"] == "学生指导"
        assert body["teacher_id"] == teacher.id
        assert body["topic_id"] == topic.id
        assert body["topic_title"] == "毕设课题"
        assert body["term_id"] == term.id
        assert body["application_id"] == app_row.id
        assert body["status"] == "active"
        assert body["confirmed_at"] is None

        assert app_row.assignments[0].id == loaded.id


def test_assignment_application_id_optional() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        teacher, student, term, topic, _app_row = _seed_accepted_application()

        row = Assignment(
            student_id=student.id,
            teacher_id=teacher.id,
            topic_id=topic.id,
            term_id=term.id,
            application_id=None,
            status=AssignmentStatus.active,
        )
        db.session.add(row)
        db.session.commit()

        loaded = db.session.get(Assignment, row.id)
        assert loaded is not None
        assert loaded.application_id is None
        body = loaded.to_assignment()
        assert body["application_id"] is None


def test_assignment_status_covers_contract() -> None:
    assert {s.value for s in AssignmentStatus} == {"active", "cancelled"}


def test_assignment_confirmed_at_optional_iso() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        teacher, student, term, topic, app_row = _seed_accepted_application()
        confirmed = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)

        row = Assignment(
            student_id=student.id,
            teacher_id=teacher.id,
            topic_id=topic.id,
            term_id=term.id,
            application_id=app_row.id,
            status=AssignmentStatus.active,
            confirmed_at=confirmed,
        )
        db.session.add(row)
        db.session.commit()

        loaded = db.session.get(Assignment, row.id)
        assert loaded is not None
        body = loaded.to_assignment()
        assert body["confirmed_at"] == "2026-05-01T12:00:00Z"
