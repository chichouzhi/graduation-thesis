"""AG-027：``LlmClientProtocol`` 与无 HTTP mock 客户端可替换性。"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from flask import Flask

from app.adapter.llm import (
    LlmClientProtocol,
    MockLlmClient,
    call,
    complete,
    configure_llm_client_from_environment,
    get_llm_client,
    invoke_chat,
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


def test_get_llm_client_prefers_current_app_extension_client() -> None:
    default_stub = MagicMock(spec=LlmClient)
    app_stub = MagicMock(spec=LlmClient)
    app_stub.complete.return_value = {"content": "app"}
    app_stub.invoke_chat.return_value = {"content": "app-invoke"}
    app_stub.call.return_value = {"content": "app-call"}

    set_llm_client(default_stub)
    app = Flask(__name__)
    app.extensions["llm_client"] = app_stub

    try:
        with app.app_context():
            assert get_llm_client() is app_stub
            assert complete([{"role": "user", "content": "x"}]) == {"content": "app"}
            assert invoke_chat([{"role": "user", "content": "x"}]) == {"content": "app-invoke"}
            assert call(
                messages=[{"role": "user", "content": "x"}],
                conversation_id="conv-1",
                term_id="term-1",
            ) == {"content": "app-call"}
    finally:
        set_llm_client(MockLlmClient())

    default_stub.complete.assert_not_called()
    default_stub.invoke_chat.assert_not_called()
    default_stub.call.assert_not_called()
    app_stub.complete.assert_called_once()
    app_stub.invoke_chat.assert_called_once()
    app_stub.call.assert_called_once()
