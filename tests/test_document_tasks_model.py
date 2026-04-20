"""AG-014：``document_tasks`` ORM；``term_id``、锁、断点、``result_*``、``error_*`` 与契约 ``DocumentTask`` 对齐。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.document.model import (
    DocumentLanguage,
    DocumentTask,
    DocumentTaskStatus,
    DocumentTaskType,
)
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


def test_document_task_persists_core_fields_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(username="doc-u1", role=UserRole.student, display_name="S")
        t = Term(name="2026 春")
        db.session.add_all([u, t])
        db.session.commit()

        locked = datetime(2026, 4, 1, 8, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
        nxt = datetime(2026, 4, 2, 9, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)

        dt = DocumentTask(
            user_id=u.id,
            term_id=t.id,
            filename="paper.pdf",
            storage_path="/store/obj/paper.pdf",
            task_type=DocumentTaskType.compare,
            language=DocumentLanguage.en,
            status=DocumentTaskStatus.running,
            locked_at=locked,
            last_completed_chunk=2,
            result_json={
                "summary": "S",
                "bullet_points": ["a", "b"],
                "raw_model": "x",
            },
            result_storage_uri="s3://bucket/key",
            error_code=None,
            error_message=None,
            retry_count=1,
            max_attempts=5,
            next_retry_at=nxt,
        )
        db.session.add(dt)
        db.session.commit()

        loaded = db.session.get(DocumentTask, dt.id)
        assert loaded is not None
        assert loaded.term_id == t.id
        assert loaded.locked_at == locked
        assert loaded.last_completed_chunk == 2
        assert loaded.retry_count == 1

        body = loaded.to_document_task()
        assert body["id"] == loaded.id
        assert body["term_id"] == t.id
        assert body["status"] == "running"
        assert body["filename"] == "paper.pdf"
        assert body["task_type"] == "compare"
        assert body["language"] == "en"
        assert body["locked_at"] == "2026-04-01T08:00:00Z"
        assert body["last_completed_chunk"] == 2
        assert body["result"] == {
            "summary": "S",
            "bullet_points": ["a", "b"],
            "raw_model": "x",
        }
        assert body["result_storage_uri"] == "s3://bucket/key"
        assert body["error_code"] is None
        assert body["error_message"] is None
        assert body["retry_count"] == 1
        assert body["max_attempts"] == 5
        assert body["next_retry_at"] == "2026-04-02T09:00:00Z"
        assert body["created_at"].endswith("Z")
        assert body["updated_at"].endswith("Z")


def test_document_task_defaults_and_errors() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(username="doc-u2", role=UserRole.student, display_name="S2")
        t = Term(name="默认学期")
        db.session.add_all([u, t])
        db.session.commit()

        dt = DocumentTask(
            user_id=u.id,
            term_id=t.id,
            filename="x.pdf",
            storage_path="/tmp/x.pdf",
            error_code="QUEUE_UNAVAILABLE",
            error_message="broker down",
        )
        db.session.add(dt)
        db.session.commit()

        loaded = db.session.get(DocumentTask, dt.id)
        assert loaded is not None
        assert loaded.task_type == DocumentTaskType.summary
        assert loaded.language == DocumentLanguage.zh
        assert loaded.status == DocumentTaskStatus.pending
        assert loaded.retry_count == 0

        body = loaded.to_document_task()
        assert body["task_type"] == "summary"
        assert body["language"] == "zh"
        assert body["status"] == "pending"
        assert body["retry_count"] == 0
        assert body["result"] is None
        assert body["error_code"] == "QUEUE_UNAVAILABLE"
        assert body["error_message"] == "broker down"


def test_document_task_term_restrict_on_delete() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        u = User(username="doc-u3", role=UserRole.student, display_name="S3")
        t = Term(name="删学期前")
        db.session.add_all([u, t])
        db.session.commit()
        dt = DocumentTask(
            user_id=u.id,
            term_id=t.id,
            filename="a.pdf",
            storage_path="/a",
        )
        db.session.add(dt)
        db.session.commit()

        # RESTRICT：有任务引用时不可删学期
        with pytest.raises(IntegrityError):
            db.session.delete(t)
            db.session.commit()
        db.session.rollback()

        db.session.delete(dt)
        db.session.commit()
        db.session.delete(t)
        db.session.commit()
