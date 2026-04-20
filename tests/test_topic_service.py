from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus
from app.topic.service.topic_service import TopicService


def _create_user(username: str, role: UserRole) -> User:
    user = User(username=username, role=role, display_name=username)
    db.session.add(user)
    db.session.commit()
    return user


def test_topic_create_update_review_and_close(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-teacher", UserRole.teacher)
        admin = _create_user("tp-admin", UserRole.admin)
        term = Term(name="2026")
        db.session.add(term)
        db.session.commit()
        captured: dict[str, str] = {}

        def _enqueue(payload: dict | None = None, **_kwargs: object) -> dict[str, str]:
            assert isinstance(payload, dict)
            captured["topic_id"] = str(payload["topic_id"])
            return {"job_id": "k1"}

        monkeypatch.setattr("app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs", _enqueue)

        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "A", "summary": "B", "requirements": "C", "capacity": 2, "term_id": term.id},
        )
        assert created["status"] == "draft"
        assert created["llm_keyword_job_status"] == "pending"

        updated = svc.update_topic_as_teacher(teacher.id, created["id"], {"summary": "B2"})
        assert updated is not None
        assert updated["summary"] == "B2"

        submitted = svc.submit_topic_for_review(teacher.id, created["id"])
        assert submitted is not None and submitted["status"] == "pending_review"

        reviewed = svc.review_topic_as_admin(admin.id, created["id"], {"action": "approve"})
        assert reviewed is not None and reviewed["status"] == "published"

        row = db.session.get(Topic, created["id"])
        assert row is not None
        row.status = TopicStatus.rejected
        db.session.commit()
        assert svc.delete_or_withdraw_topic_as_teacher(teacher.id, created["id"]) is True


def test_topic_requires_teacher_role() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user("tp-student", UserRole.student)
        term = Term(name="2027")
        db.session.add(term)
        db.session.commit()
        with pytest.raises(PermissionError):
            TopicService().create_topic_as_teacher(
                student.id,
                {"title": "A", "summary": "B", "requirements": "C", "capacity": 1, "term_id": term.id},
            )
