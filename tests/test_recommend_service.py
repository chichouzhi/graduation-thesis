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
        assert body["items"][0]["score"] == 1.0
        expl = body["items"][0]["explain"]
        assert expl is not None
        assert set(expl["matched_skills"]) == {"nlp", "python"}
        assert expl["matched_keywords"] == []


def test_recommend_uses_portrait_json_keywords() -> None:
    """课题仅画像有关键词、``tech_keywords`` 为空时仍参与只读打分（AG-016 列）。"""
    app = create_app()
    with app.app_context():
        db.create_all()
        student = User(
            username="rec-portrait-stu",
            role=UserRole.student,
            display_name="s",
            student_profile={"skills": ["rust", "wasm"]},
        )
        teacher = User(username="rec-portrait-tea", role=UserRole.teacher, display_name="t")
        db.session.add_all([student, teacher])
        db.session.commit()
        term = Term(name="portrait-term")
        db.session.add(term)
        db.session.commit()
        db.session.add_all(
            [
                Topic(
                    title="Systems",
                    summary="s",
                    requirements="r",
                    tech_keywords=[],
                        portrait_json={"keywords": ["rust"]},
                    capacity=3,
                    selected_count=0,
                    teacher_id=teacher.id,
                    term_id=term.id,
                    status=TopicStatus.published,
                ),
                Topic(
                    title="Web only",
                    summary="s",
                    requirements="r",
                    tech_keywords=["css"],
                    portrait_json=None,
                    capacity=3,
                    selected_count=0,
                    teacher_id=teacher.id,
                    term_id=term.id,
                    status=TopicStatus.published,
                ),
            ]
        )
        db.session.commit()
        body = RecommendService().recommend_topics_for_student(
            student.id, term_id=term.id, top_n=2, explain=False
        )
        assert body["items"][0]["title"] == "Systems"
        assert body["items"][0]["score"] == 0.5
        assert body["items"][1]["title"] == "Web only"
        assert body["items"][1]["score"] == 0.0


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
