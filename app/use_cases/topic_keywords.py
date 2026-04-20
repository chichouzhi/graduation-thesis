"""课题技术关键词 LLM 编排：仅 Worker 路径调用 ``adapter.llm``（与 R-SVC-LLM / W4 一致）。

载荷形状对齐 ``contract.yaml`` → ``KeywordJobPayload``；解析/落库由 ``task/keyword_jobs`` 等后续环节完成。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

KEYWORD_SYSTEM_PROMPT_ZH = (
    "你是毕业设计课题管理系统中的关键词抽取助手。"
    "请仅根据给定的课题文本快照，列出与课题相关的技术关键词。"
    "输出要求：每行一个关键词；不要编号；不要多余解释；使用与课题语言一致的书写。"
)


def build_keyword_extraction_messages(
    *,
    text_snapshot: str,
    topic_id: str,
    term_id: str,
) -> list[dict[str, str]]:
    """由快照与标识组装 OpenAI 风格 ``messages``（无 IO、无 LLM）。"""
    body = (text_snapshot or "").strip()
    if not body:
        raise ValueError("text_snapshot must be non-empty")
    tid = (topic_id or "").strip()
    if not tid:
        raise ValueError("topic_id must be non-empty")
    term = (term_id or "").strip()
    if not term:
        raise ValueError("term_id must be non-empty")

    user_lines = [
        f"课题 topic_id: {tid}",
        f"学期 term_id: {term}",
        "",
        "--- 课题文本快照 ---",
        body,
    ]
    return [
        {"role": "system", "content": KEYWORD_SYSTEM_PROMPT_ZH},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


def run_keyword_extraction(
    *,
    keyword_job_id: str,
    topic_id: str,
    term_id: str,
    text_snapshot: str,
    requested_by_user_id: str,
    request_id: str | None = None,
) -> Any:
    """消费 ``KeywordJobPayload`` 语义，调用 LLM 生成关键词相关输出（原始模型结果）。"""
    jid = (keyword_job_id or "").strip()
    if not jid:
        raise ValueError("keyword_job_id must be non-empty")
    uid = (requested_by_user_id or "").strip()
    if not uid:
        raise ValueError("requested_by_user_id must be non-empty")

    messages = build_keyword_extraction_messages(
        text_snapshot=text_snapshot,
        topic_id=topic_id,
        term_id=term_id,
    )
    from app.adapter import llm as llm_mod

    return llm_mod.complete(
        messages,
        term_id=term_id,
        keyword_job_id=jid,
        topic_id=topic_id,
        requested_by_user_id=uid,
        request_id=request_id,
    )


def run_keyword_extraction_from_payload(payload: Mapping[str, Any]) -> Any:
    """从类 ``KeywordJobPayload`` 的 mapping 调用 :func:`run_keyword_extraction`。"""
    return run_keyword_extraction(
        keyword_job_id=str(payload["keyword_job_id"]),
        topic_id=str(payload["topic_id"]),
        term_id=str(payload["term_id"]),
        text_snapshot=str(payload["text_snapshot"]),
        requested_by_user_id=str(payload["requested_by_user_id"]),
        request_id=(None if payload.get("request_id") is None else str(payload["request_id"])),
    )
