"""reconcile_jobs consumer: validate payload then call ``selection_reconcile``."""


from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def handle_reconcile_job(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    from app.extensions import db
    from app.use_cases.selection_reconcile import reconcile_assignments

    return dict(reconcile_assignments(payload, session=db.session))


def run(payload: Mapping[str, Any]) -> dict[str, Any]:
    return handle_reconcile_job(payload)
