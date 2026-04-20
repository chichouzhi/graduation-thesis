"""AG-031：``adapter.nlp`` Jieba 分词封装。"""
from __future__ import annotations

from app.adapter.nlp import tokenize


def test_tokenize_empty() -> None:
    assert tokenize("") == []
    assert tokenize("   \n\t  ") == []


def test_tokenize_chinese_yields_tokens() -> None:
    out = tokenize("我爱北京天安门")
    assert isinstance(out, list)
    assert all(isinstance(x, str) for x in out)
    assert len(out) >= 2
    assert "北京" in out or "天安门" in out or "爱" in out
