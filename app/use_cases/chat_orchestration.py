"""Chat 编排：无 HTTP 上下文；``build_messages`` 为纯函数（无 IO、无 LLM）。

``run_turn`` 仅在 Worker 路径内调用 ``adapter.llm``（与 R-SYNC-LLM / W4 一致）。

token 级裁剪：与 ``execution_plan`` chat 子任务及 §14.6 引用一致；粗估算法可替换为 tiktoken，
预算来自 ``app.config.Config.CHAT_CONTEXT_TOKEN_BUDGET``（``CHAT_CONTEXT_TOKEN_BUDGET`` 环境变量）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from app.chat.model import ChatJob, Message, MessageAsyncTaskStatus
from app.common.error_envelope import ErrorCode
from app.config import Config
from app.extensions import db

# 与 execution_plan「系统角色与免责声明」对齐
CHAT_SYSTEM_DISCLAIMER_ZH = (
    "你是毕业设计领域的辅助助手。以下回答仅供学习与研究参考，不构成正式学术结论或法律意见。"
)
_TERMINAL_CHAT_JOB_STATUSES = frozenset(
    {
        MessageAsyncTaskStatus.done,
        MessageAsyncTaskStatus.failed,
    }
)


def _context_hint_zh(
    *,
    context_type: str | None,
    context_ref_id: str | None,
) -> str | None:
    if not context_type:
        return None
    ct = context_type.strip().lower()
    if ct == "general":
        return "当前会话模式：通用对话。"
    if ct == "topic":
        ref = context_ref_id or "（未绑定）"
        return f"当前会话模式：关联课题上下文（标识 {ref}）。"
    if ct == "document":
        ref = context_ref_id or "（未绑定）"
        return f"当前会话模式：关联文献任务（标识 {ref}）。"
    return f"当前会话模式：{context_type}。"


def rough_token_estimate(text: str) -> int:
    """对单段文本的 token 数做**上界粗估**（中英混合；可换 tiktoken）。

    规则：ASCII 约 4 字符/token；CJK 约 1～2 字符/token，此处取偏保守权重以便裁剪。
    """
    if not text:
        return 0
    weight = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            weight += 2
        elif ord(ch) < 128:
            weight += 1
        else:
            weight += 2
    return max(1, (weight + 3) // 4)


def total_tokens_for_messages(messages: Sequence[Mapping[str, str]]) -> int:
    """``messages`` 列表的总粗估 token（每条含 role + content）。"""
    total = 0
    for m in messages:
        role = str(m.get("role", ""))
        content = str(m.get("content", ""))
        total += rough_token_estimate(f"{role}\n{content}")
    return total


def trim_messages_to_token_budget(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
) -> list[dict[str, str]]:
    """将 OpenAI 风格 ``messages`` 裁到不超过 ``max_tokens``（粗估）。

    顺序：先自旧向新删除 ``system`` 之后、末条 ``user`` 之前的轮次；仍超则自左截断末条
    ``user`` 正文；再超则自左截断 ``system``（最后手段）。
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if not messages:
        return []

    msgs = [dict(x) for x in messages]
    if msgs[0].get("role") != "system":
        raise ValueError("trim_messages_to_token_budget expects leading system message")
    if msgs[-1].get("role") != "user":
        raise ValueError("trim_messages_to_token_budget expects trailing user message")

    def over() -> bool:
        return total_tokens_for_messages(msgs) > max_tokens

    # 1) 去掉最旧的历史轮次（保留首条 system 与末条 user）
    while len(msgs) > 2 and over():
        msgs.pop(1)

    # 2) 截断末条 user
    while len(msgs) == 2 and over():
        u = msgs[1].get("content", "")
        if len(u) <= 1:
            break
        msgs[1]["content"] = u[1:]

    # 3) 截断 system（仍超预算时）
    while over() and msgs:
        s = msgs[0].get("content", "")
        if len(s) <= 1:
            break
        msgs[0]["content"] = s[1:]

    return msgs


def build_messages(
    *,
    user_content: str,
    term_id: str,
    history: Sequence[Mapping[str, str]] | None = None,
    context_type: str | None = None,
    context_ref_id: str | None = None,
    max_context_tokens: int | None = None,
) -> list[dict[str, str]]:
    """从入参组装 OpenAI 风格 ``messages``（无 IO、无 LLM），并按 token 预算裁剪。

    - ``history``：自旧向新；仅含 ``user`` / ``assistant``。
    - ``max_context_tokens``：缺省时使用 ``Config.CHAT_CONTEXT_TOKEN_BUDGET``。
    """
    text = (user_content or "").strip()
    if not text:
        raise ValueError("user_content must be non-empty")
    tid = (term_id or "").strip()
    if not tid:
        raise ValueError("term_id must be non-empty")

    budget = (
        max_context_tokens
        if max_context_tokens is not None
        else int(Config.CHAT_CONTEXT_TOKEN_BUDGET)
    )
    if budget <= 0:
        raise ValueError("max_context_tokens must be positive")

    lines = [CHAT_SYSTEM_DISCLAIMER_ZH, f"学期/配额命名空间 term_id: {tid}."]
    hint = _context_hint_zh(context_type=context_type, context_ref_id=context_ref_id)
    if hint:
        lines.append(hint)
    system_content = "\n".join(lines)

    out: list[dict[str, str]] = [{"role": "system", "content": system_content}]

    if history:
        for i, row in enumerate(history):
            role = row.get("role", "")
            content = row.get("content", "")
            if role not in ("user", "assistant"):
                raise ValueError(
                    f'history[{i}]: role must be "user" or "assistant", got {role!r}'
                )
            c = (content or "").strip()
            if not c:
                raise ValueError(f"history[{i}]: content must be non-empty")
            out.append({"role": role, "content": c})

    out.append({"role": "user", "content": text})
    return trim_messages_to_token_budget(out, max_tokens=budget)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_llm_output(result: Any) -> dict[str, Any]:
    if isinstance(result, Mapping):
        usage_raw = result.get("usage")
        usage = dict(usage_raw) if isinstance(usage_raw, Mapping) else None
        model_name = str(result.get("model") or result.get("model_name") or "").strip() or None
        provider_request_id = (
            str(result.get("provider_request_id") or result.get("request_id") or result.get("id") or "").strip() or None
        )
        content_raw = result.get("content", "")
        return {
            "content": "" if content_raw is None else str(content_raw),
            "usage": usage,
            "model_name": model_name,
            "provider_request_id": provider_request_id,
        }
    return {
        "content": "" if result is None else str(result),
        "usage": None,
        "model_name": None,
        "provider_request_id": None,
    }


def _normalize_error_code(value: object) -> str:
    if isinstance(value, ErrorCode):
        return value.value
    text = str(value).strip() if value is not None else ""
    return text or ErrorCode.DOMAIN_ERROR.value


def _persist_failed_job_if_possible(
    *,
    job_id: str,
    assistant_message_id: str | None,
    error_code: str,
    error_message: str,
    started_at: datetime | None = None,
) -> Exception | None:
    try:
        db.session.rollback()
    except Exception:  # noqa: BLE001 - best-effort cleanup before failure writeback
        return None

    try:
        job = db.session.get(ChatJob, job_id) if job_id else None
        assistant_message = (
            db.session.get(Message, assistant_message_id)
            if assistant_message_id is not None and str(assistant_message_id).strip()
            else None
        )
        if job is None:
            return None
        if job.status == MessageAsyncTaskStatus.done:
            return None

        job.status = MessageAsyncTaskStatus.failed
        job.started_at = job.started_at or started_at or _utc_now_naive()
        job.finished_at = _utc_now_naive()
        job.error_code = error_code
        job.error_message = error_message
        job.provider_request_id = None
        job.model_name = None
        job.usage_json = None
        if assistant_message is not None:
            assistant_message.delivery_status = MessageAsyncTaskStatus.failed
            assistant_message.content = assistant_message.content or ""
        db.session.commit()
    except Exception as exc:  # noqa: BLE001 - preserve primary failure while surfacing writeback issue
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001 - best effort only
            pass
        return exc
    return None


def _raise_with_failure_writeback(
    exc: Exception,
    *,
    job_id: str,
    assistant_message_id: str,
    error_code: str,
    started_at: datetime | None = None,
) -> None:
    writeback_exc = _persist_failed_job_if_possible(
        job_id=job_id,
        assistant_message_id=assistant_message_id,
        error_code=error_code,
        error_message=str(exc),
        started_at=started_at,
    )
    if writeback_exc is not None and hasattr(exc, "add_note"):
        exc.add_note(f"chat failure writeback also failed: {writeback_exc}")
    raise exc


def run_turn(conversation_id: str, messages: list, term_id: str, **kwargs: Any) -> None:
    """Worker 路径：调用 LLM 并将 ChatJob / assistant 占位写回到终态。"""
    from app.adapter import llm as llm_mod

    job_id = str(kwargs.get("job_id", "")).strip()
    assistant_message_id = str(kwargs.get("assistant_message_id", "")).strip()
    user_message_id = str(kwargs.get("user_message_id", "")).strip()

    job = db.session.get(ChatJob, job_id)
    if job is None:
        raise ValueError("chat job row is missing")
    if job.status in _TERMINAL_CHAT_JOB_STATUSES:
        return

    user_message = db.session.get(Message, user_message_id)
    assistant_message = db.session.get(Message, assistant_message_id)
    if user_message is None or assistant_message is None:
        exc = ValueError("chat job persistence rows are missing")
        _raise_with_failure_writeback(
            exc,
            job_id=job_id,
            assistant_message_id=assistant_message_id,
            error_code=ErrorCode.DOMAIN_ERROR.value,
        )
    if job.conversation_id != str(conversation_id).strip():
        exc = ValueError("chat job conversation_id mismatch")
        _raise_with_failure_writeback(
            exc,
            job_id=job_id,
            assistant_message_id=assistant_message_id,
            error_code=ErrorCode.DOMAIN_ERROR.value,
        )
    if user_message.conversation_id != job.conversation_id or assistant_message.conversation_id != job.conversation_id:
        exc = ValueError("chat job message rows do not belong to the same conversation")
        _raise_with_failure_writeback(
            exc,
            job_id=job_id,
            assistant_message_id=assistant_message_id,
            error_code=ErrorCode.DOMAIN_ERROR.value,
        )

    started_at = job.started_at or _utc_now_naive()
    job.status = MessageAsyncTaskStatus.running
    job.started_at = started_at
    job.finished_at = None
    job.error_code = None
    job.error_message = None
    job.provider_request_id = None
    job.model_name = None
    job.usage_json = None
    assistant_message.delivery_status = MessageAsyncTaskStatus.running
    try:
        db.session.commit()
    except Exception as exc:  # noqa: BLE001 - must fail terminally when worker claim cannot persist
        _raise_with_failure_writeback(
            exc,
            job_id=job_id,
            assistant_message_id=assistant_message_id,
            error_code=ErrorCode.DOMAIN_ERROR.value,
            started_at=started_at,
        )

    try:
        llm_result = llm_mod.complete(
            messages,
            term_id=term_id,
            user_id=kwargs.get("user_id"),
            request_id=kwargs.get("request_id"),
        )
    except Exception as exc:
        _raise_with_failure_writeback(
            exc,
            job_id=job_id,
            assistant_message_id=assistant_message_id,
            error_code=_normalize_error_code(getattr(exc, "error_code", ErrorCode.DOMAIN_ERROR.value)),
            started_at=started_at,
        )

    normalized = _normalize_llm_output(llm_result)
    assistant_message.content = normalized["content"]
    assistant_message.delivery_status = MessageAsyncTaskStatus.done
    job.status = MessageAsyncTaskStatus.done
    job.finished_at = _utc_now_naive()
    job.provider_request_id = normalized["provider_request_id"]
    job.model_name = normalized["model_name"]
    job.usage_json = normalized["usage"]
    job.error_code = None
    job.error_message = None
    try:
        db.session.commit()
    except Exception as exc:
        _raise_with_failure_writeback(
            exc,
            job_id=job_id,
            assistant_message_id=assistant_message_id,
            error_code=ErrorCode.DOMAIN_ERROR.value,
            started_at=started_at,
        )
