"""AG-002：``app/extensions.py`` 单例可 import，且在工厂中完成 init。"""
from __future__ import annotations


def test_extensions_symbols_importable() -> None:
    from app.extensions import db, jwt, migrate

    assert db is not None
    assert migrate is not None
    assert jwt is not None


def test_create_app_initializes_extensions() -> None:
    from app import create_app
    from app.common.policy import PolicyGateway
    from app.extensions import db

    app = create_app()
    with app.app_context():
        assert db.engine is not None
        assert app.extensions.get("policy_gateway") is PolicyGateway
