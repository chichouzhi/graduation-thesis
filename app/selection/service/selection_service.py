"""Selection service skeleton (policy + enqueue wiring)."""

from app.common.policy import PolicyGateway
from app.task import queue as queue_mod


class SelectionService:
    def teacher_accept_application(
        self, application_id: str, action: str, teacher_id: str, **kwargs
    ) -> None:
        PolicyGateway.assert_can_enqueue(
            queue="reconcile_jobs", application_id=application_id, action=action, teacher_id=teacher_id, **kwargs
        )
        queue_mod.enqueue(
            "reconcile_jobs",
            {"application_id": application_id, "action": action, "teacher_id": teacher_id},
        )
