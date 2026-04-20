from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term, TermLlmConfig
from app.terms.service import TermService


def _create_user(*, username: str, role: UserRole) -> User:
    user = User(username=username, role=role, display_name=username, password_hash="x")
    db.session.add(user)
    db.session.commit()
    return user


def _create_term(name: str, *, created_at: datetime | None = None) -> Term:
    term = Term(name=name)
    if created_at is not None:
        term.created_at = created_at
    db.session.add(term)
    db.session.commit()
    return term


def test_list_terms_for_teacher_returns_all_terms() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="t1", role=UserRole.teacher)
        _create_term("2026 春")
        _create_term("2026 秋")

        payload = TermService().list_terms_for_user(teacher.id)
        names = [item["name"] for item in payload["items"]]
        assert len(names) == 2
        assert set(names) == {"2026 春", "2026 秋"}


def test_list_terms_for_student_returns_latest_term_only() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user(username="s1", role=UserRole.student)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        _create_term("2026 春", created_at=base)
        latest = _create_term("2026 秋", created_at=base + timedelta(seconds=1))

        payload = TermService().list_terms_for_user(student.id)
        assert len(payload["items"]) == 1
        assert payload["items"][0]["id"] == latest.id


def test_get_term_for_user_applies_student_visibility() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user(username="s2", role=UserRole.student)
        older = _create_term("2025 秋")
        latest = _create_term("2026 春")
        svc = TermService()

        assert svc.get_term_for_user(student.id, latest.id) is not None
        assert svc.get_term_for_user(student.id, older.id) is None


def test_create_term_as_admin_success_and_forbidden() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = _create_user(username="admin1", role=UserRole.admin)
        teacher = _create_user(username="teacher1", role=UserRole.teacher)
        svc = TermService()

        created = svc.create_term_as_admin(
            admin.id,
            {
                "name": "2027 春",
                "selection_start_at": "2027-03-01T00:00:00Z",
                "selection_end_at": "2027-03-31T00:00:00Z",
            },
        )
        assert created["name"] == "2027 春"
        assert created["selection_start_at"] == "2027-03-01T00:00:00Z"
        assert created["selection_end_at"] == "2027-03-31T00:00:00Z"

        try:
            svc.create_term_as_admin(teacher.id, {"name": "forbidden"})
            assert False, "expected PermissionError"
        except PermissionError:
            pass


def test_update_term_as_admin_success_missing_and_invalid() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = _create_user(username="admin2", role=UserRole.admin)
        term = _create_term("2028 春")
        svc = TermService()

        updated = svc.update_term_as_admin(
            admin.id,
            term.id,
            {
                "name": "2028 秋",
                "selection_start_at": "2028-09-01T00:00:00Z",
            },
        )
        assert updated is not None
        assert updated["name"] == "2028 秋"
        assert updated["selection_start_at"] == "2028-09-01T00:00:00Z"
        assert svc.update_term_as_admin(admin.id, "missing-id", {"name": "x"}) is None

        try:
            svc.update_term_as_admin(admin.id, term.id, {"selection_end_at": "bad-dt"})
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_get_llm_config_for_user_reads_single_source() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="t2", role=UserRole.teacher)
        term = _create_term("2029 春")
        db.session.add(
            TermLlmConfig(
                term_id=term.id,
                provider="openai-compatible",
                daily_budget_tokens=100000,
                per_user_daily_tokens=3000,
            )
        )
        db.session.commit()

        payload = TermService().get_llm_config_for_user(teacher.id, term.id)
        assert payload == {
            "provider": "openai-compatible",
            "daily_budget_tokens": 100000,
            "per_user_daily_tokens": 3000,
        }


def test_get_llm_config_for_user_visibility_and_missing_config() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = _create_user(username="s3", role=UserRole.student)
        older = _create_term("2030 春")
        latest = _create_term("2030 秋")
        svc = TermService()

        # Student cannot read non-visible term config.
        assert svc.get_llm_config_for_user(student.id, older.id) is None

        # Visible term without config returns contract-shaped nullable fields.
        assert svc.get_llm_config_for_user(student.id, latest.id) == {
            "provider": None,
            "daily_budget_tokens": None,
            "per_user_daily_tokens": None,
        }


def test_update_llm_config_as_admin_upsert_and_patch() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = _create_user(username="admin3", role=UserRole.admin)
        term = _create_term("2031 春")
        svc = TermService()

        created = svc.update_llm_config_as_admin(
            admin.id,
            term.id,
            {
                "provider": "openai-compatible",
                "daily_budget_tokens": 50000,
                "per_user_daily_tokens": 2000,
            },
        )
        assert created == {
            "provider": "openai-compatible",
            "daily_budget_tokens": 50000,
            "per_user_daily_tokens": 2000,
        }

        patched = svc.update_llm_config_as_admin(
            admin.id,
            term.id,
            {"per_user_daily_tokens": None},
        )
        assert patched == {
            "provider": "openai-compatible",
            "daily_budget_tokens": 50000,
            "per_user_daily_tokens": None,
        }


def test_update_llm_config_as_admin_rejects_forbidden_or_invalid_payload() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="teacher2", role=UserRole.teacher)
        admin = _create_user(username="admin4", role=UserRole.admin)
        term = _create_term("2032 秋")
        svc = TermService()

        try:
            svc.update_llm_config_as_admin(teacher.id, term.id, {"provider": "x"})
            assert False, "expected PermissionError"
        except PermissionError:
            pass

        assert svc.update_llm_config_as_admin(admin.id, "missing-id", {"provider": "x"}) is None

        try:
            svc.update_llm_config_as_admin(admin.id, term.id, {"provider": "   "})
            assert False, "expected ValueError"
        except ValueError:
            pass
        try:
            svc.update_llm_config_as_admin(admin.id, term.id, {"daily_budget_tokens": -1})
            assert False, "expected ValueError"
        except ValueError:
            pass
