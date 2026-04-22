"""Chat service skeleton."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.chat.model import (
    ChatJob,
    Conversation,
    ConversationContextType,
    Message,
    MessageAsyncTaskStatus,
    MessageRole,
)
from app.common.error_envelope import ErrorCode
from app.common.policy import PolicyDenied
from app.extensions import get_policy_gateway
from app.extensions import db
from app.identity.service import IdentityService
from app.terms.model import Term
from app.task import queue as queue_mod
from flask import has_app_context
from sqlalchemy import and_, or_


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

    enq = queue_mod.enqueue_chat_jobs(queue_payload)
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
    def __init__(self, identity_service: IdentityService | None = None) -> None:
        self._identity = identity_service or IdentityService()

    def list_conversations_for_user(
        self,
        user_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Return paginated conversation list for current user."""
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")

        user = self._identity.load_user_by_id(user_id)
        if user is None:
            return {"items": [], "page": page, "page_size": page_size, "total": 0}

        q = Conversation.query.filter_by(user_id=user.id).order_by(
            Conversation.archived_at.asc(),
            Conversation.updated_at.desc(),
            Conversation.id.desc(),
        )
        q = q.filter(Conversation.archived_at.is_(None))
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [row.to_conversation() for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def create_conversation_for_user(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create conversation for current user; ``term_id`` is required."""
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        user = self._identity.load_user_by_id(user_id)
        if user is None:
            raise ValueError("user not found")

        term_id = str(payload.get("term_id", "")).strip()
        if not term_id:
            raise ValueError("term_id is required")
        if db.session.get(Term, term_id) is None:
            raise ValueError("term not found")

        context_type_raw = payload.get("context_type")
        context_type = None
        if context_type_raw is not None:
            text = str(context_type_raw).strip()
            if text not in {e.value for e in ConversationContextType}:
                raise ValueError("context_type must be one of: general, topic, document")
            context_type = ConversationContextType(text)

        title_raw = payload.get("title")
        title = None if title_raw is None else str(title_raw)
        context_ref_raw = payload.get("context_ref_id")
        context_ref_id = None if context_ref_raw is None else str(context_ref_raw)

        conv = Conversation(
            user_id=user.id,
            term_id=term_id,
            title=title,
            context_type=context_type,
            context_ref_id=context_ref_id,
        )
        db.session.add(conv)
        db.session.commit()
        return conv.to_conversation()

    def get_conversation_for_user(self, user_id: str, conversation_id: str) -> dict[str, Any] | None:
        """Return conversation metadata only when visible to current user."""
        user = self._identity.load_user_by_id(user_id)
        if user is None:
            return None
        conv_id = str(conversation_id).strip()
        if not conv_id:
            raise ValueError("conversation_id must be non-empty")

        conv = Conversation.query.filter_by(id=conv_id, user_id=user.id).one_or_none()
        if conv is None:
            return None
        if conv.archived_at is not None:
            return None
        return conv.to_conversation()

    def archive_conversation_for_user(self, user_id: str, conversation_id: str) -> bool:
        """Soft-delete/archive a conversation owned by current user."""
        user = self._identity.load_user_by_id(user_id)
        if user is None:
            return False
        conv_id = str(conversation_id).strip()
        if not conv_id:
            raise ValueError("conversation_id must be non-empty")

        conv = Conversation.query.filter_by(id=conv_id, user_id=user.id).one_or_none()
        if conv is None:
            return False
        if conv.archived_at is None:
            conv.archived_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
        return True

    def list_messages_for_conversation(
        self,
        user_id: str,
        conversation_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
        order: str = "asc",
        after_message_id: str | None = None,
        before_message_id: str | None = None,
    ) -> dict[str, Any]:
        """List conversation messages with pagination and cursor constraints."""
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        if order not in {"asc", "desc"}:
            raise ValueError("order must be 'asc' or 'desc'")
        if after_message_id and before_message_id:
            raise ValueError("after_message_id and before_message_id are mutually exclusive")

        conv = self.get_conversation_for_user(user_id, conversation_id)
        if conv is None:
            return {"items": [], "page": page, "page_size": page_size, "total": 0}

        q = Message.query.filter_by(conversation_id=str(conversation_id).strip())
        if after_message_id:
            anchor = db.session.get(Message, str(after_message_id).strip())
            if anchor is not None and anchor.conversation_id == str(conversation_id).strip():
                q = q.filter(
                    or_(
                        Message.created_at > anchor.created_at,
                        and_(Message.created_at == anchor.created_at, Message.id > anchor.id),
                    )
                )
        elif before_message_id:
            anchor = db.session.get(Message, str(before_message_id).strip())
            if anchor is not None and anchor.conversation_id == str(conversation_id).strip():
                q = q.filter(
                    or_(
                        Message.created_at < anchor.created_at,
                        and_(Message.created_at == anchor.created_at, Message.id < anchor.id),
                    )
                )

        sort_col = Message.created_at.asc() if order == "asc" else Message.created_at.desc()
        q = q.order_by(sort_col, Message.id.asc() if order == "asc" else Message.id.desc())

        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [m.to_message() for m in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def send_user_message(
        self,
        conversation_id: str,
        content: str,
        user_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from app.use_cases import chat_orchestration as uc

        job_id = str(uuid.uuid4())
        user_message_id = str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())
        if not has_app_context():
            # Compatibility path for architecture spy tests and non-Flask script usage.
            term_id = str(kwargs.pop("term_id", "")).strip()
            return create_chat(
                conversation_id=str(conversation_id),
                term_id=term_id,
                user_id=str(user_id),
                content=str(content),
                **kwargs,
            )

        conv = Conversation.query.filter_by(id=str(conversation_id).strip(), user_id=str(user_id).strip()).one_or_none()
        if conv is None or conv.archived_at is not None:
            raise ValueError("conversation not found for user")
        term_id = conv.term_id

        history_raw = kwargs.pop("history", None)
        built_messages = uc.build_messages(
            user_content=content,
            term_id=term_id,
            history=history_raw,
            context_type=conv.context_type.value if conv.context_type is not None else None,
            context_ref_id=conv.context_ref_id,
        )
        # Keep only conversational history for worker payload (strip system + trailing user).
        history_payload = built_messages[1:-1] if len(built_messages) > 2 else []

        policy_gateway = get_policy_gateway()
        policy_gateway.assert_can_enqueue(
            queue=queue_mod.CHAT_JOBS,
            conversation_id=conversation_id,
            user_id=user_id,
            term_id=term_id,
        )

        user_message = Message(
            id=user_message_id,
            conversation_id=conversation_id,
            role=MessageRole.user,
            content=str(content),
            delivery_status=None,
        )
        assistant_message = Message(
            id=assistant_message_id,
            conversation_id=conversation_id,
            role=MessageRole.assistant,
            content="",
            delivery_status=MessageAsyncTaskStatus.pending,
        )
        db.session.add_all([user_message, assistant_message])
        db.session.flush()
        db.session.add(
            ChatJob(
                job_id=job_id,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
                status=MessageAsyncTaskStatus.pending,
            )
        )
        db.session.commit()

        enqueue_payload = {
            "job_id": job_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "term_id": term_id,
            "user_id": user_id,
            "content": content,
            "history": history_payload,
            "context_type": conv.context_type.value if conv.context_type is not None else None,
            "context_ref_id": conv.context_ref_id,
            **kwargs,
        }
        try:
            queue_mod.enqueue_chat_jobs(enqueue_payload)
        except Exception as exc:
            chat_job = db.session.get(ChatJob, job_id)
            if chat_job is not None:
                chat_job.status = MessageAsyncTaskStatus.failed
                chat_job.error_code = ErrorCode.QUEUE_UNAVAILABLE.value
                chat_job.error_message = str(exc)
            assistant_row = db.session.get(Message, assistant_message_id)
            if assistant_row is not None:
                assistant_row.delivery_status = MessageAsyncTaskStatus.failed
                assistant_row.content = assistant_row.content or ""
            db.session.commit()
            raise PolicyDenied(
                "chat queue is unavailable",
                code=ErrorCode.QUEUE_UNAVAILABLE,
            ) from exc
        return {
            "job_id": job_id,
            "user_message": user_message.to_message(),
            "assistant_message": assistant_message.to_message(),
        }

    def get_chat_job_for_user(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        """Return a ``ChatJob`` when the job's conversation belongs to ``user_id``."""
        uid = str(user_id or "").strip()
        jid = str(job_id or "").strip()
        if not jid:
            raise ValueError("job_id must be non-empty")
        if not uid:
            raise ValueError("user_id must be non-empty")
        row = db.session.get(ChatJob, jid)
        if row is None:
            return None
        conv = db.session.get(Conversation, row.conversation_id)
        if conv is None or conv.user_id != uid or conv.archived_at is not None:
            return None
        return row.to_chat_job()
