"""AG-037：``selection_reconcile`` 对 ``selected_count`` 与 active ``assignments`` 对齐。"""
from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import (
    Application,
    ApplicationFlowStatus,
    Assignment,
    AssignmentStatus,
)
from app.topic.model import Topic, TopicStatus
from app.terms.model import Term
from app.use_cases.selection_reconcile import reconcile_assignments


def _seed_topic_with_assignment() -> tuple[Term, Topic, Assignment]:
    teacher = User(username="t_rec", role=UserRole.teacher, display_name="T")
    student = User(username="s_rec", role=UserRole.student, display_name="S")
    term = Term(name="term rec")
    db.session.add_all([teacher, student, term])
    db.session.commit()

    topic = Topic(
        title="课题",
        summary="",
        requirements="",
        capacity=3,
        teacher_id=teacher.id,
        term_id=term.id,
        status=TopicStatus.published,
        selected_count=99,
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

    asg = Assignment(
        student_id=student.id,
        teacher_id=teacher.id,
        topic_id=topic.id,
        term_id=term.id,
        application_id=app_row.id,
        status=AssignmentStatus.active,
    )
    db.session.add(asg)
    db.session.commit()
    return term, topic, asg


def test_reconcile_assignments_fixes_selected_count_full_table() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        _term, topic, _asg = _seed_topic_with_assignment()
        assert topic.selected_count == 99

        out = reconcile_assignments(
            {
                "reconcile_job_id": "rj-1",
                "scope": "full_table",
                "term_id": None,
            },
            session=db.session,
        )
        assert out["topics_scanned"] >= 1
        assert out["topics_updated"] >= 1
        db.session.refresh(topic)
        assert topic.selected_count == 1


def test_reconcile_by_term_requires_term_id() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        with pytest.raises(ValueError, match="term_id"):
            reconcile_assignments(
                {"reconcile_job_id": "rj-2", "scope": "by_term", "term_id": None},
                session=db.session,
            )


def test_reconcile_by_term_only_scans_that_term() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        term, topic, _ = _seed_topic_with_assignment()
        topic.selected_count = 5
        db.session.commit()

        out = reconcile_assignments(
            {
                "reconcile_job_id": "rj-3",
                "scope": "by_term",
                "term_id": term.id,
            },
            session=db.session,
        )
        assert out["topics_scanned"] == 1
        db.session.refresh(topic)
        assert topic.selected_count == 1


def test_task_reconcile_jobs_run_invokes_use_case() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        term, topic, _ = _seed_topic_with_assignment()
        topic.selected_count = 0
        db.session.commit()

        from app.task import reconcile_jobs as rj

        rj.run(
            {
                "reconcile_job_id": "rj-4",
                "scope": "by_term",
                "term_id": term.id,
            }
        )
        db.session.refresh(topic)
        assert topic.selected_count == 1


def test_task_reconcile_jobs_run_returns_summary() -> None:
    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        term, _topic, _ = _seed_topic_with_assignment()

        from app.task import reconcile_jobs as rj

        out = rj.run(
            {
                "reconcile_job_id": "rj-5",
                "scope": "by_term",
                "term_id": term.id,
                "request_id": "req-1",
            }
        )
        assert out["scope"] == "by_term"
        assert out["topics_scanned"] >= 1


def test_task_reconcile_jobs_rejects_non_mapping_payload() -> None:
    from app.task import reconcile_jobs as rj

    with pytest.raises(ValueError, match="mapping"):
        rj.run([])  # type: ignore[arg-type]
