"""LLM 客户端抽象基类与无厂商 HTTP 的默认 mock 实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LlmClient(ABC):
    """具体厂商客户端（AG-028+）与单元测试 mock 的共同基类。"""

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> Any:
        """子类实现真实或假定的生成逻辑。"""

    def invoke_chat(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> Any:
        return self.complete(messages, **kwargs)

    def chat(self, *args: Any, **kwargs: Any) -> Any:
        """Spy 与旧调用约定：首参为 messages 列表时转调 ``complete``。"""
        if args and isinstance(args[0], list):
            return self.complete(args[0], **kwargs)
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            rest = {k: v for k, v in kwargs.items() if k != "messages"}
            return self.complete(messages, **rest)
        return self.complete([], **kwargs)

    def call(
        self,
        *,
        messages: list[dict[str, Any]],
        conversation_id: str,
        term_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """默认将上下文关键字传入 ``complete``；返回可序列化 dict。"""
        out = self.complete(
            messages,
            conversation_id=conversation_id,
            term_id=term_id,
            **kwargs,
        )
        if isinstance(out, dict):
            return out
        return {"content": str(out)}


class MockLlmClient(LlmClient):
    """无外部 HTTP：占位文本，满足 contract 与 ``test_llm_adapter_surface``。"""

    def complete(
        self,
        messages: list[dict[str, Any]],
        /,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = kwargs
        prompt = _latest_user_content(messages)
        lowered = prompt.lower()
        if "aggregate chunk summaries" in lowered:
            return {"content": _mock_document_aggregate(prompt)}
        if "summarize chunk" in lowered:
            return {"content": _mock_document_chunk_summary(prompt)}
        return {"content": _mock_chat_answer(prompt)}


def _latest_user_content(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if str(message.get("role", "")).lower() == "user":
            return str(message.get("content", "")).strip()
    return ""


def _compact_text(text: str, *, limit: int = 120) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


def _mock_chat_answer(prompt: str) -> str:
    focus = _compact_text(prompt or "毕业设计选题咨询", limit=96)
    if "选择导师和课题" in prompt or "双向选择刍议" in prompt:
        return (
            "读完这篇文献后，选择导师和课题时可以把重点放在“匹配”而不是“抢热门”。"
            "\n- 不要只看题目名称：先看导师课题的研究内容、难度、资料来源和最终成果形式。"
            "\n- 评估自身条件：把自己的课程基础、编程能力、写作能力和可投入时间与课题要求对照。"
            "\n- 注意志愿顺序：第一志愿放最匹配、最愿意持续投入的课题，第二志愿选择风险更低的备选。"
            "\n- 主动沟通导师：在提交志愿前说明自己的兴趣、已有基础和担心的问题，减少后期被动调整。"
        )
    if "判断一个课题是否适合自己" in prompt or "毕业设计选题" in prompt:
        return (
            "判断一个毕业设计课题是否适合自己，可以从四个方面快速筛选。"
            "\n- 兴趣方向：题目是否和你愿意持续研究的方向相关，至少要能支撑几个月的投入。"
            "\n- 能力基础：对照题目要求，看自己是否具备必要的专业知识、工具能力和资料阅读能力。"
            "\n- 课题边界：题目范围是否清楚，成果形式是否明确，避免选择过大、过空或无法落地的方向。"
            "\n- 导师沟通：提前确认导师对进度、方法和成果的要求，判断指导方式是否适合自己。"
            "\n建议先选出 2 到 3 个候选课题，再比较匹配度、风险和可完成性。"
        )
    return (
        "可以先把问题拆成“目标、资料、方法、成果”四个部分，再决定下一步怎么推进。"
        f"\n- 针对问题：{focus}"
        "\n- 当前建议：先明确你要解决的具体问题，再列出现有资料和可用工具。"
        "\n- 下一步：如果你提供课题名称或文献摘要，我可以继续帮你判断难度、风险和切入点。"
    )


def _mock_document_chunk_summary(prompt: str) -> str:
    marker = "Chunk text:"
    chunk_text = prompt.split(marker, 1)[1] if marker in prompt else prompt
    excerpt = _compact_text(chunk_text, limit=110)
    if "双向选择" in chunk_text or "导师" in chunk_text:
        return (
            f"本段围绕毕业设计双向选择制度展开，核心内容是：{excerpt}"
            "\n- 原文要点：通过竞争机制改善以往导师和学生被动分派的问题。"
            "\n- 可提取线索：导师课题介绍、学生志愿填报、导师选择学生和落选调剂。"
        )
    return (
        f"本段提炼了文档中的主要论述，核心内容是：{excerpt}"
        "\n- 原文要点：保留了毕业设计管理、教学质量或选题流程相关信息。"
        "\n- 可提取线索：为后续聚合摘要提供关键词和论证依据。"
    )


def _mock_document_aggregate(prompt: str) -> str:
    _ = prompt
    return (
        "该文献围绕毕业设计环节中的导师与学生双向选择机制展开，讨论如何通过竞争机制提升毕业设计质量。"
        "\n- 问题背景：传统毕业设计分配方式以班主任或院系安排为主，导师和学生缺少选择空间，容易造成学生兴趣不足、导师积极性不高和优秀毕业设计评选说服力不足等问题。"
        "\n- 主要做法：先由导师公布毕业设计课题及内容概要，学生在了解课题后填报志愿；再由导师根据学生志愿、学习基础和能力情况选择学生；未被选中的导师或学生由毕业设计领导小组统一调剂。"
        "\n- 作用分析：双向选择能够促使导师提高课题质量和教学水平，也能增强学生选择课题后的主动性、自觉性和责任感，从而改善毕业设计过程质量。"
        "\n- 结论观点：在具备导师队伍和评优制度等条件时，引入竞争机制和双向选择有助于提高毕业设计质量，并使优秀毕业设计评选更具可操作性和可信度。"
        "\n- 关键词：毕业设计；竞争机制；双向选择；导师选择；学生志愿"
    )
