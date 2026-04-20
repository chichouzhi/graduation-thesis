"""AG-028：``OpenAiCompatibleHttpClient`` 单文件 HTTP 实现（mock 网络）。"""
from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.adapter.llm.openai_compatible_http import (
    K_RETRIES,
    LlmTransportError,
    OpenAiCompatibleHttpClient,
    openai_compatible_client_from_environ,
)
from app.common.error_envelope import ErrorCode


def _json_response(obj: object) -> MagicMock:
    raw = json.dumps(obj).encode("utf-8")
    m = MagicMock()
    enter = MagicMock()
    enter.read.return_value = raw
    m.__enter__.return_value = enter
    m.__exit__.return_value = None
    return m


def test_complete_returns_content_from_message_shape() -> None:
    client = OpenAiCompatibleHttpClient(
        base_url="https://example.invalid/v1",
        api_key="sk-test",
        model="m1",
        max_retries=0,
    )
    body = {"choices": [{"message": {"content": "hi"}}]}
    with patch(
        "app.adapter.llm.openai_compatible_http.urllib.request.urlopen",
        return_value=_json_response(body),
    ):
        out = client.complete([{"role": "user", "content": "ping"}])
    assert out == {"content": "hi"}


def test_429_after_retries_raises_llm_rate_limited() -> None:
    client = OpenAiCompatibleHttpClient(
        base_url="https://example.invalid/v1",
        api_key="sk-test",
        model="m1",
        max_retries=1,
    )
    err = urllib.error.HTTPError(
        "https://example.invalid/v1/chat/completions",
        429,
        "Too Many",
        hdrs=None,
        fp=BytesIO(b"{}"),
    )
    with (
        patch(
            "app.adapter.llm.openai_compatible_http.urllib.request.urlopen",
            side_effect=[err, err],
        ),
        patch("app.adapter.llm.openai_compatible_http._sleep_backoff"),
    ):
        with pytest.raises(LlmTransportError) as ei:
            client.complete([{"role": "user", "content": "x"}])
    assert ei.value.error_code == ErrorCode.LLM_RATE_LIMITED.value


def test_retries_then_success() -> None:
    client = OpenAiCompatibleHttpClient(
        base_url="https://example.invalid/v1",
        api_key="sk-test",
        model="m1",
        max_retries=2,
    )
    err503 = urllib.error.HTTPError(
        "https://example.invalid/v1/chat/completions",
        503,
        "Bad",
        hdrs=None,
        fp=BytesIO(b"{}"),
    )
    ok = _json_response({"choices": [{"message": {"content": "ok"}}]})
    with (
        patch(
            "app.adapter.llm.openai_compatible_http.urllib.request.urlopen",
            side_effect=[err503, ok],
        ),
        patch("app.adapter.llm.openai_compatible_http._sleep_backoff"),
    ):
        out = client.complete([{"role": "user", "content": "x"}])
    assert out["content"] == "ok"


def test_k_retries_constant_matches_spec() -> None:
    assert K_RETRIES == 3


def test_openai_compatible_client_from_environ_none_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_HTTP_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert openai_compatible_client_from_environ() is None


def test_openai_compatible_client_from_environ_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_HTTP_API_KEY", " k ")
    monkeypatch.setenv("LLM_HTTP_BASE_URL", "https://x/v1/")
    monkeypatch.setenv("LLM_HTTP_MODEL", "mm")
    c = openai_compatible_client_from_environ()
    assert c is not None
    assert c._model == "mm"  # noqa: SLF001 — 工厂白盒断言
