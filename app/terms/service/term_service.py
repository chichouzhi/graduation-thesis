"""Term service: list/detail with role-based visibility (AG-056)."""
from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.identity.service import IdentityService
from app.terms.model import Term, TermLlmConfig


class TermService:
    """Term queries with role-scoped visibility."""

    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    def list_terms_for_user(self, user_id: str) -> dict[str, list[dict[str, object]]]:
        """Return visible term list for given user."""
        user = self._identity.load_user_by_id(user_id)
        if user is None:
            return {"items": []}

        q = Term.query.order_by(Term.created_at.desc(), Term.id.desc())
        if user.role.value == "student":
            # Student side keeps one active/default term view in this stage.
            term = q.first()
            return {"items": [term.to_term()] if term is not None else []}
        return {"items": [t.to_term() for t in q.all()]}

    def get_term_for_user(self, user_id: str, term_id: str) -> dict[str, object] | None:
        """Return a term only when it is visible to current user."""
        user = self._identity.load_user_by_id(user_id)
        if user is None:
            return None
        term = Term.query.filter_by(id=str(term_id).strip()).one_or_none()
        if term is None:
            return None
        if user.role.value == "student":
            latest = Term.query.order_by(Term.created_at.desc(), Term.id.desc()).first()
            if latest is None or latest.id != term.id:
                return None
        return term.to_term()

    def create_term_as_admin(self, user_id: str, payload: dict[str, object]) -> dict[str, object]:
        """Create a term as admin user."""
        self._require_admin(user_id)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")

        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("name must be non-empty")

        term = Term(
            name=name,
            selection_start_at=self._parse_nullable_datetime(payload.get("selection_start_at")),
            selection_end_at=self._parse_nullable_datetime(payload.get("selection_end_at")),
        )
        db.session.add(term)
        db.session.commit()
        return term.to_term()

    def update_term_as_admin(
        self,
        user_id: str,
        term_id: str,
        payload: dict[str, object],
    ) -> dict[str, object] | None:
        """Patch a term as admin user."""
        self._require_admin(user_id)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")

        term = Term.query.filter_by(id=str(term_id).strip()).one_or_none()
        if term is None:
            return None

        if "name" in payload:
            name = str(payload.get("name", "")).strip()
            if not name:
                raise ValueError("name must be non-empty")
            term.name = name
        if "selection_start_at" in payload:
            term.selection_start_at = self._parse_nullable_datetime(payload.get("selection_start_at"))
        if "selection_end_at" in payload:
            term.selection_end_at = self._parse_nullable_datetime(payload.get("selection_end_at"))

        db.session.commit()
        return term.to_term()

    def get_llm_config_for_user(self, user_id: str, term_id: str) -> dict[str, object] | None:
        """Read term LLM config from single source when term is visible to user."""
        visible_term = self.get_term_for_user(user_id, term_id)
        if visible_term is None:
            return None
        cfg = db.session.get(TermLlmConfig, str(term_id).strip())
        if cfg is None:
            return {
                "provider": None,
                "daily_budget_tokens": None,
                "per_user_daily_tokens": None,
            }
        return cfg.to_llm_config()

    def update_llm_config_as_admin(
        self,
        user_id: str,
        term_id: str,
        payload: dict[str, object],
    ) -> dict[str, object] | None:
        """Patch term LLM config as admin with single-source upsert."""
        self._require_admin(user_id)
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        term = Term.query.filter_by(id=str(term_id).strip()).one_or_none()
        if term is None:
            return None

        cfg = db.session.get(TermLlmConfig, term.id)
        if cfg is None:
            cfg = TermLlmConfig(term_id=term.id)
            db.session.add(cfg)

        if "provider" in payload:
            provider = payload.get("provider")
            if provider is not None:
                provider = str(provider).strip()
                if provider == "":
                    raise ValueError("provider must be non-empty when provided")
            cfg.provider = provider

        for key in ("daily_budget_tokens", "per_user_daily_tokens"):
            if key not in payload:
                continue
            raw = payload.get(key)
            if raw is None:
                setattr(cfg, key, None)
                continue
            try:
                value = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} must be an integer or null") from exc
            if value < 0:
                raise ValueError(f"{key} must be >= 0")
            setattr(cfg, key, value)

        db.session.commit()
        return cfg.to_llm_config()

    def _require_admin(self, user_id: str) -> None:
        user = self._identity.load_user_by_id(user_id)
        if user is None or user.role.value != "admin":
            raise PermissionError("admin role required")

    @staticmethod
    def _parse_nullable_datetime(value: object) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            # contract style is RFC3339; normalize Z suffix for stdlib parser.
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError as exc:
            raise ValueError("invalid date-time format") from exc
