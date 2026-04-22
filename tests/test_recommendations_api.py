from __future__ import annotations

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus


def _create_user(*, username: str, role: UserRole, student_profile: dict | None = None) -> User:
    user = User(
        username=username,
        role=role,
        display_name=username,
        password_hash=generate_password_hash("pass-123"),
        student_profile=student_profile,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_term(name: str) -> Term:
    term = Term(name=name)
    db.session.add(term)
    db.session.commit()
    return term


def _create_topic(*, teacher_id: str, term_id: str, title: str, keywords: list[str]) -> Topic:
    topic = Topic(
        title=title,
        summary="S",
        requirements="R",
        tech_keywords=keywords,
        capacity=3,
        selected_count=0,
        teacher_id=teacher_id,
        term_id=term_id,
        status=TopicStatus.published,
        portrait_json=None,
    )
    db.session.add(topic)
    db.session.commit()
    return topic


def _login_and_get_token(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


def test_get_recommendation_topics_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(
            username="rec-api-stu",
            role=UserRole.student,
            student_profile={"skills": ["python", "nlp"]},
        )
        teacher = _create_user(username="rec-api-tea", role=UserRole.teacher)
        term = _create_term("rec-api-term")
        _create_topic(teacher_id=teacher.id, term_id=term.id, title="NLP", keywords=["python", "nlp"])
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "rec-api-stu", "pass-123")
    resp = client.get(
        f"/api/v1/recommendations/topics?term_id={term_id}&top_n=5&explain=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["top_n"] == 5
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "NLP"
    assert "explain" in body["items"][0]


def test_get_recommendation_topics_forbidden_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="rec-api-tea2", role=UserRole.teacher)
        term = _create_term("rec-api-term2")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "rec-api-tea2", "pass-123")
    resp = client.get(
        f"/api/v1/recommendations/topics?term_id={term_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_get_recommendation_topics_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="rec-api-stu-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "rec-api-stu-bad", "pass-123")
    resp = client.get(
        "/api/v1/recommendations/topics?term_id=t1&top_n=bad",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_recommendation_topics_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/recommendations/topics?term_id=t1")
    assert resp.status_code == 401
