from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.recommendations.service.recommend_service import RecommendService
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus


def test_recommend_top_n_and_explain() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        student = User(
            username="rec-student",
            role=UserRole.student,
            display_name="s",
            student_profile={"skills": ["python", "nlp"]},
        )
        teacher = User(username="rec-teacher", role=UserRole.teacher, display_name="t")
        db.session.add_all([student, teacher])
        db.session.commit()
        term = Term(name="2026")
        db.session.add(term)
        db.session.commit()
        db.session.add_all(
            [
                Topic(
                    title="NLP A",
                    summary="s",
                    requirements="r",
                    tech_keywords=["nlp", "python"],
                    capacity=5,
                    selected_count=0,
                    teacher_id=teacher.id,
                    term_id=term.id,
                    status=TopicStatus.published,
                ),
                Topic(
                    title="Other",
                    summary="s",
                    requirements="r",
                    tech_keywords=["java"],
                    capacity=5,
                    selected_count=0,
                    teacher_id=teacher.id,
                    term_id=term.id,
                    status=TopicStatus.published,
                ),
            ]
        )
        db.session.commit()
        body = RecommendService().recommend_topics_for_student(student.id, term_id=term.id, top_n=1, explain=True)
        assert body["top_n"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["title"] == "NLP A"
        assert body["items"][0]["explain"] is not None


def test_recommend_role_guard() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        teacher = User(username="rec-teacher-2", role=UserRole.teacher, display_name="t")
        term = Term(name="2027")
        db.session.add_all([teacher, term])
        db.session.commit()
        with pytest.raises(PermissionError):
            RecommendService().recommend_topics_for_student(teacher.id, term_id=term.id)
