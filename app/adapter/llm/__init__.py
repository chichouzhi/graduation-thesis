"""LLM adapter：协议、基类与模块级入口（默认 mock，无厂商 HTTP）。"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from flask import current_app, has_app_context

from app.adapter.llm.client import LlmClient, MockLlmClient
from app.adapter.llm.openai_compatible_http import openai_compatible_client_from_environ
from app.adapter.llm.protocol import LlmClientProtocol

# 默认进程内实现：可测试替换为厂商客户端实例
_default_client: LlmClient | None = None


class LlmConfigurationError(RuntimeError):
    """LLM 运行时配置缺失或非法。"""


def _normalize_provider(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _string_value(values: Mapping[str, object] | None, key: str) -> str:
    if values is None:
        return ""
    value = values.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def get_llm_client() -> LlmClient:
    """返回当前默认客户端；集成测试可 patch 本函数注入 stub。"""
    if has_app_context():
        client = current_app.extensions.get("llm_client")
        if isinstance(client, LlmClientProtocol):
            return client
    if _default_client is None:
        raise LlmConfigurationError(
            "No default LLM client configured for out-of-context usage; "
            "use an app context or call set_llm_client(...) explicitly."
        )
    return _default_client


def set_llm_client(client: LlmClient | None) -> None:
    """显式切换默认实现；``None`` 表示清除 no-context 默认客户端。"""
    global _default_client
    _default_client = client


def configure_llm_client_from_environment(
    values: Mapping[str, object] | None = None,
    *,
    default_to_mock: bool = True,
    set_as_default: bool = True,
) -> LlmClient:
    """按运行时环境注册默认 LLM 客户端。"""
    if values is None:
        provider = _normalize_provider(os.environ.get("LLM_PROVIDER", ""))
    else:
        provider = _normalize_provider(_string_value(values, "LLM_PROVIDER"))
    if not provider:
        if default_to_mock:
            client = MockLlmClient()
            if set_as_default:
                set_llm_client(client)
            return client
        raise LlmConfigurationError("LLM_PROVIDER must be configured before bootstrapping the LLM client")

    if provider == "mock":
        client = MockLlmClient()
        if set_as_default:
            set_llm_client(client)
        return client

    if provider == "openai_compatible":
        client = openai_compatible_client_from_environ(values)
        if client is None:
            raise LlmConfigurationError(
                "LLM_PROVIDER=openai_compatible requires LLM_HTTP_API_KEY "
                "(or OPENAI_API_KEY)"
            )
        if set_as_default:
            set_llm_client(client)
        return client

    raise LlmConfigurationError(f"Unsupported LLM_PROVIDER: {provider}")


def complete(
    messages: list[dict[str, Any]],
    /,
    **kwargs: Any,
) -> Any:
    """UC/编排常用入口，与 ``chat_orchestration`` 对齐。"""
    return get_llm_client().complete(messages, **kwargs)


def invoke_chat(
    messages: list[dict[str, Any]],
    /,
    **kwargs: Any,
) -> Any:
    """与 ``complete`` 同语义的可选名。"""
    return get_llm_client().invoke_chat(messages, **kwargs)


def call(
    *,
    messages: list[dict[str, Any]],
    conversation_id: str,
    term_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """统一高层调用；无上下文且未显式配置默认客户端时退回临时 mock。"""
    if has_app_context():
        client = get_llm_client()
    elif _default_client is not None:
        client = _default_client
    else:
        client = MockLlmClient()
    return client.call(
        messages=messages,
        conversation_id=conversation_id,
        term_id=term_id,
        **kwargs,
    )


__all__ = (
    "LlmClient",
    "LlmClientProtocol",
    "complete",
    "invoke_chat",
    "call",
)
