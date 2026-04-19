"""Chat service skeleton."""

from __future__ import annotations

from typing import Any

from app.task import queue as queue_mod


def create_chat(
    conversation_id: str,
    term_id: str,
    user_id: str,
    content: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """受理路径占位：返回 contract 对齐的 202 体（pending + job_id + 消息占位）。"""
    enq = queue_mod.enqueue(
        "chat_jobs",
        {
            "conversation_id": conversation_id,
            "content": content,
            "user_id": user_id,
            "term_id": term_id,
            **kwargs,
        },
    )
    job_id = enq.get("job_id") if isinstance(enq, dict) else getattr(enq, "job_id", None)
    return {
        "status": "pending",
        "job_id": str(job_id) if job_id is not None else "",
        "user_message": {
            "role": "user",
            "content": content,
            "conversation_id": conversation_id,
            "user_id": user_id,
        },
        "assistant_message": {
            "status": "pending",
            "role": "assistant",
            "content": "",
        },
    }


class ChatService:
    def send_user_message(self, conversation_id: str, content: str, user_id: str, **kwargs) -> None:
        queue_mod.enqueue(
            "chat_jobs",
            {
                "conversation_id": conversation_id,
                "content": content,
                "user_id": user_id,
                **kwargs,
            },
        )
