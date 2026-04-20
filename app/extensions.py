"""Flask 扩展单例：数据库、迁移、JWT（AG-002）。

各层可按 ``spec/architecture.spec.md`` §1.3 引用本模块；初始化在应用工厂内完成。
``policy_gateway``（AG-006）：入队前 Policy 门面依赖注入，默认 ``app.common.policy.PolicyGateway``。
"""
from __future__ import annotations

from typing import Any

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    """SQLite 默认关闭外键；启用后 ``ON DELETE CASCADE`` 等与 PostgreSQL 语义一致。"""
    try:
        from sqlite3 import Connection as SQLiteConnection
    except ImportError:
        return
    if not isinstance(dbapi_connection, SQLiteConnection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
migrate = Migrate()
jwt = JWTManager()


def init_extensions(app: Flask) -> None:
    """将 ``db`` / ``migrate`` / ``jwt`` 绑定到给定 ``Flask`` 实例。"""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app.common.policy import PolicyGateway

    app.extensions["policy_gateway"] = PolicyGateway


def get_policy_gateway() -> Any:
    """返回当前 App 注册的 Policy 门面（类或实例，须提供 ``assert_can_enqueue``）。

    无应用上下文时回退到默认 :class:`app.common.policy.PolicyGateway`，便于脚本与单测。
    """
    from flask import has_app_context, current_app

    from app.common.policy import PolicyGateway

    if has_app_context():
        return current_app.extensions.get("policy_gateway", PolicyGateway)
    return PolicyGateway
