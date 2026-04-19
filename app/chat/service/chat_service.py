"""Chat service skeleton."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.task import queue as queue_mod


def _utc_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_chat(
    conversation_id: str,
    term_id: str,
    user_id: str,
    content: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """受理路径占位：返回 contract 对齐的 202 体（job_id + Message 真字段 + ChatJobPayload 入队）。"""
    job_id = str(uuid.uuid4())
    user_message_id = str(uuid.uuid4())
    assistant_message_id = str(uuid.uuid4())
    created_at = _utc_iso_z()

    client_request_id = kwargs.pop("client_request_id", None)
    seq = kwargs.pop("seq", None)

    queue_payload: dict[str, Any] = {
        "job_id": job_id,
        "conversation_id": conversation_id,
        "user_message_id": user_message_id,
        "assistant_message_id": assistant_message_id,
        "term_id": term_id,
        "user_id": user_id,
        "content": content,
        **kwargs,
    }
    if client_request_id is not None:
        queue_payload["client_request_id"] = client_request_id
    if seq is not None:
        queue_payload["seq"] = seq

    enq = queue_mod.enqueue("chat_jobs", queue_payload)
    out_job_id = enq.get("job_id") if isinstance(enq, dict) else getattr(enq, "job_id", job_id)
    out_job_id = str(out_job_id) if out_job_id is not None else job_id

    return {
        "status": "pending",
        "job_id": out_job_id,
        "user_message": {
            "id": user_message_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": content,
            "created_at": created_at,
        },
        "assistant_message": {
            "id": assistant_message_id,
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": "",
            "status": "pending",
            "created_at": created_at,
        },
    }


class ChatService:
    def send_user_message(self, conversation_id: str, content: str, user_id: str, **kwargs) -> None:
        job_id = str(uuid.uuid4())
        user_message_id = str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())
        term_id = str(kwargs.pop("term_id", ""))
        queue_mod.enqueue(
            "chat_jobs",
            {
                "job_id": job_id,
                "conversation_id": conversation_id,
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
                "term_id": term_id,
                "user_id": user_id,
                "content": content,
                **kwargs,
            },
        )
