"""Document service skeleton."""

from __future__ import annotations

import uuid
from typing import Any

from app.task import queue as queue_mod


class DocumentService:
    def create_document_task(
        self, user_id: str, term_id: str, storage_path: str, filename: str, **kwargs: Any
    ) -> None:
        document_task_id = str(uuid.uuid4())
        task_type = kwargs.pop("task_type", "summary")
        language = kwargs.pop("language", "zh")
        queue_mod.enqueue(
            "document_jobs",
            {
                "document_task_id": document_task_id,
                "user_id": user_id,
                "storage_path": storage_path,
                "term_id": term_id,
                "task_type": task_type,
                "language": language,
                "stage": kwargs.pop("stage", "extract"),
                "filename": filename,
                **kwargs,
            },
        )
