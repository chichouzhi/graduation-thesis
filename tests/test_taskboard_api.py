from __future__ import annotations

from datetime import date

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Assignment, AssignmentStatus
from app.taskboard.model import Milestone, MilestoneStatus
from app.topic.model import Topic, TopicStatus
from app.terms.model import Term


def _create_user(*, username: str, role: UserRole) -> User:
    user = User(
        username=username,
        role=role,
        display_name=username,
        password_hash=generate_password_hash("pass-123"),
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username: str) -> str:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": "pass-123"})
    assert r.status_code == 200
    return r.get_json()["access_token"]


def test_milestones_crud_student_201_200_204() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        stu = _create_user(username="tb-stu", role=UserRole.student)

    client = app.test_client()
    token = _login(client, "tb-stu")
    h = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/milestones",
        headers=h,
        json={
            "title": "m1",
            "description": "d",
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
            "status": "todo",
            "sort_order": 0,
        },
    )
    assert create.status_code == 201
    mid = create.get_json()["id"]

    one = client.get(f"/api/v1/milestones/{mid}", headers=h)
    assert one.status_code == 200
    assert one.get_json()["title"] == "m1"

    lst = client.get("/api/v1/milestones", headers=h)
    assert lst.status_code == 200
    assert lst.get_json()["total"] == 1

    patch = client.patch(
        f"/api/v1/milestones/{mid}",
        headers=h,
        json={"status": "doing"},
    )
    assert patch.status_code == 200
    assert patch.get_json()["status"] == "doing"

    dele = client.delete(f"/api/v1/milestones/{mid}", headers=h)
    assert dele.status_code == 204


def test_milestones_teacher_lists_with_student_id_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="tb-s2", role=UserRole.student)
        teacher = _create_user(username="tb-t2", role=UserRole.teacher)
        term = Term(name="tb-term")
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
        db.session.add(
            Milestone(
                student_id=student.id,
                title="ms",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
                status=MilestoneStatus.todo,
            )
        )
        db.session.commit()
        sid = student.id

    client = app.test_client()
    token = _login(client, "tb-t2")
    resp = client.get(f"/api/v1/milestones?student_id={sid}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1
