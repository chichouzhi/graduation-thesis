"""keyword_jobs consumer: validate payload, call UC, write topic portrait."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class KeywordJobPayload:
    keyword_job_id: str
    topic_id: str
    term_id: str
    text_snapshot: str
    requested_by_user_id: str
    request_id: str | None = None
    retry_count: int | None = None
    max_attempts: int | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "KeywordJobPayload":
        required = (
            "keyword_job_id",
            "topic_id",
            "term_id",
            "text_snapshot",
            "requested_by_user_id",
        )
        normalized: dict[str, str] = {}
        for key in required:
            raw = payload.get(key)
            text = str(raw).strip() if raw is not None else ""
            if not text:
                raise ValueError(f"KeywordJobPayload.{key} must be non-empty")
            normalized[key] = text

        request_id_raw = payload.get("request_id")
        request_id = None if request_id_raw is None else str(request_id_raw).strip() or None
        retry_count_raw = payload.get("retry_count")
        retry_count = None if retry_count_raw is None else int(retry_count_raw)
        max_attempts_raw = payload.get("max_attempts")
        max_attempts = None if max_attempts_raw is None else int(max_attempts_raw)
        return cls(
            keyword_job_id=normalized["keyword_job_id"],
            topic_id=normalized["topic_id"],
            term_id=normalized["term_id"],
            text_snapshot=normalized["text_snapshot"],
            requested_by_user_id=normalized["requested_by_user_id"],
            request_id=request_id,
            retry_count=retry_count,
            max_attempts=max_attempts,
        )


def _extract_keywords(raw: Any) -> list[str]:
    if isinstance(raw, dict):
        content = str(raw.get("content", ""))
    else:
        content = str(raw)
    out: list[str] = []
    for line in content.splitlines():
        k = line.strip()
        if k:
            out.append(k)
    return out


def _write_topic_portrait(payload: KeywordJobPayload, keywords: list[str]) -> None:
    from app.extensions import db
    from app.topic.model import Topic, TopicKeywordJobStatus

    topic = db.session.get(Topic, payload.topic_id)
    if topic is None:
        raise ValueError(f"topic not found: {payload.topic_id}")
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    topic.portrait_json = {"keywords": keywords, "extracted_at": now_utc}
    topic.llm_keyword_job_id = payload.keyword_job_id
    topic.llm_keyword_job_status = TopicKeywordJobStatus.done
    db.session.commit()


def _write_topic_failure(
    payload: KeywordJobPayload,
    *,
    error_code: str,
    error_message: str,
) -> None:
    from app.extensions import db
    from app.topic.model import Topic, TopicKeywordJobStatus

    topic = db.session.get(Topic, payload.topic_id)
    if topic is None:
        return
    portrait_raw = topic.portrait_json
    portrait = dict(portrait_raw) if isinstance(portrait_raw, dict) else {}
    portrait["error_code"] = str(error_code)
    portrait["error_message"] = str(error_message)
    topic.llm_keyword_job_id = payload.keyword_job_id
    topic.llm_keyword_job_status = TopicKeywordJobStatus.failed
    topic.portrait_json = portrait
    db.session.commit()


def handle_keyword_job(payload: dict[str, Any]) -> list[str]:
    from app.use_cases.topic_keywords import run_keyword_extraction_from_payload

    typed = KeywordJobPayload.from_mapping(payload)
    uc_payload = {
        "keyword_job_id": typed.keyword_job_id,
        "topic_id": typed.topic_id,
        "term_id": typed.term_id,
        "text_snapshot": typed.text_snapshot,
        "requested_by_user_id": typed.requested_by_user_id,
        "request_id": typed.request_id,
    }
    try:
        raw = run_keyword_extraction_from_payload(uc_payload)
        keywords = _extract_keywords(raw)
        _write_topic_portrait(typed, keywords)
        return keywords
    except ValueError as exc:
        if "topic not found" in str(exc):
            _write_topic_failure(
                typed,
                error_code="TOPIC_NOT_FOUND",
                error_message=str(exc),
            )
        else:
            _write_topic_failure(
                typed,
                error_code="DOMAIN_ERROR",
                error_message=str(exc),
            )
        raise
    except Exception as exc:
        _write_topic_failure(
            typed,
            error_code="DOMAIN_ERROR",
            error_message=str(exc),
        )
        raise


def run(payload: dict[str, Any]) -> None:
    handle_keyword_job(payload)
