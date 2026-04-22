"""§5 it-uc-skip-chain：``chat_jobs`` 消费路径须进入 ``app.use_cases.chat_orchestration``。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.task.chat_jobs import handle_chat_job


def test_handle_chat_job_invokes_use_cases_chat_orchestration(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    assert (root / "app").is_dir()
    import app.use_cases.chat_orchestration as uc

    bm = MagicMock(return_value=[{"role": "user", "content": "x"}])
    rt = MagicMock()
    monkeypatch.setattr(uc, "build_messages", bm)
    monkeypatch.setattr(uc, "run_turn", rt)

    payload = {
        "job_id": "job-uc-1",
        "conversation_id": "conv-uc-1",
        "user_message_id": "um-1",
        "assistant_message_id": "am-1",
        "term_id": "term-uc-1",
        "user_id": "user-uc-1",
        "content": "hello",
        "history": [],
    }
    handle_chat_job(payload)
    bm.assert_called_once()
    rt.assert_called_once()
