"""AG-001：应用工厂与「无 /api/v1 业务域路由」边界。"""
from __future__ import annotations


def test_create_app_returns_flask_app() -> None:
    from app import create_app

    app = create_app()
    assert app.name == "app"


def test_ag004_eight_domain_blueprints_registered() -> None:
    """AG-004：``/api/v1`` 下八大域 Blueprint 已注册（路由文件可空，端点由后续任务补齐）。"""
    from app import create_app

    app = create_app()
    expected = {
        "identity",
        "terms",
        "taskboard",
        "chat",
        "document",
        "topic",
        "selection",
        "recommendations",
    }
    assert expected == set(app.blueprints.keys())
    for name in expected:
        assert app.blueprints[name].url_prefix == "/api/v1"


def test_health_and_root() -> None:
    from app import create_app

    client = create_app().test_client()
    h = client.get("/health")
    assert h.status_code == 200
    assert h.get_json() == {"status": "healthy"}
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_json()
    assert body is not None
    assert body.get("status") == "ok"
