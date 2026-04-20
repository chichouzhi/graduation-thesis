"""AG-026：``app.adapter`` 四子包可导入且根包不隐式重导出业务符号。"""
from __future__ import annotations

import importlib

import pytest


def test_adapter_subpackages_importable() -> None:
    llm = importlib.import_module("app.adapter.llm")
    pdf = importlib.import_module("app.adapter.pdf")
    nlp = importlib.import_module("app.adapter.nlp")
    storage = importlib.import_module("app.adapter.storage")

    assert hasattr(llm, "call")
    assert hasattr(pdf, "parse_document")
    assert hasattr(nlp, "tokenize")
    assert hasattr(storage, "put_bytes")
    assert hasattr(storage, "get_bytes")


def test_adapter_root_public_submodules_only_in_all() -> None:
    import app.adapter as root

    assert set(root.__all__) == {"llm", "pdf", "nlp", "storage"}


@pytest.mark.parametrize(
    "mod_name,expected",
    [
        ("app.adapter.llm", {"LlmClient", "LlmClientProtocol", "complete", "invoke_chat", "call"}),
        ("app.adapter.pdf", {"PdfParseError", "parse_document"}),
        ("app.adapter.nlp", {"tokenize"}),
        ("app.adapter.storage", {"put_bytes", "get_bytes"}),
    ],
)
def test_adapter_subpackage_all_matches_documented_surface(mod_name: str, expected: set[str]) -> None:
    mod = importlib.import_module(mod_name)
    assert set(getattr(mod, "__all__", ())) == expected


def test_adapter_root_does_not_reexport_subpackage_symbols() -> None:
    import app.adapter as root

    assert not hasattr(root, "call")
    assert not hasattr(root, "parse_document")
    assert not hasattr(root, "tokenize")
    assert not hasattr(root, "put_bytes")
    assert not hasattr(root, "get_bytes")
    assert not hasattr(root, "LlmClient")


def test_adapter_submodule_import_from_root_matches_layout() -> None:
    """``from app.adapter import llm`` 等仅绑定子包，不拉平业务 API。"""
    from app.adapter import llm, nlp, pdf, storage

    assert llm.__name__ == "app.adapter.llm"
    assert pdf.__name__ == "app.adapter.pdf"
    assert nlp.__name__ == "app.adapter.nlp"
    assert storage.__name__ == "app.adapter.storage"
