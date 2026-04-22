from __future__ import annotations

from werkzeug.security import generate_password_hash

from app import create_app
from app.chat.model import Conversation, Message, MessageRole
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term


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


def _create_conversation(*, user_id: str, term_id: str, title: str) -> Conversation:
    conv = Conversation(user_id=user_id, term_id=term_id, title=title)
    db.session.add(conv)
    db.session.commit()
    return conv


def _create_message(*, conversation_id: str, role: MessageRole, content: str) -> Message:
    msg = Message(conversation_id=conversation_id, role=role, content=content)
    db.session.add(msg)
    db.session.commit()
    return msg


def _login_and_get_token(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.get_json()["access_token"]


def test_get_conversations_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        mine = _create_user(username="chat-api-user", role=UserRole.student)
        other = _create_user(username="chat-api-other", role=UserRole.student)
        term = _create_term("2040 春")
        own = _create_conversation(user_id=mine.id, term_id=term.id, title="my-conv")
        _create_conversation(user_id=other.id, term_id=term.id, title="other-conv")
        own_id = own.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-user", "pass-123")
    resp = client.get("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == own_id


def test_get_conversations_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/conversations")
    assert resp.status_code == 401


def test_get_conversations_invalid_pagination_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-page", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-page", "pass-123")
    resp = client.get(
        "/api/v1/conversations?page=0&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_conversations_success_201() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-post", role=UserRole.student)
        term = _create_term("2041 春")
        term_id = term.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-post", "pass-123")
    resp = client.post(
        "/api/v1/conversations",
        json={
            "term_id": term_id,
            "title": "new-conv",
            "context_type": "topic",
            "context_ref_id": "topic-100",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["term_id"] == term_id
    assert body["title"] == "new-conv"
    assert body["context_type"] == "topic"
    assert body["context_ref_id"] == "topic-100"


def test_post_conversations_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-post-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-post-bad", "pass-123")
    resp = client.post(
        "/api/v1/conversations",
        json={"title": "missing-term-id"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_conversations_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/conversations", json={"term_id": "x"})
    assert resp.status_code == 401


def test_get_conversation_by_id_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-get-one", role=UserRole.student)
        term = _create_term("2042 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="single-conv")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-get-one", "pass-123")
    resp = client.get(
        f"/api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == conv_id
    assert body["title"] == "single-conv"


def test_get_conversation_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-get-missing", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-get-missing", "pass-123")
    resp = client.get(
        "/api/v1/conversations/missing-conversation-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_conversation_by_id_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-get-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-get-bad", "pass-123")
    resp = client.get(
        "/api/v1/conversations/%20%20%20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_conversation_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/conversations/some-conversation-id")
    assert resp.status_code == 401


def test_delete_conversation_by_id_success_204() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-del", role=UserRole.student)
        term = _create_term("2043 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="to-delete")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-del", "pass-123")
    resp = client.delete(
        f"/api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
    assert resp.get_data(as_text=True) == ""


def test_delete_conversation_by_id_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-del-missing", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-del-missing", "pass-123")
    resp = client.delete(
        "/api/v1/conversations/missing-conversation-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_delete_conversation_by_id_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-del-bad", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-del-bad", "pass-123")
    resp = client.delete(
        "/api/v1/conversations/%20%20%20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_conversation_by_id_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.delete("/api/v1/conversations/some-conversation-id")
    assert resp.status_code == 401


def test_get_conversation_messages_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-msg", role=UserRole.student)
        term = _create_term("2044 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="msg-conv")
        _create_message(conversation_id=conv.id, role=MessageRole.user, content="u1")
        _create_message(conversation_id=conv.id, role=MessageRole.assistant, content="a1")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-msg", "pass-123")
    resp = client.get(
        f"/api/v1/conversations/{conv_id}/messages?page=1&page_size=10&order=asc",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_get_conversation_messages_cursor_conflict_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-msg-cursor", role=UserRole.student)
        term = _create_term("2044 秋")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="cursor-conv")
        m1 = _create_message(conversation_id=conv.id, role=MessageRole.user, content="u1")
        m2 = _create_message(conversation_id=conv.id, role=MessageRole.assistant, content="a1")
        conv_id = conv.id
        m1_id = m1.id
        m2_id = m2.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-msg-cursor", "pass-123")
    resp = client.get(
        f"/api/v1/conversations/{conv_id}/messages?after_message_id={m1_id}&before_message_id={m2_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_conversation_messages_invalid_pagination_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        _create_user(username="chat-api-msg-page", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-msg-page", "pass-123")
    resp = client.get(
        "/api/v1/conversations/some-conv/messages?page=bad&page_size=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_conversation_messages_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/v1/conversations/some-conv/messages")
    assert resp.status_code == 401


def test_post_conversation_messages_success_202() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-post-msg", role=UserRole.student)
        term = _create_term("2045 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="post-msg-conv")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-post-msg", "pass-123")
    resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "hello", "client_request_id": "req-1", "seq": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["job_id"]
    assert body["user_message"]["conversation_id"] == conv_id
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "hello"
    assert body["assistant_message"]["conversation_id"] == conv_id
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["status"] == "pending"


def test_post_conversation_messages_validation_error_400() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-post-msg-bad", role=UserRole.student)
        term = _create_term("2045 秋")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="post-msg-bad-conv")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-post-msg-bad", "pass-123")
    resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_post_conversation_messages_requires_access_token() -> None:
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/v1/conversations/some-conv/messages", json={"content": "x"})
    assert resp.status_code == 401


def test_get_chat_job_success_200() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-job", role=UserRole.student)
        term = _create_term("2046 春")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="job-conv")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-job", "pass-123")
    post = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "ping"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post.status_code == 202
    job_id = post.get_json()["job_id"]

    get = client.get(f"/api/v1/chat/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
    assert get.status_code == 200
    body = get.get_json()
    assert body["job_id"] == job_id
    assert body["conversation_id"] == conv_id
    assert body["status"] == "pending"


def test_get_chat_job_not_found_404() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-job-miss", role=UserRole.student)

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-job-miss", "pass-123")
    resp = client.get(
        "/api/v1/chat/jobs/00000000-0000-4000-8000-000000000001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_get_conversation_stream_sse_not_enabled_501() -> None:
    app = create_app()
    app.config["REFRESH_TOKEN_COOKIE_SECURE"] = False
    with app.app_context():
        db.create_all()
        user = _create_user(username="chat-api-sse", role=UserRole.student)
        term = _create_term("2046 秋")
        conv = _create_conversation(user_id=user.id, term_id=term.id, title="sse-conv")
        conv_id = conv.id

    client = app.test_client()
    token = _login_and_get_token(client, "chat-api-sse", "pass-123")
    resp = client.get(f"/api/v1/conversations/{conv_id}/stream", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 501
    assert resp.get_json()["error"]["code"] == "SSE_NOT_ENABLED"
