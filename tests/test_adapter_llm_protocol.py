"""AG-027：``LlmClientProtocol`` 与无 HTTP mock 客户端可替换性。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.adapter.llm import LlmClientProtocol, MockLlmClient, complete, set_llm_client
from app.adapter.llm.client import LlmClient


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
