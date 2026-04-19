"""Chat 受理契约：create_chat / 发消息路径须返回 pending + job_id（对齐 contract AsyncTaskStatus / PostUserMessageResponse）。"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.contract


def test_create_chat_returns_pending_and_job_id() -> None:
    from app.chat.service.chat_service import create_chat

    out = create_chat(
        conversation_id="conv-contract-1",
        term_id="term-contract-1",
        user_id="user-contract-1",
        content="hello-contract",
    )
    assert isinstance(out, dict), (
        "create_chat 须返回可 JSON 化的受理体（例如 HTTP 202 body 或等价 dict）；"
        "禁止仅返回 ChatService 实例而无 job_id/status"
    )
    assert out.get("status") == "pending", "受理后异步任务状态须为 contract.AsyncTaskStatus=pending"
    job_id = out.get("job_id")
    assert job_id is not None, "必须返回 job_id（contract: PostUserMessageResponse.required）"
    assert str(job_id).strip() != "", "job_id 须为非空字符串"


def test_create_chat_includes_message_placeholders_when_dict() -> None:
    """PostUserMessageResponse 还要求 user_message / assistant_message；实现须一并满足。"""
    from app.chat.service.chat_service import create_chat

    out = create_chat(
        conversation_id="conv-contract-2",
        term_id="term-contract-1",
        user_id="user-contract-1",
        content="hi",
    )
    assert isinstance(out, dict)
    assert "user_message" in out and isinstance(out["user_message"], dict)
    assert "assistant_message" in out and isinstance(out["assistant_message"], dict)
    assert out["assistant_message"].get("status") == "pending"
