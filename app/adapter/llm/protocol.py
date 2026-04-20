"""LLM 适配器协议：厂商实现与 mock 均须满足同一结构类型（无 HTTP 亦可替换）。"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LlmClientProtocol(Protocol):
    """编排层可依赖的最小 LLM 客户端契约（Worker 栈内使用）。"""

    def complete(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> Any:
        """给定 OpenAI 风格 messages 列表，返回模型输出（形状由 UC/contract 消费侧约定）。"""
        ...

    def chat(self, *args: Any, **kwargs: Any) -> Any:
        """兼容名；具体实现可委托 ``complete``（供测试 patch ``LlmClient.chat``）。"""
        ...

    def invoke_chat(self, messages: list[dict[str, Any]], /, **kwargs: Any) -> Any:
        """与 ``complete`` 同语义的可选入口名（模块级 ``invoke_chat`` 默认转调）。"""
        ...

    def call(
        self,
        *,
        messages: list[dict[str, Any]],
        conversation_id: str,
        term_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """统一高层入口（含 ``term_id`` 等命名空间）；须返回可 JSON 序列化的 dict。"""
        ...
