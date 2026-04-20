"""AG-032 / AG-032+AG-033：``chat_orchestration.build_messages`` 与 token 预算裁剪。"""
from __future__ import annotations

import pytest

from app.use_cases.chat_orchestration import (
    CHAT_SYSTEM_DISCLAIMER_ZH,
    build_messages,
    total_tokens_for_messages,
    trim_messages_to_token_budget,
)


def test_build_messages_minimal() -> None:
    msgs = build_messages(user_content="  Hello  ", term_id="term-1")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert "term_id: term-1" in msgs[0]["content"]
    assert CHAT_SYSTEM_DISCLAIMER_ZH in msgs[0]["content"]
    assert msgs[1] == {"role": "user", "content": "Hello"}


def test_build_messages_with_history_and_context() -> None:
    msgs = build_messages(
        user_content="Next",
        term_id="t1",
        history=[
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello back"},
        ],
        context_type="topic",
        context_ref_id="topic-9",
    )
    assert msgs[0]["role"] == "system"
    assert "关联课题" in msgs[0]["content"]
    assert "topic-9" in msgs[0]["content"]
    assert msgs[1:] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello back"},
        {"role": "user", "content": "Next"},
    ]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"user_content": "", "term_id": "t"}, "user_content"),
        ({"user_content": "   ", "term_id": "t"}, "user_content"),
        ({"user_content": "x", "term_id": ""}, "term_id"),
        ({"user_content": "x", "term_id": "  "}, "term_id"),
    ],
)
def test_build_messages_rejects_invalid(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        build_messages(**kwargs)


def test_build_messages_rejects_bad_history_role() -> None:
    with pytest.raises(ValueError, match="history\\[0\\]"):
        build_messages(
            user_content="x",
            term_id="t",
            history=[{"role": "system", "content": "nope"}],
        )


def test_build_messages_rejects_empty_history_content() -> None:
    with pytest.raises(ValueError, match="history\\[0\\]"):
        build_messages(
            user_content="x",
            term_id="t",
            history=[{"role": "user", "content": "  "}],
        )


def test_build_messages_trims_old_history_when_budget_small() -> None:
    long_a = "A" * 200
    long_b = "B" * 200
    msgs = build_messages(
        user_content="final",
        term_id="term-z",
        history=[
            {"role": "user", "content": "old-user"},
            {"role": "assistant", "content": long_a},
            {"role": "user", "content": "mid-user"},
            {"role": "assistant", "content": long_b},
        ],
        max_context_tokens=80,
    )
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == "final"
    assert total_tokens_for_messages(msgs) <= 80
    joined = " ".join(m["content"] for m in msgs[1:-1])
    assert "old-user" not in joined


def test_trim_messages_rejects_bad_shape() -> None:
    with pytest.raises(ValueError, match="leading system"):
        trim_messages_to_token_budget(
            [{"role": "user", "content": "x"}], max_tokens=10
        )
