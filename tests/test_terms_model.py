"""AG-009：``terms`` ORM 与 ``Term`` 契约字段（含选题窗口）对齐。"""
from __future__ import annotations

from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.terms.model import Term, TermLlmConfig


def test_term_persists_selection_window_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        start = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
        end = datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc).replace(tzinfo=None)
        t = Term(
            name="2026 春",
            selection_start_at=start,
            selection_end_at=end,
        )
        db.session.add(t)
        db.session.commit()

        loaded = db.session.get(Term, t.id)
        assert loaded is not None
        assert loaded.name == "2026 春"
        assert loaded.selection_start_at == start
        assert loaded.selection_end_at == end

        body = loaded.to_term()
        assert body["id"] == loaded.id
        assert body["name"] == "2026 春"
        assert body["selection_start_at"] == "2026-03-01T00:00:00Z"
        assert body["selection_end_at"] == "2026-04-30T23:59:59Z"
        assert body["created_at"].endswith("Z")


def test_term_nullable_selection_window() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        t = Term(name="无窗口")
        db.session.add(t)
        db.session.commit()

        loaded = db.session.get(Term, t.id)
        assert loaded is not None
        body = loaded.to_term()
        assert body["selection_start_at"] is None
        assert body["selection_end_at"] is None


def test_term_llm_config_persists_by_term_id_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        t = Term(name="2026 秋")
        db.session.add(t)
        db.session.commit()

        cfg = TermLlmConfig(
            term_id=t.id,
            provider="stub",
            daily_budget_tokens=1_000_000,
            per_user_daily_tokens=10_000,
        )
        db.session.add(cfg)
        db.session.commit()

        loaded = db.session.get(TermLlmConfig, t.id)
        assert loaded is not None
        assert loaded.provider == "stub"
        assert loaded.daily_budget_tokens == 1_000_000
        assert loaded.per_user_daily_tokens == 10_000

        body = loaded.to_llm_config()
        assert body == {
            "provider": "stub",
            "daily_budget_tokens": 1_000_000,
            "per_user_daily_tokens": 10_000,
        }

        assert t.llm_config is not None
        assert t.llm_config.term_id == t.id


def test_term_llm_config_cascade_on_term_delete() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        t = Term(name="级联")
        db.session.add(t)
        db.session.commit()
        db.session.add(TermLlmConfig(term_id=t.id, provider="x"))
        db.session.commit()

        db.session.delete(t)
        db.session.commit()

        assert db.session.get(TermLlmConfig, t.id) is None
