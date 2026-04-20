"""AG-019：``milestones`` ORM 与 ``Milestone`` 契约字段及 ``is_overdue`` / ``sort_order`` 策略对齐。"""
from __future__ import annotations

from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.taskboard.model import Milestone, MilestoneStatus, compute_is_overdue


def test_milestone_persists_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(
            username="stu1",
            role=UserRole.student,
            display_name="S",
        )
        db.session.add(u)
        db.session.commit()

        start = date(2026, 3, 1)
        end = date(2026, 6, 30)
        m = Milestone(
            student_id=u.id,
            title="开题",
            description=None,
            start_date=start,
            end_date=end,
            status=MilestoneStatus.doing,
            sort_order=2,
        )
        db.session.add(m)
        db.session.commit()

        loaded = db.session.get(Milestone, m.id)
        assert loaded is not None
        body = loaded.to_milestone()
        assert body["id"] == loaded.id
        assert body["student_id"] == u.id
        assert body["title"] == "开题"
        assert body["description"] is None
        assert body["start_date"] == "2026-03-01"
        assert body["end_date"] == "2026-06-30"
        assert body["status"] == "doing"
        assert body["sort_order"] == 2
        assert body["created_at"].endswith("Z")
        assert body["updated_at"] is not None and str(body["updated_at"]).endswith("Z")


def test_sort_order_defaults_to_zero() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(username="stu2", role=UserRole.student, display_name="T")
        db.session.add(u)
        db.session.commit()
        m = Milestone(
            student_id=u.id,
            title="默认序",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=MilestoneStatus.todo,
        )
        db.session.add(m)
        db.session.commit()
        assert m.sort_order == 0


def test_is_overdue_done_is_false() -> None:
    assert (
        compute_is_overdue(
            MilestoneStatus.done,
            date(2020, 1, 1),
            today_utc=date(2026, 4, 20),
        )
        is False
    )


def test_is_overdue_before_end_false() -> None:
    assert (
        compute_is_overdue(
            MilestoneStatus.doing,
            date(2026, 5, 1),
            today_utc=date(2026, 4, 20),
        )
        is False
    )


def test_is_overdue_after_end_true() -> None:
    assert (
        compute_is_overdue(
            MilestoneStatus.todo,
            date(2026, 4, 1),
            today_utc=date(2026, 4, 20),
        )
        is True
    )


def test_to_milestone_is_overdue_matches_compute() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(username="stu3", role=UserRole.student, display_name="U")
        db.session.add(u)
        db.session.commit()
        past_end = date(2026, 4, 1)
        m = Milestone(
            student_id=u.id,
            title="逾期测",
            start_date=past_end - timedelta(days=30),
            end_date=past_end,
            status=MilestoneStatus.todo,
        )
        db.session.add(m)
        db.session.commit()
        assert m.to_milestone()["is_overdue"] == compute_is_overdue(m.status, m.end_date)
