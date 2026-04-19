"""
R-POLICY-SVC（含 reconcile_jobs）：Policy 拒绝时不得 enqueue；允许时须调用 queue。

实现约定（与 architecture.spec / execution_plan 对齐，若符号不同请改本文件 patch 路径或方法名表）：
- `app.common.policy.PolicyGateway.assert_can_enqueue`：拒绝时抛异常或返回 False（本测对「抛异常」分支断言）；
- `app.task.queue.enqueue`：统一入队门面；
- `app.selection.service.selection_service.SelectionService`：实现教师 **accept** 的业务方法（见 `METHOD_CANDIDATES`）。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.arch.spy._import_helpers import import_module_or_fail

METHOD_CANDIDATES = (
    "teacher_accept_application",
    "accept_application",
    "post_teacher_decision",
    "record_teacher_decision",
)


def _selection_service_stub():
    sel_mod = import_module_or_fail("app.selection.service.selection_service")
    cls = getattr(sel_mod, "SelectionService", None)
    if cls is None:
        pytest.fail("app.selection.service.selection_service 须定义 SelectionService")
    svc = object.__new__(cls)
    svc.db = MagicMock()
    svc.session = MagicMock()
    return cls, svc


def _find_accept_method(cls):
    for name in METHOD_CANDIDATES:
        fn = getattr(cls, name, None)
        if callable(fn):
            return fn
    pytest.fail(
        f"SelectionService 缺少 accept 相关方法；请在以下名称中实现其一: {METHOD_CANDIDATES}"
    )


@patch("app.task.queue.enqueue")
@patch("app.common.policy.PolicyGateway.assert_can_enqueue")
def test_policy_deny_blocks_reconcile_enqueue(mock_assert_can_enqueue, mock_enqueue):
    """Policy 抛错 → enqueue 不得被调用。"""
    mock_assert_can_enqueue.side_effect = RuntimeError("POLICY_DENY")

    cls, svc = _selection_service_stub()
    accept = _find_accept_method(cls)

    with pytest.raises(RuntimeError, match="POLICY_DENY"):
        accept(svc, application_id="app-1", action="accept", teacher_id="tea-1")

    mock_enqueue.assert_not_called()


@patch("app.task.queue.enqueue")
@patch("app.common.policy.PolicyGateway.assert_can_enqueue")
def test_policy_allow_invokes_enqueue(mock_assert_can_enqueue, mock_enqueue):
    """Policy 正常返回 → enqueue 须被调用（spy）。"""
    mock_assert_can_enqueue.return_value = None

    cls, svc = _selection_service_stub()
    accept = _find_accept_method(cls)
    accept(svc, application_id="app-1", action="accept", teacher_id="tea-1")

    mock_assert_can_enqueue.assert_called()
    mock_enqueue.assert_called()
