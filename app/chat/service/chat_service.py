"""Chat service skeleton."""

from app.task import queue as queue_mod


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
