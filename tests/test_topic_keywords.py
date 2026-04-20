"""AG-036：``topic_keywords`` 快照编排与 LLM 调用。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.use_cases.topic_keywords import (
    KEYWORD_SYSTEM_PROMPT_ZH,
    build_keyword_extraction_messages,
    run_keyword_extraction,
    run_keyword_extraction_from_payload,
)


def test_build_keyword_messages_shape() -> None:
    msgs = build_keyword_extraction_messages(
        text_snapshot="  摘要与要求  ",
        topic_id="tp-1",
        term_id="term-1",
    )
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert KEYWORD_SYSTEM_PROMPT_ZH in msgs[0]["content"]
    assert "tp-1" in msgs[1]["content"]
    assert "摘要与要求" in msgs[1]["content"]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"text_snapshot": "", "topic_id": "t", "term_id": "x"}, "text_snapshot"),
        ({"text_snapshot": "a", "topic_id": "", "term_id": "x"}, "topic_id"),
        ({"text_snapshot": "a", "topic_id": "t", "term_id": "  "}, "term_id"),
    ],
)
def test_build_rejects_empty(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        build_keyword_extraction_messages(**kwargs)


def test_run_keyword_extraction_requires_ids() -> None:
    with pytest.raises(ValueError, match="keyword_job_id"):
        run_keyword_extraction(
            keyword_job_id="",
            topic_id="t",
            term_id="term",
            text_snapshot="x",
            requested_by_user_id="u",
        )
    with pytest.raises(ValueError, match="requested_by_user_id"):
        run_keyword_extraction(
            keyword_job_id="j1",
            topic_id="t",
            term_id="term",
            text_snapshot="x",
            requested_by_user_id="  ",
        )


def test_run_keyword_extraction_invokes_llm() -> None:
    with patch("app.adapter.llm.complete", new=MagicMock(return_value={"content": "k1\nk2"})) as m:
        out = run_keyword_extraction(
            keyword_job_id="kj-1",
            topic_id="tp-1",
            term_id="term-1",
            text_snapshot="hello",
            requested_by_user_id="user-1",
            request_id="req-9",
        )
    m.assert_called_once()
    assert out == {"content": "k1\nk2"}
    call_kw = m.call_args.kwargs
    assert call_kw["term_id"] == "term-1"
    assert call_kw["keyword_job_id"] == "kj-1"


def test_run_from_payload() -> None:
    with patch("app.adapter.llm.complete", new=MagicMock(return_value={})):
        run_keyword_extraction_from_payload(
            {
                "keyword_job_id": "a",
                "topic_id": "b",
                "term_id": "c",
                "text_snapshot": "snap",
                "requested_by_user_id": "u",
            }
        )
