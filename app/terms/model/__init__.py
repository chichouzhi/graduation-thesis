"""Terms 域 ORM：``terms`` / ``term_llm_configs`` 与 ``contract.yaml`` 对齐（AG-009 Term；AG-010 LlmConfig）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.extensions import db


def _naive_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt_to_contract_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class Term(db.Model):
    """``terms`` 表；``id`` 即 ``term_id``，与全库 ``term_id`` 外键语义一致。"""

    __tablename__ = "terms"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(256), nullable=False)
    selection_start_at = db.Column(db.DateTime, nullable=True)
    selection_end_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_naive_utc_now)

    def to_term(self) -> dict[str, Any]:
        """``Term`` OpenAPI 组件形状（``date-time`` 为 UTC、``Z`` 后缀）。"""
        return {
            "id": self.id,
            "name": self.name,
            "selection_start_at": _dt_to_contract_iso(self.selection_start_at),
            "selection_end_at": _dt_to_contract_iso(self.selection_end_at),
            "created_at": _dt_to_contract_iso(self.created_at) or "",
        }


class TermLlmConfig(db.Model):
    """``term_llm_configs`` 独立表；每 ``term_id`` 至多一行，与 ``LlmConfig`` 单一真源一致。"""

    __tablename__ = "term_llm_configs"

    term_id = db.Column(
        db.String(36),
        db.ForeignKey("terms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider = db.Column(db.String(256), nullable=True)
    daily_budget_tokens = db.Column(db.Integer, nullable=True)
    per_user_daily_tokens = db.Column(db.Integer, nullable=True)

    term = db.relationship(
        "Term",
        backref=db.backref("llm_config", uselist=False, passive_deletes=True),
    )

    def to_llm_config(self) -> dict[str, Any]:
        """``LlmConfig`` OpenAPI 组件（字段均可空）。"""
        return {
            "provider": self.provider,
            "daily_budget_tokens": self.daily_budget_tokens,
            "per_user_daily_tokens": self.per_user_daily_tokens,
        }


__all__ = ["Term", "TermLlmConfig"]
