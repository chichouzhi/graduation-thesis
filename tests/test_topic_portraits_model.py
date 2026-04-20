"""AG-016：``topic_portraits`` 等价物 — ``topics.portrait_json`` 列与契约 ``Topic.portrait`` 映射。"""
from __future__ import annotations

from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicKeywordJobStatus, TopicStatus, contract_portrait_from_json


def test_contract_portrait_from_json_none() -> None:
    assert contract_portrait_from_json(None) is None


def test_contract_portrait_from_json_maps_contract_keys() -> None:
    ext = "2026-05-01T12:00:00Z"
    assert contract_portrait_from_json({"keywords": ["x"], "extracted_at": ext}) == {
        "keywords": ["x"],
        "extracted_at": ext,
    }


def test_contract_portrait_from_json_ignores_extra_keys() -> None:
    out = contract_portrait_from_json({"keywords": ["a"], "extra": 1})
    assert out == {"keywords": ["a"], "extracted_at": None}


def test_topic_portrait_and_llm_job_fields_round_trip() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = User(username="t2", role=UserRole.teacher, display_name="T")
        term = Term(name="学期")
        db.session.add_all([teacher, term])
        db.session.commit()

        ext = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        topic = Topic(
            title="x",
            summary="s",
            requirements="r",
            capacity=1,
            teacher_id=teacher.id,
            term_id=term.id,
            status=TopicStatus.published,
            portrait_json={"keywords": ["a"], "extracted_at": ext},
            llm_keyword_job_id="job-uuid",
            llm_keyword_job_status=TopicKeywordJobStatus.done,
        )
        db.session.add(topic)
        db.session.commit()

        loaded = db.session.get(Topic, topic.id)
        assert loaded is not None
        body = loaded.to_topic()
        assert body["status"] == "published"
        assert body["portrait"] == {"keywords": ["a"], "extracted_at": ext}
        assert body["llm_keyword_job_id"] == "job-uuid"
        assert body["llm_keyword_job_status"] == "done"
