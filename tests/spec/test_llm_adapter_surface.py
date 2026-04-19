"""LLM 适配器契约：call() 在 Worker/UC 栈中须产生可序列化结果（非裸 None）。"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.contract


def test_llm_call_returns_non_trivial_result() -> None:
    from app.adapter.llm import call

    out = call(
        messages=[{"role": "user", "content": "ping"}],
        conversation_id="conv-1",
        term_id="term-1",
    )
    assert out is not None, "call() 不得仅返回 None；至少返回占位结构（如 {\"content\": \"\"}）"
    assert isinstance(out, dict), "call() 应返回 dict 或统一 DTO 的 model_dump()，便于序列化与断言"
    assert "content" in out or "text" in out, "响应须暴露 content 或 text 字段之一"
