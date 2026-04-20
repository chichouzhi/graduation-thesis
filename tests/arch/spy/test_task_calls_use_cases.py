"""
M-CHAIN-WORKER / W4：task/*_jobs 消费路径须调用 app.use_cases。

- reconcile_jobs → app.use_cases.selection_reconcile.reconcile_assignments（ADR）
- chat_jobs → app.use_cases.chat_orchestration.run_turn（或等价符号，见 CANDIDATES）
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.arch.spy._import_helpers import get_callable_or_fail, import_module_or_fail

CHAT_JOB_HANDLER_CANDIDATES = ("handle_chat_job", "process_chat_job", "run")
RECONCILE_HANDLER_CANDIDATES = ("handle_reconcile_job", "process_reconcile_job", "run")


def test_reconcile_jobs_invokes_use_cases_run():
    rj = import_module_or_fail("app.task.reconcile_jobs")
    handler = get_callable_or_fail(rj, *RECONCILE_HANDLER_CANDIDATES)
    payload = {
        "reconcile_job_id": "rj-1",
        "scope": "by_term",
        "term_id": "term-1",
    }
    with patch("app.use_cases.selection_reconcile.reconcile_assignments") as mock_uc:
        handler(payload)
    mock_uc.assert_called_once()


def test_chat_jobs_invokes_use_cases_run_turn():
    cj = import_module_or_fail("app.task.chat_jobs")
    handler = get_callable_or_fail(cj, *CHAT_JOB_HANDLER_CANDIDATES)
    payload = {
        "job_id": "job-1",
        "conversation_id": "conv-1",
        "user_message_id": "um-1",
        "assistant_message_id": "am-1",
        "term_id": "term-1",
        "user_id": "user-1",
    }
    with patch("app.use_cases.chat_orchestration.run_turn") as mock_uc:
        handler(payload)
    mock_uc.assert_called_once()
