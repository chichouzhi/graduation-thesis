"""
验证 use_cases → adapter.llm：对 chat 编排入口打 patch，断言 LLM 网关被调用。

若 `app.adapter.llm` 导出与下列候选均不一致，请在本文件增加新的 patch 目标字符串。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.arch.spy._import_helpers import get_callable_or_fail, import_module_or_fail

LLM_PATCH_TARGETS = (
    "app.adapter.llm.complete",
    "app.adapter.llm.invoke_chat",
    "app.adapter.llm.LlmClient.chat",
)

CHAT_UC_RUN_CANDIDATES = ("run_turn", "execute_chat_turn", "generate_assistant_reply")


def test_chat_orchestration_invokes_llm_adapter():
    ch = import_module_or_fail("app.use_cases.chat_orchestration")
    run = get_callable_or_fail(ch, *CHAT_UC_RUN_CANDIDATES)

    last_err: Exception | None = None
    for target in LLM_PATCH_TARGETS:
        try:
            with patch(target, new=MagicMock()) as mock_llm:
                run(
                    conversation_id="conv-1",
                    messages=[{"role": "user", "content": "hi"}],
                    term_id="term-1",
                )
            mock_llm.assert_called()
            return
        except Exception as exc:  # noqa: BLE001 — 探测可用 patch 与签名
            last_err = exc
            continue

    pytest.fail(
        "未能以任一 LLM_PATCH_TARGETS 完成 patch 并断言调用；"
        f"最后错误: {last_err!r}；请扩展 LLM_PATCH_TARGETS 或修正 run() 参数。"
    )
