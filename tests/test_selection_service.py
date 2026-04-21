from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Application, ApplicationFlowStatus, Assignment, ReconcileDispatchFailure
from app.selection.service.selection_service import SelectionService
from app.task.queue import RECONCILE_JOBS
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


def test_withdraw_outside_selection_window_raises() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="wd-closed",
            selection_start_at=now - timedelta(days=30),
            selection_end_at=now - timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("wd-stu", UserRole.student)
        teacher = _create_user("wd-tea", UserRole.teacher)
        topic = Topic(
            title="Wd",
            summary="S",
            requirements="R",
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
        with pytest.raises(PermissionError, match="selection window"):
            SelectionService().withdraw_application_as_student(student.id, row.id)


def test_withdraw_non_pending_raises() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="wd-np",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("wd-np-stu", UserRole.student)
        teacher = _create_user("wd-np-tea", UserRole.teacher)
        for i, status in enumerate(
            (
                ApplicationFlowStatus.accepted,
                ApplicationFlowStatus.rejected,
                ApplicationFlowStatus.superseded,
                ApplicationFlowStatus.withdrawn,
            )
        ):
            topic = Topic(
                title=f"WdNp-{i}",
                summary="S",
                requirements="R",
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
                status=status,
            )
            db.session.add(row)
            db.session.commit()
            with pytest.raises(ValueError, match="pending"):
                SelectionService().withdraw_application_as_student(student.id, row.id)
            db.session.delete(row)
            db.session.delete(topic)
            db.session.commit()


def test_withdraw_unknown_id_returns_false() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user("wd-miss", UserRole.student)
        assert SelectionService().withdraw_application_as_student(student.id, "00000000-0000-0000-0000-000000000099") is False


def test_withdraw_twice_second_call_raises() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="wd-2x",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("wd-2x-stu", UserRole.student)
        teacher = _create_user("wd-2x-tea", UserRole.teacher)
        topic = Topic(
            title="Wd2x",
            summary="S",
            requirements="R",
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
        svc = SelectionService()
        assert svc.withdraw_application_as_student(student.id, row.id) is True
        with pytest.raises(ValueError, match="pending"):
            svc.withdraw_application_as_student(student.id, row.id)


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


def _term_open_window() -> Term:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return Term(
        name="open-win",
        selection_start_at=now - timedelta(days=1),
        selection_end_at=now + timedelta(days=1),
    )


def test_create_application_requires_term_id_and_topic_term_alignment() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term = _term_open_window()
        other = Term(name="other-term")
        db.session.add_all([term, other])
        db.session.commit()
        student = _create_user("ca-stu", UserRole.student)
        teacher = _create_user("ca-tea", UserRole.teacher)
        topic = Topic(
            title="CA",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        svc = SelectionService()
        with pytest.raises(ValueError, match="term_id is required"):
            svc.create_application_as_student(
                student.id,
                {"topic_id": topic.id, "priority": 1},
            )
        with pytest.raises(ValueError, match="mismatch"):
            svc.create_application_as_student(
                student.id,
                {"topic_id": topic.id, "term_id": other.id, "priority": 1},
            )


def test_create_application_rejects_non_published_topic() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term = _term_open_window()
        db.session.add(term)
        db.session.commit()
        student = _create_user("ca-np-stu", UserRole.student)
        teacher = _create_user("ca-np-tea", UserRole.teacher)
        topic = Topic(
            title="Draft",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.draft,
        )
        db.session.add(topic)
        db.session.commit()
        with pytest.raises(ValueError, match="not published"):
            SelectionService().create_application_as_student(
                student.id,
                {"topic_id": topic.id, "term_id": term.id, "priority": 1},
            )


def test_create_application_unique_student_term_topic() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term = _term_open_window()
        db.session.add(term)
        db.session.commit()
        student = _create_user("ca-uq1-stu", UserRole.student)
        teacher = _create_user("ca-uq1-tea", UserRole.teacher)
        t1 = Topic(
            title="UQ1",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(t1)
        db.session.commit()
        svc = SelectionService()
        svc.create_application_as_student(
            student.id,
            {"topic_id": t1.id, "term_id": term.id, "priority": 1},
        )
        with pytest.raises(ValueError, match="uniqueness"):
            svc.create_application_as_student(
                student.id,
                {"topic_id": t1.id, "term_id": term.id, "priority": 2},
            )


def test_create_application_unique_student_term_priority() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term = _term_open_window()
        db.session.add(term)
        db.session.commit()
        student = _create_user("ca-uq2-stu", UserRole.student)
        teacher = _create_user("ca-uq2-tea", UserRole.teacher)
        t1 = Topic(
            title="UQ2a",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        t2 = Topic(
            title="UQ2b",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add_all([t1, t2])
        db.session.commit()
        svc = SelectionService()
        svc.create_application_as_student(
            student.id,
            {"topic_id": t1.id, "term_id": term.id, "priority": 1},
        )
        with pytest.raises(ValueError, match="uniqueness"):
            svc.create_application_as_student(
                student.id,
                {"topic_id": t2.id, "term_id": term.id, "priority": 1},
            )


def test_list_applications_teacher_filters_topic_and_term() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term_open = _term_open_window()
        term_other = Term(name="no-apps-term")
        db.session.add_all([term_open, term_other])
        db.session.commit()
        teacher = _create_user("lst-tea", UserRole.teacher)
        s1 = _create_user("lst-s1", UserRole.student)
        s2 = _create_user("lst-s2", UserRole.student)
        ta = Topic(
            title="Ta",
            summary="S",
            requirements="R",
            capacity=4,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term_open.id,
            status=TopicStatus.published,
        )
        tb = Topic(
            title="Tb",
            summary="S",
            requirements="R",
            capacity=4,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term_open.id,
            status=TopicStatus.published,
        )
        db.session.add_all([ta, tb])
        db.session.commit()
        svc = SelectionService()
        svc.create_application_as_student(
            s1.id, {"topic_id": ta.id, "term_id": term_open.id, "priority": 1}
        )
        svc.create_application_as_student(
            s1.id, {"topic_id": tb.id, "term_id": term_open.id, "priority": 2}
        )
        svc.create_application_as_student(
            s2.id, {"topic_id": ta.id, "term_id": term_open.id, "priority": 1}
        )

        all_rows = svc.list_applications_for_user(teacher.id)
        assert all_rows["total"] == 3

        only_a = svc.list_applications_for_user(teacher.id, topic_id=ta.id)
        assert only_a["total"] == 2
        assert {x["topic_id"] for x in only_a["items"]} == {ta.id}

        only_b = svc.list_applications_for_user(teacher.id, topic_id=tb.id)
        assert only_b["total"] == 1

        wrong_term = svc.list_applications_for_user(teacher.id, term_id=term_other.id)
        assert wrong_term["total"] == 0

        open_and_a = svc.list_applications_for_user(
            teacher.id, term_id=term_open.id, topic_id=ta.id
        )
        assert open_and_a["total"] == 2


def test_list_applications_student_and_admin_filters() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term_open = _term_open_window()
        db.session.add(term_open)
        db.session.commit()
        teacher = _create_user("lst2-tea", UserRole.teacher)
        admin = _create_user("lst2-adm", UserRole.admin)
        stu = _create_user("lst2-stu", UserRole.student)
        ta = Topic(
            title="T2a",
            summary="S",
            requirements="R",
            capacity=4,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term_open.id,
            status=TopicStatus.published,
        )
        tb = Topic(
            title="T2b",
            summary="S",
            requirements="R",
            capacity=4,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term_open.id,
            status=TopicStatus.published,
        )
        db.session.add_all([ta, tb])
        db.session.commit()
        svc = SelectionService()
        svc.create_application_as_student(
            stu.id, {"topic_id": ta.id, "term_id": term_open.id, "priority": 1}
        )
        svc.create_application_as_student(
            stu.id, {"topic_id": tb.id, "term_id": term_open.id, "priority": 2}
        )

        stu_all = svc.list_applications_for_user(stu.id)
        assert stu_all["total"] == 2
        stu_b = svc.list_applications_for_user(stu.id, topic_id=tb.id)
        assert stu_b["total"] == 1 and stu_b["items"][0]["topic_id"] == tb.id

        blank_ignored = svc.list_applications_for_user(stu.id, topic_id="   ")
        assert blank_ignored["total"] == 2

        adm_ta = svc.list_applications_for_user(admin.id, topic_id=ta.id)
        assert adm_ta["total"] == 1


def test_update_priority_outside_window_raises() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="pri-closed",
            selection_start_at=now - timedelta(days=20),
            selection_end_at=now - timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("pri-win-stu", UserRole.student)
        teacher = _create_user("pri-win-tea", UserRole.teacher)
        topic = Topic(
            title="PriWin",
            summary="S",
            requirements="R",
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
        with pytest.raises(PermissionError, match="selection window"):
            SelectionService().update_application_priority_as_student(
                student.id, row.id, {"priority": 2}
            )


def test_update_priority_non_pending_raises() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="pri-np",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("pri-np-stu", UserRole.student)
        teacher = _create_user("pri-np-tea", UserRole.teacher)
        topic = Topic(
            title="PriNp",
            summary="S",
            requirements="R",
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
            status=ApplicationFlowStatus.withdrawn,
        )
        db.session.add(row)
        db.session.commit()
        with pytest.raises(ValueError, match="pending"):
            SelectionService().update_application_priority_as_student(
                student.id, row.id, {"priority": 2}
            )


def test_update_priority_invalid_value_raises() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term = _term_open_window()
        db.session.add(term)
        db.session.commit()
        student = _create_user("pri-inv-stu", UserRole.student)
        teacher = _create_user("pri-inv-tea", UserRole.teacher)
        topic = Topic(
            title="PriInv",
            summary="S",
            requirements="R",
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
        svc = SelectionService()
        for bad in (0, 3, -1):
            with pytest.raises(ValueError, match="priority must be 1 or 2"):
                svc.update_application_priority_as_student(student.id, row.id, {"priority": bad})


def test_update_priority_conflicts_with_sibling_application() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        term = _term_open_window()
        db.session.add(term)
        db.session.commit()
        student = _create_user("pri-cf-stu", UserRole.student)
        teacher = _create_user("pri-cf-tea", UserRole.teacher)
        t1 = Topic(
            title="PriCf1",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        t2 = Topic(
            title="PriCf2",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add_all([t1, t2])
        db.session.commit()
        svc = SelectionService()
        svc.create_application_as_student(
            student.id, {"topic_id": t1.id, "term_id": term.id, "priority": 1}
        )
        a2 = svc.create_application_as_student(
            student.id, {"topic_id": t2.id, "term_id": term.id, "priority": 2}
        )
        with pytest.raises(ValueError, match="priority conflicts"):
            svc.update_application_priority_as_student(
                student.id, a2["id"], {"priority": 1}
            )


def test_teacher_reject_single_transaction_status_only(monkeypatch: pytest.MonkeyPatch) -> None:
    enqueue_calls: list[str] = []

    def capture_enqueue(*_a: object, **_k: object) -> dict[str, str]:
        enqueue_calls.append("reconcile")
        return {"job_id": "rj-reject"}

    monkeypatch.setattr(
        "app.selection.service.selection_service.queue_mod.enqueue_reconcile_jobs",
        capture_enqueue,
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="rj-reject-term",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("rj-stu", UserRole.student)
        teacher = _create_user("rj-tea", UserRole.teacher)
        topic = Topic(
            title="RjT",
            summary="S",
            requirements="R",
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

        out = SelectionService().teacher_accept_application(row.id, "reject", teacher.id)
        assert enqueue_calls == []
        assert out["assignment"] is None
        assert out["application"]["status"] == "rejected"
        reloaded = db.session.get(Application, row.id)
        assert reloaded is not None and reloaded.status == ApplicationFlowStatus.rejected


def test_accept_commit_then_policy_before_reconcile_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    policy_events: list[tuple[str, dict[str, object]]] = []

    class _PolicySpy:
        @staticmethod
        def assert_can_enqueue(*, queue: str, **ctx: object) -> None:
            policy_events.append((queue, dict(ctx)))

    import app.task.queue as queue_at

    real_enqueue = queue_at.enqueue_reconcile_jobs

    monkeypatch.setattr("app.extensions.get_policy_gateway", lambda: _PolicySpy())

    def wrapped_enqueue(
        payload: dict | None = None,
        *,
        policy_context: dict[str, object] | None = None,
        **kwargs: object,
    ) -> dict[str, str]:
        assert policy_events == [], "policy runs only after accept commit, inside enqueue"
        return real_enqueue(payload, policy_context=policy_context, **kwargs)

    monkeypatch.setattr(
        "app.selection.service.selection_service.queue_mod.enqueue_reconcile_jobs",
        wrapped_enqueue,
    )

    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="pol-order",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("pol-stu", UserRole.student)
        teacher = _create_user("pol-tea", UserRole.teacher)
        topic = Topic(
            title="Pol",
            summary="S",
            requirements="R",
            capacity=2,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add(topic)
        db.session.commit()
        app_row = SelectionService().create_application_as_student(
            student.id, {"topic_id": topic.id, "term_id": term.id, "priority": 1}
        )
        app_id = app_row["id"]
        teacher_uid = teacher.id
        term_id = term.id
        SelectionService().teacher_accept_application(app_id, "accept", teacher_uid)

    assert len(policy_events) == 1
    assert policy_events[0][0] == RECONCILE_JOBS
    ctx = policy_events[0][1]
    assert ctx["application_id"] == app_id
    assert ctx["action"] == "accept"
    assert ctx["teacher_id"] == teacher_uid
    assert ctx["term_id"] == term_id


def test_teacher_accept_co_transaction_assignment_selected_count_supersedes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.selection.service.selection_service.queue_mod.enqueue_reconcile_jobs",
        lambda *_a, **_k: {"job_id": "rj-acc"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="acc-co",
            selection_start_at=now - timedelta(days=1),
            selection_end_at=now + timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        student = _create_user("acc-stu", UserRole.student)
        teacher = _create_user("acc-tea", UserRole.teacher)
        t1 = Topic(
            title="Acc1",
            summary="S",
            requirements="R",
            capacity=3,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        t2 = Topic(
            title="Acc2",
            summary="S",
            requirements="R",
            capacity=3,
            selected_count=0,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
        )
        db.session.add_all([t1, t2])
        db.session.commit()
        svc = SelectionService()
        a1 = svc.create_application_as_student(
            student.id, {"topic_id": t1.id, "term_id": term.id, "priority": 1}
        )
        a2 = svc.create_application_as_student(
            student.id, {"topic_id": t2.id, "term_id": term.id, "priority": 2}
        )
        out = svc.teacher_accept_application(a1["id"], "accept", teacher.id)
        assert out["application"]["status"] == "accepted"
        assert out["assignment"] is not None

        topic1 = db.session.get(Topic, t1.id)
        topic2 = db.session.get(Topic, t2.id)
        assert topic1 is not None and topic1.selected_count == 1
        assert topic2 is not None and topic2.selected_count == 0

        asg = db.session.query(Assignment).filter_by(application_id=a1["id"]).one()
        assert asg.topic_id == t1.id and asg.student_id == student.id

        other = db.session.get(Application, a2["id"])
        assert other is not None and other.status == ApplicationFlowStatus.superseded


def test_update_priority_unknown_application_returns_none() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user("pri-miss", UserRole.student)
        assert (
            SelectionService().update_application_priority_as_student(
                student.id, "00000000-0000-0000-0000-000000000099", {"priority": 2}
            )
            is None
        )
