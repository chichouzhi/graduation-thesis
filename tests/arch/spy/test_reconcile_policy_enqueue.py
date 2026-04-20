"""
R-POLICY-SVC（含 reconcile_jobs）：Policy 拒绝时不得 enqueue；允许时须调用 queue。

实现约定（与 architecture.spec / execution_plan 对齐，若符号不同请改本文件 patch 路径或方法名表）：
- `app.common.policy.PolicyGateway.assert_can_enqueue`：拒绝时抛异常或返回 False（本测对「抛异常」分支断言）；
- `app.task.queue.enqueue`：统一入队门面；
- `app.selection.service.selection_service.SelectionService`：实现教师 **accept** 的业务方法（见 `METHOD_CANDIDATES`）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Application, ApplicationFlowStatus, ReconcileDispatchFailure
from app.selection.service.selection_service import SelectionService
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus

def _seed_accept_case() -> tuple[str, str]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    term = Term(
        name="spy-reconcile-term",
        selection_start_at=now - timedelta(days=1),
        selection_end_at=now + timedelta(days=1),
    )
    student = User(username="spy-reconcile-stu", role=UserRole.student, display_name="stu")
    teacher = User(username="spy-reconcile-tea", role=UserRole.teacher, display_name="tea")
    db.session.add_all([term, student, teacher])
    db.session.commit()
    topic = Topic(
        title="spy-topic",
        summary="s",
        requirements="r",
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
    return app_row.id, teacher.id


@patch("app.task.queue.enqueue")
@patch("app.common.policy.PolicyGateway.assert_can_enqueue")
def test_policy_deny_blocks_reconcile_enqueue(mock_assert_can_enqueue, mock_enqueue):
    """Policy 抛错 → enqueue 不得被调用，且失败事件应被持久化。"""
    mock_assert_can_enqueue.side_effect = RuntimeError("POLICY_DENY")

    app = create_app()
    with app.app_context():
        db.create_all()
        application_id, teacher_id = _seed_accept_case()
        SelectionService().teacher_accept_application(
            application_id=application_id,
            action="accept",
            teacher_id=teacher_id,
        )
        failure = ReconcileDispatchFailure.query.filter_by(application_id=application_id).first()
        assert failure is not None
        assert "POLICY_DENY" in failure.error_message
    mock_enqueue.assert_not_called()


@patch("app.task.queue.enqueue")
@patch("app.common.policy.PolicyGateway.assert_can_enqueue")
def test_policy_allow_invokes_enqueue(mock_assert_can_enqueue, mock_enqueue):
    """Policy 正常返回 → enqueue 须被调用（spy）。"""
    mock_assert_can_enqueue.return_value = None

    app = create_app()
    with app.app_context():
        db.create_all()
        application_id, teacher_id = _seed_accept_case()
        SelectionService().teacher_accept_application(
            application_id=application_id,
            action="accept",
            teacher_id=teacher_id,
        )

    mock_assert_can_enqueue.assert_called()
    mock_enqueue.assert_called()
