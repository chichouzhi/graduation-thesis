from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term, TermLlmConfig


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


def _create_term(name: str, *, created_at: datetime) -> Term:
    term = Term(name=name, created_at=created_at)
    db.session.add(term)
    db.session.commit()
    return term


def _login_and_get_token(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


def test_get_terms_teacher_sees_all_terms() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="teacher-api", role=UserRole.teacher)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        _create_term("2026 春", created_at=base)
        _create_term("2026 秋", created_at=base + timedelta(seconds=1))

    client = app.test_client()
    token = _login_and_get_token(client, "teacher-api", "pass-123")
    resp = client.get("/api/v1/terms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 2


def test_get_terms_student_sees_latest_term_only() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="student-api", role=UserRole.student)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        _create_term("2027 春", created_at=base)
        latest = _create_term("2027 秋", created_at=base + timedelta(seconds=1))
        latest_id = latest.id

    client = app.test_client()
    token = _login_and_get_token(client, "student-api", "pass-123")
    resp = client.get("/api/v1/terms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == latest_id


def test_get_terms_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/terms")
    assert resp.status_code == 401


def test_post_terms_admin_success_201() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-api", role=UserRole.admin)

    client = app.test_client()
    token = _login_and_get_token(client, "admin-api", "pass-123")
    payload = {
        "name": "2028 春",
        "selection_start_at": "2028-03-01T00:00:00Z",
        "selection_end_at": "2028-03-31T00:00:00Z",
    }
    resp = client.post("/api/v1/terms", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "2028 春"
    assert body["selection_start_at"] == "2028-03-01T00:00:00Z"
    assert body["selection_end_at"] == "2028-03-31T00:00:00Z"


def test_post_terms_forbidden_for_non_admin_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="teacher-no-admin", role=UserRole.teacher)

    client = app.test_client()
    token = _login_and_get_token(client, "teacher-no-admin", "pass-123")
    resp = client.post(
        "/api/v1/terms",
        json={"name": "2028 秋"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_post_terms_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-bad-payload", role=UserRole.admin)

    client = app.test_client()
    token = _login_and_get_token(client, "admin-bad-payload", "pass-123")
    resp = client.post(
        "/api/v1/terms",
        json={"name": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_terms_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/terms", json={"name": "2029 春"})
    assert resp.status_code == 401


def test_get_term_by_id_teacher_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="teacher-get-term", role=UserRole.teacher)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        target = _create_term("2030 春", created_at=base)
        target_id = target.id

    client = app.test_client()
    token = _login_and_get_token(client, "teacher-get-term", "pass-123")
    resp = client.get(f"/api/v1/terms/{target_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["id"] == target_id


def test_get_term_by_id_student_non_latest_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="student-get-term", role=UserRole.student)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        older = _create_term("2031 春", created_at=base)
        _create_term("2031 秋", created_at=base + timedelta(seconds=1))
        older_id = older.id

    client = app.test_client()
    token = _login_and_get_token(client, "student-get-term", "pass-123")
    resp = client.get(f"/api/v1/terms/{older_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_term_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/terms/some-term-id")
    assert resp.status_code == 401


def test_patch_term_by_id_admin_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-patch-term", role=UserRole.admin)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2032 春", created_at=base)
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "admin-patch-term", "pass-123")
    resp = client.patch(
        f"/api/v1/terms/{term_id}",
        json={"name": "2032 秋", "selection_end_at": "2032-12-31T00:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == term_id
    assert body["name"] == "2032 秋"
    assert body["selection_end_at"] == "2032-12-31T00:00:00Z"


def test_patch_term_by_id_forbidden_non_admin_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="teacher-patch-term", role=UserRole.teacher)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2033 春", created_at=base)
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "teacher-patch-term", "pass-123")
    resp = client.patch(
        f"/api/v1/terms/{term_id}",
        json={"name": "forbidden-change"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_patch_term_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-patch-missing", role=UserRole.admin)

    client = app.test_client()
    token = _login_and_get_token(client, "admin-patch-missing", "pass-123")
    resp = client.patch(
        "/api/v1/terms/missing-term-id",
        json={"name": "does-not-matter"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_patch_term_by_id_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-patch-invalid", role=UserRole.admin)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2034 春", created_at=base)
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "admin-patch-invalid", "pass-123")
    resp = client.patch(
        f"/api/v1/terms/{term_id}",
        json={"selection_start_at": "not-a-datetime"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_term_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.patch("/api/v1/terms/some-term-id", json={"name": "x"})
    assert resp.status_code == 401


def test_get_term_llm_config_teacher_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="teacher-llm-config", role=UserRole.teacher)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2035 春", created_at=base)
        term_id = term.id
        db.session.add(
            TermLlmConfig(
                term_id=term_id,
                provider="openai-compatible",
                daily_budget_tokens=50000,
                per_user_daily_tokens=2000,
            )
        )
        db.session.commit()

    client = app.test_client()
    token = _login_and_get_token(client, "teacher-llm-config", "pass-123")
    resp = client.get(f"/api/v1/terms/{term_id}/llm-config", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json() == {
        "provider": "openai-compatible",
        "daily_budget_tokens": 50000,
        "per_user_daily_tokens": 2000,
    }


def test_get_term_llm_config_student_non_visible_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="student-llm-config", role=UserRole.student)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        older = _create_term("2036 春", created_at=base)
        _create_term("2036 秋", created_at=base + timedelta(seconds=1))
        older_id = older.id

    client = app.test_client()
    token = _login_and_get_token(client, "student-llm-config", "pass-123")
    resp = client.get(
        f"/api/v1/terms/{older_id}/llm-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_term_llm_config_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/terms/some-term-id/llm-config")
    assert resp.status_code == 401


def test_patch_term_llm_config_admin_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-patch-llm", role=UserRole.admin)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2037 春", created_at=base)
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "admin-patch-llm", "pass-123")
    resp = client.patch(
        f"/api/v1/terms/{term_id}/llm-config",
        json={
            "provider": "openai-compatible",
            "daily_budget_tokens": 80000,
            "per_user_daily_tokens": 3000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {
        "provider": "openai-compatible",
        "daily_budget_tokens": 80000,
        "per_user_daily_tokens": 3000,
    }


def test_patch_term_llm_config_forbidden_non_admin_403() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="teacher-patch-llm", role=UserRole.teacher)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2038 春", created_at=base)
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "teacher-patch-llm", "pass-123")
    resp = client.patch(
        f"/api/v1/terms/{term_id}/llm-config",
        json={"provider": "openai-compatible"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_patch_term_llm_config_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-patch-llm-missing", role=UserRole.admin)

    client = app.test_client()
    token = _login_and_get_token(client, "admin-patch-llm-missing", "pass-123")
    resp = client.patch(
        "/api/v1/terms/missing-term-id/llm-config",
        json={"provider": "openai-compatible"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_patch_term_llm_config_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="admin-patch-llm-invalid", role=UserRole.admin)
        base = datetime.now(timezone.utc).replace(tzinfo=None)
        term = _create_term("2039 春", created_at=base)
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "admin-patch-llm-invalid", "pass-123")
    resp = client.patch(
        f"/api/v1/terms/{term_id}/llm-config",
        json={"daily_budget_tokens": -1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_term_llm_config_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.patch("/api/v1/terms/some-term-id/llm-config", json={"provider": "x"})
    assert resp.status_code == 401
