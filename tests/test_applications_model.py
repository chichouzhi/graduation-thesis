"""AG-017：``applications`` ORM、唯一约束与 ``ApplicationFlowStatus``。"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Application, ApplicationFlowStatus
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus


def _seed_user_term_topics() -> tuple[User, Term, Topic, Topic]:
    teacher = User(
        username="t_app",
        role=UserRole.teacher,
        display_name="教师志愿测",
    )
    student = User(
        username="s_app",
        role=UserRole.student,
        display_name="学生志愿测",
    )
    term = Term(name="2026 春")
    db.session.add_all([teacher, student, term])
    db.session.commit()

    t1 = Topic(
        title="课题一",
        summary="",
        requirements="",
        capacity=5,
        teacher_id=teacher.id,
        term_id=term.id,
        status=TopicStatus.published,
    )
    t2 = Topic(
        title="课题二",
        summary="",
        requirements="",
        capacity=5,
        teacher_id=teacher.id,
        term_id=term.id,
        status=TopicStatus.published,
    )
    db.session.add_all([t1, t2])
    db.session.commit()
    return student, term, t1, t2


def test_application_persists_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student, term, topic_a, _topic_b = _seed_user_term_topics()

        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic_a.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()

        loaded = db.session.get(Application, row.id)
        assert loaded is not None
        assert loaded.status == ApplicationFlowStatus.pending

        body = loaded.to_application(topic_title=topic_a.title)
        assert body["id"] == loaded.id
        assert body["topic_id"] == topic_a.id
        assert body["topic_title"] == "课题一"
        assert body["student_id"] == student.id
        assert body["term_id"] == term.id
        assert body["priority"] == 1
        assert body["status"] == "pending"
        assert body["created_at"].endswith("Z")
        assert "updated_at" in body


def test_application_flow_status_covers_contract() -> None:
    assert {s.value for s in ApplicationFlowStatus} == {
        "pending",
        "withdrawn",
        "accepted",
        "rejected",
        "superseded",
    }


def test_unique_constraint_student_term_topic() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student, term, topic_a, _t2 = _seed_user_term_topics()

        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic_a.id,
                priority=1,
            )
        )
        db.session.commit()

        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic_a.id,
                priority=2,
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_unique_constraint_student_term_priority() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student, term, topic_a, topic_b = _seed_user_term_topics()

        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic_a.id,
                priority=1,
            )
        )
        db.session.commit()

        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic_b.id,
                priority=1,
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
