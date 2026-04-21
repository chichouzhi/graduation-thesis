from __future__ import annotations

from typing import Any

import pytest

from app import create_app
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus
from app.topic.service.topic_service import TopicService


def test_get_topic_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k0"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-get", UserRole.teacher)
        term = Term(name="2028")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "X", "summary": "Y", "requirements": "Z", "capacity": 1, "term_id": term.id},
        )
        got = svc.get_topic(created["id"])
        assert got is not None and got["id"] == created["id"]
        assert svc.get_topic("missing-id-0000") is None


def test_withdraw_pending_review_closes_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k0"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-wd-pr", UserRole.teacher)
        term = Term(name="2029")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "W", "summary": "Y", "requirements": "Z", "capacity": 1, "term_id": term.id},
        )
        svc.submit_topic_for_review(teacher.id, created["id"])
        assert svc.delete_or_withdraw_topic_as_teacher(teacher.id, created["id"]) is True
        row = db.session.get(Topic, created["id"])
        assert row is not None and row.status == TopicStatus.closed


def test_withdraw_published_topic_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k0"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-pub", UserRole.teacher)
        admin = _create_user("tp-adm", UserRole.admin)
        term = Term(name="2030")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "P", "summary": "Y", "requirements": "Z", "capacity": 1, "term_id": term.id},
        )
        svc.submit_topic_for_review(teacher.id, created["id"])
        svc.review_topic_as_admin(admin.id, created["id"], {"action": "approve"})
        with pytest.raises(ValueError, match="withdrawn"):
            svc.delete_or_withdraw_topic_as_teacher(teacher.id, created["id"])


def _create_user(username: str, role: UserRole) -> User:
    user = User(username=username, role=role, display_name=username)
    db.session.add(user)
    db.session.commit()
    return user


def test_create_topic_sync_portrait_uses_nlp_tokenize(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_text: list[str] = []

    def fake_tokenize(text: str) -> list[str]:
        seen_text.append(text)
        return ["nlp_a", "nlp_b"]

    monkeypatch.setattr("app.topic.service.topic_service.nlp_mod.tokenize", fake_tokenize)
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-nlp"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-nlp", UserRole.teacher)
        term = Term(name="nlp-term")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {
                "title": "标题",
                "summary": "摘要",
                "requirements": "要求",
                "capacity": 2,
                "term_id": term.id,
                "tech_keywords": ["kw1", "kw2"],
            },
        )
    assert seen_text and "标题" in seen_text[0] and "摘要" in seen_text[0]
    assert created["portrait"] is not None
    assert created["portrait"]["keywords"] == ["kw1", "kw2", "nlp_a", "nlp_b"]
    assert created["portrait"]["extracted_at"] is not None


def test_update_topic_resyncs_portrait_via_nlp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-up"},
    )
    calls: list[int] = []

    def counting_tokenize(text: str) -> list[str]:
        calls.append(1)
        return ["tok"] if "新" in text else ["old"]

    monkeypatch.setattr("app.topic.service.topic_service.nlp_mod.tokenize", counting_tokenize)
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-up-nlp", UserRole.teacher)
        term = Term(name="up-term")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {
                "title": "旧",
                "summary": "S",
                "requirements": "R",
                "capacity": 1,
                "term_id": term.id,
            },
        )
        assert created["portrait"]["keywords"] == ["old"]
        updated = svc.update_topic_as_teacher(teacher.id, created["id"], {"title": "新标题"})
        assert updated is not None
        assert updated["portrait"]["keywords"] == ["tok"]
        assert len(calls) >= 2


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


def test_create_topic_commits_before_enqueue_keyword_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        "app.topic.service.topic_service.get_policy_gateway",
        lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
    )
    orig_commit = db.session.commit

    def wrapped_commit() -> None:
        events.append("commit")
        orig_commit()

    def capture_enqueue(payload: dict | None = None, **_kwargs: Any) -> dict[str, str]:
        assert isinstance(payload, dict)
        assert db.session.get(Topic, payload["topic_id"]) is not None
        events.append("enqueue")
        return {"job_id": "k-order-create"}

    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-commit-c", UserRole.teacher)
        term = Term(name="ct-order")
        db.session.add(term)
        db.session.commit()

        monkeypatch.setattr(db.session, "commit", wrapped_commit)
        monkeypatch.setattr(
            "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
            capture_enqueue,
        )

        TopicService().create_topic_as_teacher(
            teacher.id,
            {"title": "A", "summary": "B", "requirements": "C", "capacity": 1, "term_id": term.id},
        )

    assert events.index("commit") < events.index("enqueue")


def test_update_topic_text_change_commits_before_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        "app.topic.service.topic_service.get_policy_gateway",
        lambda: type("P", (), {"assert_can_enqueue": staticmethod(lambda **_kw: None)}),
    )
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-seed"},
    )
    orig_commit = db.session.commit

    def wrapped_commit() -> None:
        events.append("commit")
        orig_commit()

    def capture_enqueue(payload: dict | None = None, **_kwargs: Any) -> dict[str, str]:
        events.append("enqueue")
        return {"job_id": "k-order-up"}

    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-commit-u", UserRole.teacher)
        term = Term(name="up-order")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "A", "summary": "B", "requirements": "C", "capacity": 2, "term_id": term.id},
        )
        events.clear()
        monkeypatch.setattr(db.session, "commit", wrapped_commit)
        monkeypatch.setattr(
            "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
            capture_enqueue,
        )
        svc.update_topic_as_teacher(teacher.id, created["id"], {"summary": "B2"})

    assert events.index("commit") < events.index("enqueue")


def test_create_topic_policy_deny_skips_persist_and_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny(**_kwargs: Any) -> None:
        raise PolicyDenied("denied", code=ErrorCode.POLICY_QUEUE_DEPTH)

    monkeypatch.setattr(
        "app.topic.service.topic_service.get_policy_gateway",
        lambda: type("P", (), {"assert_can_enqueue": staticmethod(deny)}),
    )

    def enqueue_must_not_run(*_a: Any, **_k: Any) -> dict[str, str]:
        raise AssertionError("enqueue_keyword_jobs must not run when policy denies")

    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        enqueue_must_not_run,
    )

    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-pol-deny", UserRole.teacher)
        term = Term(name="pol-term")
        db.session.add(term)
        db.session.commit()
        with pytest.raises(PolicyDenied):
            TopicService().create_topic_as_teacher(
                teacher.id,
                {"title": "A", "summary": "B", "requirements": "C", "capacity": 1, "term_id": term.id},
            )
        assert db.session.query(Topic).count() == 0


def test_update_topic_capacity_only_skips_policy_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-cap"},
    )

    def policy_must_not_run(**_kwargs: Any) -> None:
        raise AssertionError("assert_can_enqueue must not run when only capacity changes")

    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-cap-only", UserRole.teacher)
        term = Term(name="cap-term")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        created = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "A", "summary": "B", "requirements": "C", "capacity": 2, "term_id": term.id},
        )
        monkeypatch.setattr(
            "app.topic.service.topic_service.get_policy_gateway",
            lambda: type("P", (), {"assert_can_enqueue": staticmethod(policy_must_not_run)}),
        )
        out = svc.update_topic_as_teacher(teacher.id, created["id"], {"capacity": 5})
        assert out is not None and out["capacity"] == 5


def test_submit_review_state_transitions_without_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-sr"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-sr-t", UserRole.teacher)
        admin = _create_user("tp-sr-a", UserRole.admin)
        term = Term(name="sr-term")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        t1 = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "T1", "summary": "S", "requirements": "R", "capacity": 1, "term_id": term.id},
        )
        s1 = svc.submit_topic_for_review(teacher.id, t1["id"])
        assert s1 is not None and s1["status"] == "pending_review"

        pub = svc.review_topic_as_admin(admin.id, t1["id"], {"action": "approve", "comment": "ok"})
        assert pub is not None and pub["status"] == "published"

        t2 = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "T2", "summary": "S", "requirements": "R", "capacity": 1, "term_id": term.id},
        )
        svc.submit_topic_for_review(teacher.id, t2["id"])
        rej = svc.review_topic_as_admin(admin.id, t2["id"], {"action": "reject"})
        assert rej is not None and rej["status"] == "rejected"

        again = svc.submit_topic_for_review(teacher.id, t2["id"])
        assert again is not None and again["status"] == "pending_review"


def test_submit_fails_for_pending_review_or_published(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-sf"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-sf-t", UserRole.teacher)
        admin = _create_user("tp-sf-a", UserRole.admin)
        term = Term(name="sf-term")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        t = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "X", "summary": "S", "requirements": "R", "capacity": 1, "term_id": term.id},
        )
        svc.submit_topic_for_review(teacher.id, t["id"])
        with pytest.raises(ValueError, match="submitted"):
            svc.submit_topic_for_review(teacher.id, t["id"])
        svc.review_topic_as_admin(admin.id, t["id"], {"action": "approve"})
        with pytest.raises(ValueError, match="submitted"):
            svc.submit_topic_for_review(teacher.id, t["id"])


def test_review_requires_pending_review_and_valid_comment_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-rv"},
    )
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user("tp-rv-t", UserRole.teacher)
        admin = _create_user("tp-rv-a", UserRole.admin)
        term = Term(name="rv-term")
        db.session.add(term)
        db.session.commit()
        svc = TopicService()
        t = svc.create_topic_as_teacher(
            teacher.id,
            {"title": "R", "summary": "S", "requirements": "R", "capacity": 1, "term_id": term.id},
        )
        with pytest.raises(ValueError, match="reviewed"):
            svc.review_topic_as_admin(admin.id, t["id"], {"action": "approve"})
        svc.submit_topic_for_review(teacher.id, t["id"])
        with pytest.raises(ValueError, match="comment"):
            svc.review_topic_as_admin(admin.id, t["id"], {"action": "approve", "comment": 99})


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
