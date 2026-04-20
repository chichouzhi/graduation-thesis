"""LLM 客户端抽象基类与无厂商 HTTP 的默认 mock 实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LlmClient(ABC):
    """具体厂商客户端（AG-028+）与单元测试 mock 的共同基类。"""

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> Any:
        """子类实现真实或假定的生成逻辑。"""

    def invoke_chat(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> Any:
        return self.complete(messages, **kwargs)

    def chat(self, *args: Any, **kwargs: Any) -> Any:
        """Spy 与旧调用约定：首参为 messages 列表时转调 ``complete``。"""
        if args and isinstance(args[0], list):
            return self.complete(args[0], **kwargs)
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            rest = {k: v for k, v in kwargs.items() if k != "messages"}
            return self.complete(messages, **rest)
        return self.complete([], **kwargs)

    def call(
        self,
        *,
        messages: list[dict[str, Any]],
        conversation_id: str,
        term_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """默认将上下文关键字传入 ``complete``；返回可序列化 dict。"""
        out = self.complete(
            messages,
            conversation_id=conversation_id,
            term_id=term_id,
            **kwargs,
        )
        if isinstance(out, dict):
            return out
        return {"content": str(out)}


class MockLlmClient(LlmClient):
    """无外部 HTTP：占位文本，满足 contract 与 ``test_llm_adapter_surface``。"""

    def complete(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = (messages, kwargs)
        return {"content": ""}
