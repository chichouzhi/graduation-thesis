from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.task.keyword_jobs import KeywordJobPayload, handle_keyword_job


def _payload() -> dict[str, object]:
    return {
        "keyword_job_id": "kj-1",
        "topic_id": "tp-1",
        "term_id": "tm-1",
        "text_snapshot": "snapshot",
        "requested_by_user_id": "u-1",
        "request_id": "req-1",
    }


def test_keyword_payload_requires_fields() -> None:
    p = _payload()
    p["topic_id"] = " "
    with pytest.raises(ValueError, match="topic_id"):
        KeywordJobPayload.from_mapping(p)


def test_keyword_payload_accepts_optional_retry_fields() -> None:
    p = _payload()
    p["retry_count"] = "2"
    p["max_attempts"] = 5
    typed = KeywordJobPayload.from_mapping(p)
    assert typed.retry_count == 2
    assert typed.max_attempts == 5


def test_handle_keyword_job_calls_uc_and_writes_portrait(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_payloads: list[dict[str, object]] = []

    def fake_uc(payload: dict[str, object]) -> dict[str, str]:
        captured_payloads.append(payload)
        return {"content": "Python\nFlask\n"}

    topic = SimpleNamespace(
        portrait_json=None,
        llm_keyword_job_id=None,
        llm_keyword_job_status=None,
    )
    session = SimpleNamespace(
        get=lambda _model, _id: topic,
        commit=MagicMock(),
    )

    monkeypatch.setattr("app.use_cases.topic_keywords.run_keyword_extraction_from_payload", fake_uc)
    from app.extensions import db

    monkeypatch.setattr(db, "session", session, raising=False)

    keywords = handle_keyword_job(_payload())
    assert keywords == ["Python", "Flask"]
    assert captured_payloads and captured_payloads[0]["keyword_job_id"] == "kj-1"
    assert topic.portrait_json is not None
    assert topic.portrait_json["keywords"] == ["Python", "Flask"]
    assert topic.llm_keyword_job_id == "kj-1"
    assert topic.llm_keyword_job_status.value == "done"
    session.commit.assert_called_once()


def test_handle_keyword_job_raises_when_topic_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.use_cases.topic_keywords.run_keyword_extraction_from_payload",
        lambda _payload: {"content": "A"},
    )
    from app.extensions import db

    session = SimpleNamespace(get=lambda _m, _i: None, commit=MagicMock())
    monkeypatch.setattr(db, "session", session, raising=False)
    with pytest.raises(ValueError, match="topic not found"):
        handle_keyword_job(_payload())


def test_handle_keyword_job_writes_failed_when_uc_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_payload: dict[str, object]) -> dict[str, str]:
        raise RuntimeError("llm timeout")

    monkeypatch.setattr("app.use_cases.topic_keywords.run_keyword_extraction_from_payload", boom)
    from app.extensions import db

    topic = SimpleNamespace(
        portrait_json={"keywords": ["existing"], "extracted_at": "2026-01-01T00:00:00Z"},
        llm_keyword_job_id=None,
        llm_keyword_job_status=None,
    )
    session = SimpleNamespace(get=lambda _m, _i: topic, commit=MagicMock())
    monkeypatch.setattr(db, "session", session, raising=False)

    with pytest.raises(RuntimeError, match="llm timeout"):
        handle_keyword_job(_payload())
    assert topic.llm_keyword_job_id == "kj-1"
    assert topic.llm_keyword_job_status.value == "failed"
    assert topic.portrait_json["error_code"] == "DOMAIN_ERROR"
    assert topic.portrait_json["keywords"] == ["existing"]
    assert topic.portrait_json["extracted_at"] == "2026-01-01T00:00:00Z"


def test_handle_keyword_job_failure_merge_portrait_when_portrait_not_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_payload: dict[str, object]) -> dict[str, str]:
        raise RuntimeError("llm timeout")

    monkeypatch.setattr("app.use_cases.topic_keywords.run_keyword_extraction_from_payload", boom)
    from app.extensions import db

    topic = SimpleNamespace(
        portrait_json=None,
        llm_keyword_job_id=None,
        llm_keyword_job_status=None,
    )
    session = SimpleNamespace(get=lambda _m, _i: topic, commit=MagicMock())
    monkeypatch.setattr(db, "session", session, raising=False)

    with pytest.raises(RuntimeError, match="llm timeout"):
        handle_keyword_job(_payload())
    assert topic.portrait_json == {
        "error_code": "DOMAIN_ERROR",
        "error_message": "llm timeout",
    }
