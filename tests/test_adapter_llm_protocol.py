"""AG-027：``LlmClientProtocol`` 与无 HTTP mock 客户端可替换性。"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from flask import Flask

from app.adapter.llm import (
    LlmConfigurationError,
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


@pytest.fixture(autouse=True)
def _restore_default_client() -> None:
    from app.adapter import llm as llm_module

    original = llm_module._default_client
    try:
        yield
    finally:
        llm_module._default_client = original


def test_mock_llm_client_is_protocol_compatible() -> None:
    c = MockLlmClient()
    assert isinstance(c, LlmClientProtocol)


def test_mock_llm_client_returns_topic_selection_chat_answer() -> None:
    c = MockLlmClient()

    out = c.complete(
        [
            {"role": "system", "content": "你是毕业设计领域的辅助助手。"},
            {"role": "user", "content": "我现在要开始毕业设计选题，应该怎样判断一个课题是否适合自己？"},
        ],
        term_id="term-2026-spring",
    )

    assert isinstance(out, dict)
    assert "兴趣方向" in out["content"]
    assert "能力基础" in out["content"]
    assert "课题边界" in out["content"]
    assert "导师沟通" in out["content"]


def test_mock_llm_client_returns_follow_up_literature_chat_answer() -> None:
    c = MockLlmClient()

    out = c.complete(
        [
            {"role": "system", "content": "你是毕业设计领域的辅助助手。"},
            {"role": "user", "content": "我现在要开始毕业设计选题，应该怎样判断一个课题是否适合自己？"},
            {"role": "assistant", "content": "可以从兴趣方向、能力基础、课题边界等角度判断。"},
            {"role": "user", "content": "读完《毕业设计与双向选择刍议》后，我在选择导师和课题时应该注意什么？"},
        ],
        term_id="term-2026-spring",
    )

    assert isinstance(out, dict)
    assert "不要只看题目名称" in out["content"]
    assert "导师课题" in out["content"]
    assert "志愿顺序" in out["content"]
    assert "自身条件" in out["content"]


def test_mock_llm_client_returns_document_summary_shape() -> None:
    c = MockLlmClient()

    out = c.complete(
        [
            {
                "role": "user",
                "content": (
                    "Aggregate chunk summaries for document_task_id=demo-doc. "
                    "Produce a concise final summary followed by bullet points.\n\n"
                    "Chunk summaries:\n"
                    "- 文章提出在毕业设计中引入竞争机制，实行导师和学生双向选择。\n"
                    "- 学生先根据导师课题填报志愿，导师再按志愿选择学生，落选者由领导小组调剂。"
                ),
            }
        ],
        term_id="term-2026-spring",
    )

    assert isinstance(out, dict)
    assert "双向选择" in out["content"]
    assert "导师" in out["content"]
    assert "学生" in out["content"]
    assert "- " in out["content"]


def test_mock_llm_client_returns_fixed_document_summary_for_demo_upload() -> None:
    c = MockLlmClient()

    out = c.complete(
        [
            {
                "role": "user",
                "content": (
                    "Aggregate chunk summaries for document_task_id=demo-doc. "
                    "Produce a concise final summary followed by bullet points.\n\n"
                    "Chunk summaries:\n"
                    "- 任意分块摘要。"
                ),
            }
        ],
        term_id="term-2026-spring",
    )

    assert isinstance(out, dict)
    assert out["content"].startswith("该文献围绕毕业设计环节中的导师与学生双向选择机制展开")
    assert "问题背景：传统毕业设计分配方式以班主任或院系安排为主" in out["content"]
    assert "主要做法：先由导师公布毕业设计课题及内容概要" in out["content"]
    assert "作用分析：双向选择能够促使导师提高课题质量" in out["content"]
    assert "结论观点：在具备导师队伍和评优制度等条件时" in out["content"]
    assert "关键词：毕业设计；竞争机制；双向选择；导师选择；学生志愿" in out["content"]
    assert "答辩" not in out["content"]
    assert "本系统" not in out["content"]


def test_set_llm_client_switches_module_complete() -> None:
    stub = MagicMock(spec=LlmClient)
    stub.complete.return_value = {"content": "ok"}
    set_llm_client(stub)
    try:
        out = complete([{"role": "user", "content": "x"}])
        assert out == {"content": "ok"}
        stub.complete.assert_called_once()
    finally:
        set_llm_client(None)


def test_configure_llm_client_from_environment_returns_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_HTTP_API_KEY", "secret-key")
    monkeypatch.setenv("LLM_HTTP_BASE_URL", "https://api.example.invalid/v1")
    monkeypatch.setenv("LLM_HTTP_MODEL", "demo-model")

    client = configure_llm_client_from_environment(default_to_mock=False)

    assert isinstance(client, OpenAiCompatibleHttpClient)
    assert get_llm_client() is client


def test_configure_llm_client_from_environment_accepts_openai_alias_env_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LLM_HTTP_API_KEY", raising=False)
    monkeypatch.delenv("LLM_HTTP_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_HTTP_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "alias-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://alias.example.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "alias-model")

    client = configure_llm_client_from_environment(default_to_mock=False)

    assert isinstance(client, OpenAiCompatibleHttpClient)
    assert client._base == "https://alias.example.invalid/v1/"  # noqa: SLF001 — 引导兼容面回归保护
    assert client._model == "alias-model"  # noqa: SLF001 — 引导兼容面回归保护
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


def test_get_llm_client_accepts_protocol_only_client_from_app_extensions() -> None:
    class _ProtocolOnlyClient:
        def complete(self, messages, /, **kwargs):
            _ = (messages, kwargs)
            return {"content": "protocol-complete"}

        def invoke_chat(self, messages, /, **kwargs):
            _ = (messages, kwargs)
            return {"content": "protocol-invoke"}

        def chat(self, *args, **kwargs):
            _ = (args, kwargs)
            return {"content": "protocol-chat"}

        def call(self, *, messages, conversation_id, term_id, **kwargs):
            _ = (messages, conversation_id, term_id, kwargs)
            return {"content": "protocol-call"}

    app = Flask(__name__)
    app.extensions["llm_client"] = _ProtocolOnlyClient()

    with app.app_context():
        client = get_llm_client()
        assert isinstance(client, LlmClientProtocol)
        assert complete([{"role": "user", "content": "x"}]) == {"content": "protocol-complete"}
        assert invoke_chat([{"role": "user", "content": "x"}]) == {"content": "protocol-invoke"}
        assert call(
            messages=[{"role": "user", "content": "x"}],
            conversation_id="conv-1",
            term_id="term-1",
        ) == {"content": "protocol-call"}


def test_complete_without_explicit_default_client_raises_configuration_error() -> None:
    set_llm_client(None)

    with pytest.raises(LlmConfigurationError, match="default LLM client"):
        complete([{"role": "user", "content": "x"}])


def test_create_app_dev_bootstrap_uses_app_config_as_authoritative_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import Config

    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_HTTP_API_KEY", "dev-http-key")
    monkeypatch.setenv("LLM_HTTP_BASE_URL", "https://dev.example.invalid/v1")
    monkeypatch.setenv("LLM_HTTP_MODEL", "dev-model")
    monkeypatch.setattr(Config, "LLM_PROVIDER", "mock", raising=False)
    monkeypatch.setattr(Config, "LLM_HTTP_API_KEY", "", raising=False)
    monkeypatch.setattr(Config, "LLM_HTTP_BASE_URL", "", raising=False)
    monkeypatch.setattr(Config, "LLM_HTTP_MODEL", "", raising=False)

    app = create_app()

    assert app.config["LLM_PROVIDER"] == "openai_compatible"
    assert app.config["LLM_HTTP_API_KEY"] == "dev-http-key"
    assert app.config["LLM_HTTP_BASE_URL"] == "https://dev.example.invalid/v1"
    assert app.config["LLM_HTTP_MODEL"] == "dev-model"
    assert isinstance(app.extensions["llm_client"], OpenAiCompatibleHttpClient)


def test_create_app_registration_does_not_replace_global_default_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app

    default_stub = MagicMock(spec=LlmClient)
    set_llm_client(default_stub)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    try:
        app = create_app()

        assert get_llm_client() is default_stub
        with app.app_context():
            assert get_llm_client() is app.extensions["llm_client"]
    finally:
        set_llm_client(None)


def test_create_app_does_not_enable_no_context_llm_calls_without_explicit_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app

    set_llm_client(None)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    create_app()

    with pytest.raises(LlmConfigurationError, match="default LLM client"):
        complete([{"role": "user", "content": "x"}])
