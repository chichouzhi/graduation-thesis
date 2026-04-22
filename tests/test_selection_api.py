from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.selection.model import Application, ApplicationFlowStatus, Assignment, AssignmentStatus
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


def _create_term_in_window(*, name: str) -> Term:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    term = Term(
        name=name,
        selection_start_at=now - timedelta(days=1),
        selection_end_at=now + timedelta(days=1),
    )
    db.session.add(term)
    db.session.commit()
    return term


def _create_published_topic(*, teacher_id: str, term_id: str, title: str) -> Topic:
    topic = Topic(
        title=title,
        summary="S",
        requirements="R",
        tech_keywords=[],
        capacity=2,
        selected_count=0,
        teacher_id=teacher_id,
        term_id=term_id,
        status=TopicStatus.published,
        portrait_json={"keywords": [], "extracted_at": None},
    )
    db.session.add(topic)
    db.session.commit()
    return topic


def _login_and_get_token(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


def test_post_applications_success_201() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-api-stu", role=UserRole.student)
        teacher = _create_user(username="sel-api-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-api-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Sel Topic")
        topic_id = topic.id
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-api-stu", "pass-123")
    resp = client.post(
        "/api/v1/applications",
        json={"topic_id": topic_id, "term_id": term_id, "priority": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["topic_id"] == topic_id
    assert body["term_id"] == term_id
    assert body["priority"] == 1
    assert body["status"] == "pending"


def test_post_applications_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-api-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-api-bad", "pass-123")
    resp = client.post("/api/v1/applications", json={}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_applications_forbidden_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        teacher = _create_user(username="sel-api-tea403", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-api-term403")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="T403")
        topic_id = topic.id
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-api-tea403", "pass-123")
    resp = client.post(
        "/api/v1/applications",
        json={"topic_id": topic_id, "term_id": term_id, "priority": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_applications_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/applications", json={})
    assert resp.status_code == 401


def test_post_applications_conflict_uniqueness_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-api-dup", role=UserRole.student)
        teacher = _create_user(username="sel-api-tea-dup", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-dup-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Dup Topic")
        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic.id,
                priority=1,
                status=ApplicationFlowStatus.pending,
            )
        )
        db.session.commit()
        topic_id = topic.id
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-api-dup", "pass-123")
    resp = client.post(
        "/api/v1/applications",
        json={"topic_id": topic_id, "term_id": term_id, "priority": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "uniqueness" in resp.get_json()["error"]["message"].lower()


def test_post_applications_selection_window_closed_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-api-closed", role=UserRole.student)
        teacher = _create_user(username="sel-api-tea-closed", role=UserRole.teacher)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="closed-term",
            selection_start_at=now - timedelta(days=30),
            selection_end_at=now - timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Closed Topic")
        topic_id = topic.id
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-api-closed", "pass-123")
    resp = client.post(
        "/api/v1/applications",
        json={"topic_id": topic_id, "term_id": term_id, "priority": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_get_applications_success_200_student() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-get-stu", role=UserRole.student)
        teacher = _create_user(username="sel-get-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-get-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Sel Get")
        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic.id,
                priority=1,
                status=ApplicationFlowStatus.pending,
            )
        )
        db.session.commit()
        student_id = student.id
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-get-stu", "pass-123")
    resp = client.get(
        f"/api/v1/applications?term_id={term_id}&page=1&page_size=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["student_id"] == student_id


def test_get_applications_teacher_topic_filter_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-get-stu2", role=UserRole.student)
        teacher_a = _create_user(username="sel-get-tea-a", role=UserRole.teacher)
        teacher_b = _create_user(username="sel-get-tea-b", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-get-term2")
        topic_a = _create_published_topic(teacher_id=teacher_a.id, term_id=term.id, title="TA")
        topic_b = _create_published_topic(teacher_id=teacher_b.id, term_id=term.id, title="TB")
        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic_a.id,
                priority=1,
                status=ApplicationFlowStatus.pending,
            )
        )
        db.session.add(
            Application(
                student_id=student.id,
                term_id=term.id,
                topic_id=topic_b.id,
                priority=2,
                status=ApplicationFlowStatus.pending,
            )
        )
        db.session.commit()
        topic_a_id = topic_a.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-get-tea-a", "pass-123")
    resp = client.get(
        f"/api/v1/applications?topic_id={topic_a_id}&page=1&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["topic_id"] == topic_a_id


def test_get_applications_invalid_pagination_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-get-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-get-bad", "pass-123")
    resp = client.get("/api/v1/applications?page=bad&page_size=20", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_applications_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 401


def test_delete_application_success_204() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-del-stu", role=UserRole.student)
        teacher = _create_user(username="sel-del-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-del-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Sel Del")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-del-stu", "pass-123")
    resp = client.delete(f"/api/v1/applications/{application_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204
    assert resp.get_data(as_text=True) == ""


def test_delete_application_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-del-miss", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-del-miss", "pass-123")
    resp = client.delete("/api/v1/applications/missing-id", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_delete_application_forbidden_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-del-stu2", role=UserRole.student)
        teacher = _create_user(username="sel-del-tea403", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-del-term403")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Sel403")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-del-tea403", "pass-123")
    resp = client.delete(f"/api/v1/applications/{application_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_delete_application_validation_non_pending_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-del-stu400", role=UserRole.student)
        teacher = _create_user(username="sel-del-tea400", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-del-term400")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Sel400")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.accepted,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-del-stu400", "pass-123")
    resp = client.delete(f"/api/v1/applications/{application_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_application_selection_window_closed_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-del-stu-closed", role=UserRole.student)
        teacher = _create_user(username="sel-del-tea-closed", role=UserRole.teacher)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        term = Term(
            name="sel-del-closed-term",
            selection_start_at=now - timedelta(days=30),
            selection_end_at=now - timedelta(days=1),
        )
        db.session.add(term)
        db.session.commit()
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelClosed")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-del-stu-closed", "pass-123")
    resp = client.delete(f"/api/v1/applications/{application_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_delete_application_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.delete("/api/v1/applications/any-id")
    assert resp.status_code == 401


def test_patch_application_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-patch-stu", role=UserRole.student)
        teacher = _create_user(username="sel-patch-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-patch-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelPatch")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-patch-stu", "pass-123")
    resp = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == application_id
    assert body["priority"] == 2


def test_patch_application_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-patch-miss", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-patch-miss", "pass-123")
    resp = client.patch(
        "/api/v1/applications/missing-id",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_patch_application_forbidden_teacher_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-patch-stu403", role=UserRole.student)
        teacher = _create_user(username="sel-patch-tea403", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-patch-term403")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelPatch403")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-patch-tea403", "pass-123")
    resp = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_patch_application_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-patch-stu400", role=UserRole.student)
        teacher = _create_user(username="sel-patch-tea400", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-patch-term400")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelPatch400")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-patch-stu400", "pass-123")
    resp = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"priority": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_application_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.patch("/api/v1/applications/any-id", json={"priority": 1})
    assert resp.status_code == 401


def test_post_application_decision_accept_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-dec-stu", role=UserRole.student)
        teacher = _create_user(username="sel-dec-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-dec-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelDecision")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-dec-tea", "pass-123")
    resp = client.post(
        f"/api/v1/applications/{application_id}/decisions",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["application"]["status"] == "accepted"
    assert body["assignment"] is not None


def test_post_application_decision_reject_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-dec-stu2", role=UserRole.student)
        teacher = _create_user(username="sel-dec-tea2", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-dec-term2")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelDecision2")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-dec-tea2", "pass-123")
    resp = client.post(
        f"/api/v1/applications/{application_id}/decisions",
        json={"action": "reject"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["application"]["status"] == "rejected"
    assert body["assignment"] is None


def test_post_application_decision_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-dec-miss", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-dec-miss", "pass-123")
    resp = client.post(
        "/api/v1/applications/missing-id/decisions",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_post_application_decision_forbidden_student_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-dec-stu403", role=UserRole.student)
        teacher = _create_user(username="sel-dec-tea403", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-dec-term403")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelDecision403")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-dec-stu403", "pass-123")
    resp = client.post(
        f"/api/v1/applications/{application_id}/decisions",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_application_decision_capacity_exceeded_409() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-dec-stu409", role=UserRole.student)
        teacher = _create_user(username="sel-dec-tea409", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-dec-term409")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelDecision409")
        topic.capacity = 0
        db.session.commit()
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-dec-tea409", "pass-123")
    resp = client.post(
        f"/api/v1/applications/{application_id}/decisions",
        json={"action": "accept"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "CAPACITY_EXCEEDED"


def test_post_application_decision_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-dec-stu400", role=UserRole.student)
        teacher = _create_user(username="sel-dec-tea400", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-dec-term400")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="SelDecision400")
        row = Application(
            student_id=student.id,
            term_id=term.id,
            topic_id=topic.id,
            priority=1,
            status=ApplicationFlowStatus.pending,
        )
        db.session.add(row)
        db.session.commit()
        application_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-dec-tea400", "pass-123")
    resp = client.post(
        f"/api/v1/applications/{application_id}/decisions",
        json={"action": "unknown"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_application_decision_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/applications/any-id/decisions", json={"action": "accept"})
    assert resp.status_code == 401


def test_get_assignments_success_200_student() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-asg-stu", role=UserRole.student)
        teacher = _create_user(username="sel-asg-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-asg-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="Asg")
        row = Assignment(
            student_id=student.id,
            teacher_id=teacher.id,
            topic_id=topic.id,
            term_id=term.id,
            status=AssignmentStatus.active,
        )
        db.session.add(row)
        db.session.commit()
        student_id = student.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-asg-stu", "pass-123")
    resp = client.get("/api/v1/assignments?page=1&page_size=10", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 1
    assert body["items"][0]["student_id"] == student_id


def test_get_assignments_success_200_teacher() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-asg-stu2", role=UserRole.student)
        teacher_a = _create_user(username="sel-asg-tea-a", role=UserRole.teacher)
        teacher_b = _create_user(username="sel-asg-tea-b", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-asg-term2")
        topic_a = _create_published_topic(teacher_id=teacher_a.id, term_id=term.id, title="AsgA")
        topic_b = _create_published_topic(teacher_id=teacher_b.id, term_id=term.id, title="AsgB")
        db.session.add(
            Assignment(
                student_id=student.id,
                teacher_id=teacher_a.id,
                topic_id=topic_a.id,
                term_id=term.id,
                status=AssignmentStatus.active,
            )
        )
        db.session.add(
            Assignment(
                student_id=student.id,
                teacher_id=teacher_b.id,
                topic_id=topic_b.id,
                term_id=term.id,
                status=AssignmentStatus.active,
            )
        )
        db.session.commit()
        teacher_a_id = teacher_a.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-asg-tea-a", "pass-123")
    resp = client.get("/api/v1/assignments", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["teacher_id"] == teacher_a_id


def test_get_assignments_invalid_pagination_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-asg-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-asg-bad", "pass-123")
    resp = client.get("/api/v1/assignments?page=bad&page_size=20", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_assignments_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/assignments")
    assert resp.status_code == 401


def test_get_assignment_by_id_success_200_student() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        student = _create_user(username="sel-asg-get-stu", role=UserRole.student)
        teacher = _create_user(username="sel-asg-get-tea", role=UserRole.teacher)
        term = _create_term_in_window(name="sel-asg-get-term")
        topic = _create_published_topic(teacher_id=teacher.id, term_id=term.id, title="AsgGet")
        row = Assignment(
            student_id=student.id,
            teacher_id=teacher.id,
            topic_id=topic.id,
            term_id=term.id,
            status=AssignmentStatus.active,
        )
        db.session.add(row)
        db.session.commit()
        assignment_id = row.id

    client = app.test_client()
    token = _login_and_get_token(client, "sel-asg-get-stu", "pass-123")
    resp = client.get(f"/api/v1/assignments/{assignment_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["id"] == assignment_id


def test_get_assignment_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-asg-get-miss", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-asg-get-miss", "pass-123")
    resp = client.get("/api/v1/assignments/missing-id", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_assignment_by_id_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="sel-asg-get-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "sel-asg-get-bad", "pass-123")
    resp = client.get("/api/v1/assignments/%20%20", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_assignment_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/assignments/any-id")
    assert resp.status_code == 401
