"""Chat 编排：无 HTTP 上下文；``build_messages`` 为纯函数（无 IO、无 LLM）。

``run_turn`` 仅在 Worker 路径内调用 ``adapter.llm``（与 R-SYNC-LLM / W4 一致）。

token 级裁剪：与 ``execution_plan`` chat 子任务及 §14.6 引用一致；粗估算法可替换为 tiktoken，
预算来自 ``app.config.Config.CHAT_CONTEXT_TOKEN_BUDGET``（``CHAT_CONTEXT_TOKEN_BUDGET`` 环境变量）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.config import Config

# 与 execution_plan「系统角色与免责声明」对齐
CHAT_SYSTEM_DISCLAIMER_ZH = (
    "你是毕业设计领域的辅助助手。以下回答仅供学习与研究参考，不构成正式学术结论或法律意见。"
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


def run_turn(conversation_id: str, messages: list, term_id: str, **kwargs) -> None:
    """Worker 路径：调用 LLM（由架构测试 patch ``adapter.llm``）。"""
    from app.adapter import llm as llm_mod

    _ = (conversation_id, term_id, kwargs)
    llm_mod.complete(messages)
