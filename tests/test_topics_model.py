"""AG-015：``topics`` ORM、``TopicStatus`` 与契约 ``Topic.status`` 对齐。"""
from __future__ import annotations

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicKeywordJobStatus, TopicStatus


def test_topic_persists_workflow_status_and_maps_to_contract_shape() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = User(
            username="t1",
            role=UserRole.teacher,
            display_name="教师一",
        )
        term = Term(name="2026 春")
        db.session.add_all([teacher, term])
        db.session.commit()

        topic = Topic(
            title="课题 A",
            summary="摘要",
            requirements="要求",
            capacity=3,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.draft,
            tech_keywords=["ml", "nlp"],
        )
        db.session.add(topic)
        db.session.commit()

        loaded = db.session.get(Topic, topic.id)
        assert loaded is not None
        assert loaded.status == TopicStatus.draft

        body = loaded.to_topic()
        assert body["id"] == loaded.id
        assert body["title"] == "课题 A"
        assert body["summary"] == "摘要"
        assert body["requirements"] == "要求"
        assert body["tech_keywords"] == ["ml", "nlp"]
        assert body["capacity"] == 3
        assert body["selected_count"] == 0
        assert body["teacher_id"] == teacher.id
        assert body["term_id"] == term.id
        assert body["status"] == "draft"
        assert body["portrait"] is None
        assert body["llm_keyword_job_id"] is None
        assert body["llm_keyword_job_status"] is None
        assert body["created_at"].endswith("Z")
        assert body["updated_at"].endswith("Z")


def test_topic_status_enum_covers_contract_values() -> None:
    assert {s.value for s in TopicStatus} == {
        "draft",
        "pending_review",
        "published",
        "rejected",
        "closed",
    }


def test_topic_keyword_job_status_matches_async_task_status() -> None:
    assert {s.value for s in TopicKeywordJobStatus} == {"pending", "running", "done", "failed"}
