"""Document service skeleton."""

from app.task import queue as queue_mod


class DocumentService:
    def create_document_task(
        self, user_id: str, term_id: str, storage_path: str, filename: str, **kwargs
    ) -> None:
        queue_mod.enqueue(
            "document_jobs",
            {
                "user_id": user_id,
                "term_id": term_id,
                "storage_path": storage_path,
                "filename": filename,
                **kwargs,
            },
        )
