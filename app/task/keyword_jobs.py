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


def _normalize_unique(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in out:
            out.append(text)
    return out


def _topic_analysis_from_snapshot(*, text_snapshot: str, keywords: list[str]) -> dict[str, Any]:
    lines = [line.strip() for line in str(text_snapshot).splitlines() if line.strip()]
    title = lines[0] if lines else (keywords[0] if keywords else "题目")
    source_text = " ".join([str(text_snapshot), " ".join(keywords)]).lower()

    capability_rules = [
        (
            "前端实现与交互设计",
            ["react", "前端", "ui", "界面", "交互", "页面", "workbench"],
        ),
        (
            "后端接口与数据建模",
            ["flask", "python", "后端", "接口", "数据库", "api"],
        ),
        (
            "模型调用与语义分析",
            ["llm", "大模型", "ai", "推荐", "画像", "关键词", "prompt", "语义"],
        ),
        (
            "文档处理与内容理解",
            ["pdf", "文档", "解析", "摘要", "分块"],
        ),
        (
            "异步任务编排与状态流转",
            ["异步", "队列", "任务", "worker", "状态"],
        ),
        (
            "学术写作与实验整理",
            ["论文", "学术", "文献", "实验", "答辩"],
        ),
    ]

    required_capabilities = [
        label
        for label, signals in capability_rules
        if any(signal.lower() in source_text for signal in signals)
    ]
    if not required_capabilities:
        required_capabilities = ["需求分析与阶段推进"]

    keyword_count = len(keywords)
    score = len(required_capabilities)
    score += 1 if keyword_count >= 4 else 0
    score += 1 if len(source_text) > 180 else 0
    score += 1 if len(source_text) > 320 else 0

    if score >= 5:
        difficulty_label = "advanced"
        difficulty_reason = "题目覆盖多个能力域，适合拆成阶段里程碑推进。"
    elif score >= 3:
        difficulty_label = "intermediate"
        difficulty_reason = "题目需要一定的工程整合能力，建议提前规划任务拆分。"
    else:
        difficulty_label = "basic"
        difficulty_reason = "题目边界较清晰，适合按模块逐步实现。"

    suitable_students = []
    if difficulty_label == "advanced":
        suitable_students.append("有完整项目经验、能持续投入的学生")
    if "模型调用与语义分析" in required_capabilities:
        suitable_students.append("对大模型、提示词或推荐解释感兴趣的学生")
    if "前端实现与交互设计" in required_capabilities:
        suitable_students.append("希望做出可答辩展示交互界面的学生")
    if "后端接口与数据建模" in required_capabilities:
        suitable_students.append("熟悉接口联调和数据组织的学生")
    if not suitable_students:
        suitable_students.append("愿意按阶段推进并完成基础功能的学生")

    risks = []
    if len(required_capabilities) > 2:
        risks.append("跨模块较多，建议先固定边界再实现主链路。")
    if "异步任务编排与状态流转" in required_capabilities:
        risks.append("异步状态需要明确终态回写与失败兜底。")
    if "模型调用与语义分析" in required_capabilities:
        risks.append("推荐结果需要可解释字段，避免黑盒输出。")
    if not risks:
        risks.append("需求边界较清晰，但仍需注意阶段拆分。")

    summary_seed = keywords[0] if keywords else title
    summary = f"围绕 {summary_seed} 形成题目画像，方便后续推荐与答辩展示。"
    if title != summary_seed:
        summary = f"围绕 {title} 形成题目画像，方便后续推荐与答辩展示。"

    return {
        "keywords": _normalize_unique(keywords),
        "difficulty_label": difficulty_label,
        "difficulty_reason": difficulty_reason,
        "required_capabilities": _normalize_unique(required_capabilities),
        "suitable_students": _normalize_unique(suitable_students),
        "risks": _normalize_unique(risks),
        "summary": summary,
        "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _write_topic_portrait(payload: KeywordJobPayload, keywords: list[str], text_snapshot: str) -> None:
    from app.extensions import db
    from app.topic.model import Topic, TopicKeywordJobStatus

    topic = db.session.get(Topic, payload.topic_id)
    if topic is None:
        raise ValueError(f"topic not found: {payload.topic_id}")
    topic.portrait_json = _topic_analysis_from_snapshot(text_snapshot=text_snapshot, keywords=keywords)
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
        _write_topic_portrait(typed, keywords, typed.text_snapshot)
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
