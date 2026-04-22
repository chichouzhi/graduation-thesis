from __future__ import annotations

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Assignment, AssignmentStatus
from app.taskboard.model import Milestone, MilestoneStatus
from app.taskboard.service.milestone_service import MilestoneService
from app.topic.model import Topic, TopicStatus
from app.terms.model import Term


def _create_user(username: str, role: UserRole) -> User:
    user = User(username=username, role=role, display_name=username)
    db.session.add(user)
    db.session.commit()
    return user


def test_student_milestone_crud_and_teacher_guidance_listing() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user("ms-stu", UserRole.student)
        teacher = _create_user("ms-tea", UserRole.teacher)
        other_teacher = _create_user("ms-tea-2", UserRole.teacher)
        term = Term(name="2026")
        db.session.add(term)
        db.session.commit()
        topic = Topic(
            title="t",
            summary="s",
            requirements="r",
            capacity=2,
            selected_count=1,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        db.session.add(
            Assignment(
                student_id=student.id,
                teacher_id=teacher.id,
                topic_id=topic.id,
                term_id=term.id,
                status=AssignmentStatus.active,
            )
        )
        db.session.commit()

        svc = MilestoneService()
        created = svc.create_milestone_as_student(
            student.id,
            {
                "title": "m1",
                "description": "d",
                "start_date": "2026-03-01",
                "end_date": "2026-03-20",
                "status": "todo",
                "sort_order": 2,
            },
        )
        assert created["student_id"] == student.id
        assert created["status"] == "todo"

        updated = svc.update_milestone_as_student(student.id, created["id"], {"status": "doing", "sort_order": 1})
        assert updated is not None
        assert updated["status"] == "doing"

        teacher_list = svc.list_milestones_for_user(teacher.id, student_id=student.id)
        assert teacher_list["total"] == 1
        assert teacher_list["items"][0]["id"] == created["id"]

        denied = False
        try:
            svc.list_milestones_for_user(other_teacher.id, student_id=student.id)
        except PermissionError:
            denied = True
        assert denied

        assert svc.delete_milestone_as_student(student.id, created["id"]) is True
        assert db.session.get(Milestone, created["id"]) is None


def test_student_only_operations() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("ms-teacher", UserRole.teacher)
        student = _create_user("ms-student", UserRole.student)
        row = Milestone(
            student_id=student.id,
            title="x",
            start_date=MilestoneService._parse_date("2026-01-01"),
            end_date=MilestoneService._parse_date("2026-01-02"),
            status=MilestoneStatus.todo,
        )
        db.session.add(row)
        db.session.commit()

        svc = MilestoneService()
        raised = False
        try:
            svc.update_milestone_as_student(teacher.id, row.id, {"title": "z"})
        except PermissionError:
            raised = True
        assert raised


def test_list_milestones_date_range_and_get_single() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user("ms-range", UserRole.student)
        svc = MilestoneService()
        early = svc.create_milestone_as_student(
            student.id,
            {
                "title": "early",
                "start_date": "2026-01-01",
                "end_date": "2026-01-10",
                "status": "todo",
            },
        )
        late = svc.create_milestone_as_student(
            student.id,
            {
                "title": "late",
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "status": "todo",
            },
        )
        from datetime import date

        listed = svc.list_milestones_for_user(
            student.id,
            from_date=date(2026, 1, 5),
            to_date=date(2026, 2, 5),
        )
        ids = {x["id"] for x in listed["items"]}
        assert early["id"] in ids
        assert late["id"] in ids

        got = svc.get_milestone_for_user(student.id, early["id"])
        assert got is not None
        assert got["title"] == "early"
