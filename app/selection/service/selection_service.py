"""Selection service skeleton (policy + enqueue wiring)."""

from __future__ import annotations

import uuid
from typing import Any

from app.common.policy import PolicyGateway
from app.task import queue as queue_mod


class SelectionService:
    def teacher_accept_application(
        self, application_id: str, action: str, teacher_id: str, **kwargs: Any
    ) -> None:
        PolicyGateway.assert_can_enqueue(
            queue="reconcile_jobs", application_id=application_id, action=action, teacher_id=teacher_id, **kwargs
        )
        term_id = kwargs.get("term_id")
        scope = "by_term" if term_id else "full_table"
        payload: dict[str, Any] = {
            "reconcile_job_id": str(uuid.uuid4()),
            "scope": scope,
            "application_id": application_id,
            "action": action,
            "teacher_id": teacher_id,
        }
        if term_id is not None:
            payload["term_id"] = term_id
        queue_mod.enqueue("reconcile_jobs", payload)
