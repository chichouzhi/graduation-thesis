"""AG-003 / R-NO-QUEUE：production 缺 broker URL 时 ``create_app`` 失败。"""
from __future__ import annotations

import pytest


def test_production_without_broker_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(RuntimeError, match="R-NO-QUEUE"):
        create_app()


def test_production_with_broker_url_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/0")

    app = create_app()
    assert app.config["BROKER_URL"] == "redis://localhost:6379/0"


def test_production_accepts_redis_url_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("BROKER_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/1")

    app = create_app()
    assert app.config["BROKER_URL"] == "redis://redis:6379/1"


def test_explicit_production_config_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    monkeypatch.delenv("BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(RuntimeError, match="R-NO-QUEUE"):
        create_app(config=ProductionConfig)
