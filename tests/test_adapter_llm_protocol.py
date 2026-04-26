"""AG-027：``LlmClientProtocol`` 与无 HTTP mock 客户端可替换性。"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.adapter.llm import (
    LlmClientProtocol,
    MockLlmClient,
    complete,
    configure_llm_client_from_environment,
    get_llm_client,
    set_llm_client,
)
from app.adapter.llm.client import LlmClient
from app.adapter.llm.openai_compatible_http import OpenAiCompatibleHttpClient


def test_mock_llm_client_is_protocol_compatible() -> None:
    c = MockLlmClient()
    assert isinstance(c, LlmClientProtocol)


def test_set_llm_client_switches_module_complete() -> None:
    stub = MagicMock(spec=LlmClient)
    stub.complete.return_value = {"content": "ok"}
    set_llm_client(stub)
    try:
        out = complete([{"role": "user", "content": "x"}])
        assert out == {"content": "ok"}
        stub.complete.assert_called_once()
    finally:
        set_llm_client(MockLlmClient())


def test_configure_llm_client_from_environment_returns_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_HTTP_API_KEY", "secret-key")
    monkeypatch.setenv("LLM_HTTP_BASE_URL", "https://api.example.invalid/v1")
    monkeypatch.setenv("LLM_HTTP_MODEL", "demo-model")

    client = configure_llm_client_from_environment(default_to_mock=False)

    assert isinstance(client, OpenAiCompatibleHttpClient)
    assert get_llm_client() is client


def test_configure_llm_client_from_environment_requires_explicit_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_HTTP_API_KEY", raising=False)
    monkeypatch.delenv("LLM_HTTP_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_HTTP_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="LLM_PROVIDER"):
        configure_llm_client_from_environment(default_to_mock=False)
