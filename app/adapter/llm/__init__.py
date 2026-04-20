"""LLM adapter：协议、基类与模块级入口（默认 mock，无厂商 HTTP）。"""

from __future__ import annotations

from typing import Any

from app.adapter.llm.client import LlmClient, MockLlmClient
from app.adapter.llm.protocol import LlmClientProtocol

# 默认进程内实现：可测试替换为厂商客户端实例
_default_client: LlmClient = MockLlmClient()


def get_llm_client() -> LlmClient:
    """返回当前默认客户端；集成测试可 patch 本函数注入 stub。"""
    return _default_client


def set_llm_client(client: LlmClient) -> None:
    """显式切换实现（例如单测或 AG-028 注册厂商客户端）。"""
    global _default_client
    _default_client = client


def complete(
    messages: list[dict[str, Any]],
    /,
    **kwargs: Any,
) -> Any:
    """UC/编排常用入口，与 ``chat_orchestration`` 对齐。"""
    return _default_client.complete(messages, **kwargs)


def invoke_chat(
    messages: list[dict[str, Any]],
    /,
    **kwargs: Any,
) -> Any:
    """与 ``complete`` 同语义的可选名。"""
    return _default_client.invoke_chat(messages, **kwargs)


def call(
    *,
    messages: list[dict[str, Any]],
    conversation_id: str,
    term_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """统一高层调用；默认委托 ``MockLlmClient.call``。"""
    return _default_client.call(
        messages=messages,
        conversation_id=conversation_id,
        term_id=term_id,
        **kwargs,
    )


__all__ = ("LlmClient", "LlmClientProtocol", "complete", "invoke_chat", "call")
