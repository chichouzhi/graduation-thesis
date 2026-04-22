from __future__ import annotations

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus


def _create_user(*, username: str, role: UserRole) -> User:
    user = User(
        username=username,
        role=role,
        display_name=username,
        password_hash=generate_password_hash("pass-123"),
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_term(name: str) -> Term:
    term = Term(name=name)
    db.session.add(term)
    db.session.commit()
    return term


def _create_topic(*, teacher_id: str, term_id: str, title: str, status: TopicStatus = TopicStatus.draft) -> Topic:
    topic = Topic(
        title=title,
        summary="summary",
        requirements="requirements",
        tech_keywords=[],
        capacity=2,
        selected_count=0,
        teacher_id=teacher_id,
        term_id=term_id,
        status=status,
        portrait_json={"keywords": [], "extracted_at": None},
    )
    db.session.add(topic)
    db.session.commit()
    return topic


def _login_and_get_token(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


def test_get_topics_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        caller = _create_user(username="topic-api-user", role=UserRole.teacher)
        teacher = _create_user(username="topic-api-owner", role=UserRole.teacher)
        term = _create_term("2049 春")
        _create_topic(teacher_id=teacher.id, term_id=term.id, title="AI Topic", status=TopicStatus.published)
        teacher_id = teacher.id
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-api-user", "pass-123")
    resp = client.get(
        f"/api/v1/topics?status=published&teacher_id={teacher_id}&term_id={term_id}&q=AI&page=1&page_size=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "AI Topic"


def test_get_topics_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-api-bad", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-api-bad", "pass-123")
    resp = client.get("/api/v1/topics?page=bad&page_size=20", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_topics_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/topics")
    assert resp.status_code == 401


def test_post_topics_success_201(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-topic-api"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-create-teacher", role=UserRole.teacher)
        teacher_id = teacher.id
        term = _create_term("2050 春")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-create-teacher", "pass-123")
    resp = client.post(
        "/api/v1/topics",
        json={
            "title": "New Topic",
            "summary": "Topic summary",
            "requirements": "Topic requirements",
            "capacity": 3,
            "term_id": term_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "New Topic"
    assert body["status"] == "draft"
    assert body["teacher_id"] == teacher_id
    assert body["term_id"] == term_id


def test_post_topics_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-create-bad", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-create-bad", "pass-123")
    resp = client.post("/api/v1/topics", json={"title": "x"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_topics_forbidden_non_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-create-student", role=UserRole.student)
        term = _create_term("2051 春")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-create-student", "pass-123")
    resp = client.post(
        "/api/v1/topics",
        json={
            "title": "Student Topic",
            "summary": "S",
            "requirements": "R",
            "capacity": 1,
            "term_id": term_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_topics_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/topics", json={})
    assert resp.status_code == 401


def test_get_topic_by_id_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-get-user", role=UserRole.teacher)
        teacher = _create_user(username="topic-get-owner", role=UserRole.teacher)
        term = _create_term("2052 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="Single Topic", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-get-user", "pass-123")
    resp = client.get(f"/api/v1/topics/{topic_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["id"] == topic_id


def test_get_topic_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-get-missing", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-get-missing", "pass-123")
    resp = client.get("/api/v1/topics/missing-topic-id", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_topic_by_id_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-get-bad", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-get-bad", "pass-123")
    resp = client.get("/api/v1/topics/%20%20", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_topic_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/topics/any-id")
    assert resp.status_code == 401


def test_patch_topic_by_id_success_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-patch"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-patch-owner", role=UserRole.teacher)
        term = _create_term("2053 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="Patch Me", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-patch-owner", "pass-123")
    resp = client.patch(
        f"/api/v1/topics/{topic_id}",
        json={"summary": "Updated summary"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == topic_id
    assert body["summary"] == "Updated summary"


def test_patch_topic_by_id_not_found_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-patch-miss"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-patch-miss", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-patch-miss", "pass-123")
    resp = client.patch(
        "/api/v1/topics/missing-topic-id",
        json={"summary": "X"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_patch_topic_by_id_forbidden_non_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-patch-teacher", role=UserRole.teacher)
        _create_user(username="topic-patch-student", role=UserRole.student)
        term = _create_term("2054 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="T", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-patch-student", "pass-123")
    resp = client.patch(
        f"/api/v1/topics/{topic_id}",
        json={"summary": "Hack"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_patch_topic_by_id_validation_error_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-patch-val"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-patch-val", role=UserRole.teacher)
        term = _create_term("2055 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="V", status=TopicStatus.published)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-patch-val", "pass-123")
    resp = client.patch(
        f"/api/v1/topics/{topic_id}",
        json={"summary": "No"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_topic_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.patch("/api/v1/topics/any-id", json={})
    assert resp.status_code == 401


def test_delete_topic_by_id_success_204() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-del-owner", role=UserRole.teacher)
        term = _create_term("2056 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="Del Me", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-del-owner", "pass-123")
    resp = client.delete(f"/api/v1/topics/{topic_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204
    assert resp.get_data(as_text=True) == ""

    get_resp = client.get(f"/api/v1/topics/{topic_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 200
    assert get_resp.get_json()["status"] == "closed"


def test_delete_topic_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-del-miss", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-del-miss", "pass-123")
    resp = client.delete("/api/v1/topics/missing-topic-id", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_delete_topic_by_id_forbidden_wrong_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        owner = _create_user(username="topic-del-owner2", role=UserRole.teacher)
        other = _create_user(username="topic-del-other", role=UserRole.teacher)
        term = _create_term("2057 春")
        topic = _create_topic(teacher_id=owner.id, term_id=term.id, title="Not Yours", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-del-other", "pass-123")
    resp = client.delete(f"/api/v1/topics/{topic_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_delete_topic_by_id_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-del-val", role=UserRole.teacher)
        term = _create_term("2058 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="Pub", status=TopicStatus.published)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-del-val", "pass-123")
    resp = client.delete(f"/api/v1/topics/{topic_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_topic_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.delete("/api/v1/topics/any-id")
    assert resp.status_code == 401


def test_post_topic_submit_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-submit-owner", role=UserRole.teacher)
        term = _create_term("2059 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="Submit Me", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-submit-owner", "pass-123")
    resp = client.post(f"/api/v1/topics/{topic_id}/submit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "pending_review"


def test_post_topic_submit_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-submit-miss", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-submit-miss", "pass-123")
    resp = client.post("/api/v1/topics/missing-topic-id/submit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_post_topic_submit_forbidden_wrong_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        owner = _create_user(username="topic-submit-owner2", role=UserRole.teacher)
        other = _create_user(username="topic-submit-other", role=UserRole.teacher)
        term = _create_term("2060 春")
        topic = _create_topic(teacher_id=owner.id, term_id=term.id, title="Not Yours", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-submit-other", "pass-123")
    resp = client.post(f"/api/v1/topics/{topic_id}/submit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_topic_submit_forbidden_student_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-submit-t", role=UserRole.teacher)
        _create_user(username="topic-submit-s", role=UserRole.student)
        term = _create_term("2061 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="S", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-submit-s", "pass-123")
    resp = client.post(f"/api/v1/topics/{topic_id}/submit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_topic_submit_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-submit-val", role=UserRole.teacher)
        term = _create_term("2062 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="V", status=TopicStatus.pending_review)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-submit-val", "pass-123")
    resp = client.post(f"/api/v1/topics/{topic_id}/submit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_topic_submit_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/topics/any-id/submit")
    assert resp.status_code == 401


def test_post_topic_review_approve_success_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-review-ap"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-rev-t", role=UserRole.teacher)
        _create_user(username="topic-rev-a", role=UserRole.admin)
        term = _create_term("2063 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="R1", status=TopicStatus.draft)
        topic.status = TopicStatus.pending_review
        db.session.commit()
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-rev-a", "pass-123")
    resp = client.post(
        f"/api/v1/topics/{topic_id}/review",
        json={"action": "approve", "comment": "ok"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == topic_id
    assert body["status"] == "published"


def test_post_topic_review_reject_success_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-review-rj"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-rev-t2", role=UserRole.teacher)
        admin = _create_user(username="topic-rev-a2", role=UserRole.admin)
        term = _create_term("2064 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="R2", status=TopicStatus.draft)
        topic.status = TopicStatus.pending_review
        db.session.commit()
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-rev-a2", "pass-123")
    resp = client.post(
        f"/api/v1/topics/{topic_id}/review",
        json={"action": "reject"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "rejected"


def test_post_topic_review_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="topic-rev-miss-a", role=UserRole.admin)

    client = app.test_client()
    token = _login_and_get_token(client, "topic-rev-miss-a", "pass-123")
    resp = client.post(
        "/api/v1/topics/missing-topic-id/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_post_topic_review_forbidden_teacher_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-review-t403"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-rev-t403", role=UserRole.teacher)
        term = _create_term("2065 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="R3", status=TopicStatus.draft)
        topic.status = TopicStatus.pending_review
        db.session.commit()
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-rev-t403", "pass-123")
    resp = client.post(
        f"/api/v1/topics/{topic_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_topic_review_validation_wrong_state_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-review-st"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-rev-t400", role=UserRole.teacher)
        admin = _create_user(username="topic-rev-a400", role=UserRole.admin)
        term = _create_term("2066 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="R4", status=TopicStatus.draft)
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-rev-a400", "pass-123")
    resp = client.post(
        f"/api/v1/topics/{topic_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_topic_review_validation_bad_comment_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.topic.service.topic_service.queue_mod.enqueue_keyword_jobs",
        lambda *_a, **_k: {"job_id": "k-review-cm"},
    )
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="topic-rev-tcm", role=UserRole.teacher)
        admin = _create_user(username="topic-rev-acm", role=UserRole.admin)
        term = _create_term("2067 春")
        topic = _create_topic(teacher_id=teacher.id, term_id=term.id, title="R5", status=TopicStatus.draft)
        topic.status = TopicStatus.pending_review
        db.session.commit()
        topic_id = topic.id

    client = app.test_client()
    token = _login_and_get_token(client, "topic-rev-acm", "pass-123")
    resp = client.post(
        f"/api/v1/topics/{topic_id}/review",
        json={"action": "approve", "comment": 99},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_topic_review_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/topics/any-id/review", json={"action": "approve"})
    assert resp.status_code == 401
