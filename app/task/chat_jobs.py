"""chat_jobs consumer: validate payload then dispatch chat orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChatJobPayload:
    job_id: str
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    term_id: str
    user_id: str
    content: str
    history: tuple[dict[str, str], ...] = ()
    context_type: str | None = None
    context_ref_id: str | None = None
    client_request_id: str | None = None
    seq: int | None = None
    request_id: str | None = None
    dispatch_attempt: int | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "ChatJobPayload":
        required = (
            "job_id",
            "conversation_id",
            "user_message_id",
            "assistant_message_id",
            "term_id",
            "user_id",
        )
        normalized: dict[str, str] = {}
        for key in required:
            raw = payload.get(key)
            text = str(raw).strip() if raw is not None else ""
            if not text:
                raise ValueError(f"ChatJobPayload.{key} must be non-empty")
            normalized[key] = text

        content_raw = payload.get("content")
        content = str(content_raw).strip() if content_raw is not None else ""
        if not content:
            raise ValueError("ChatJobPayload.content must be non-empty")

        history = payload.get("history")
        parsed_history: tuple[dict[str, str], ...] = ()
        if history is not None:
            if not isinstance(history, list):
                raise ValueError("ChatJobPayload.history must be a list when provided")
            items: list[dict[str, str]] = []
            for item in history:
                if not isinstance(item, dict):
                    raise ValueError("ChatJobPayload.history items must be mappings")
                items.append(
                    {
                        "role": str(item.get("role", "")),
                        "content": str(item.get("content", "")),
                    }
                )
            parsed_history = tuple(items)

        def _opt_text(name: str) -> str | None:
            raw = payload.get(name)
            if raw is None:
                return None
            text = str(raw).strip()
            return text or None

        seq_raw = payload.get("seq")
        seq = None if seq_raw is None else int(seq_raw)
        dispatch_attempt_raw = payload.get("dispatch_attempt")
        dispatch_attempt = None if dispatch_attempt_raw is None else int(dispatch_attempt_raw)

        return cls(
            job_id=normalized["job_id"],
            conversation_id=normalized["conversation_id"],
            user_message_id=normalized["user_message_id"],
            assistant_message_id=normalized["assistant_message_id"],
            term_id=normalized["term_id"],
            user_id=normalized["user_id"],
            content=content,
            history=parsed_history,
            context_type=_opt_text("context_type"),
            context_ref_id=_opt_text("context_ref_id"),
            client_request_id=_opt_text("client_request_id"),
            seq=seq,
            request_id=_opt_text("request_id"),
            dispatch_attempt=dispatch_attempt,
        )


def handle_chat_job(payload: dict[str, Any]) -> None:
    from app.use_cases import chat_orchestration as uc

    typed = ChatJobPayload.from_mapping(payload)
    messages = uc.build_messages(
        user_content=typed.content,
        term_id=typed.term_id,
        history=list(typed.history),
        context_type=typed.context_type,
        context_ref_id=typed.context_ref_id,
    )
    uc.run_turn(
        conversation_id=typed.conversation_id,
        messages=messages,
        term_id=typed.term_id,
        job_id=typed.job_id,
        user_id=typed.user_id,
        user_message_id=typed.user_message_id,
        assistant_message_id=typed.assistant_message_id,
        client_request_id=typed.client_request_id,
        seq=typed.seq,
        request_id=typed.request_id,
        dispatch_attempt=typed.dispatch_attempt,
    )


def run(payload: dict[str, Any]) -> None:
    handle_chat_job(payload)
