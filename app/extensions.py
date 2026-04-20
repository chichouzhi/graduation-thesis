"""Flask 扩展单例：数据库、迁移、JWT（AG-002）。

各层可按 ``spec/architecture.spec.md`` §1.3 引用本模块；初始化在应用工厂内完成。
"""
from __future__ import annotations

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def init_extensions(app: Flask) -> None:
    """将 ``db`` / ``migrate`` / ``jwt`` 绑定到给定 ``Flask`` 实例。"""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
