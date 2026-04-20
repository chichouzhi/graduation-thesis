"""Flask 配置对象。

生产环境 broker URL 等强校验见任务图 AG-003；本文件仅提供工厂可加载的最小配置。
"""
from __future__ import annotations

import os
from typing import Final

# 与队列客户端对齐：优先显式 broker，其次常见 Redis 直连 URL（R-NO-QUEUE）
_ENV_BROKER_KEYS: Final[tuple[str, ...]] = ("BROKER_URL", "REDIS_URL")


class Config:
    """默认配置（开发可用环境变量覆盖）。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
    TESTING = False

    # Flask-SQLAlchemy / Flask-Migrate（AG-002）
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-JWT-Extended
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        os.environ.get("SECRET_KEY", "dev-only-change-in-production"),
    )


class ProductionConfig(Config):
    """生产：必须配置 broker，否则进程不得启动（architecture.spec R-NO-QUEUE）。"""

    DEBUG = False


def broker_url_from_environ() -> str:
    """从环境变量读取 broker URL（去首尾空白）；未配置则为空串。"""
    for key in _ENV_BROKER_KEYS:
        raw = os.environ.get(key)
        if raw is not None and raw.strip():
            return raw.strip()
    return ""


def validate_production_broker(config_class: type[Config]) -> None:
    """若选用 ProductionConfig，则要求非空 broker URL，否则抛错使工厂失败。"""
    if config_class is not ProductionConfig:
        return
    if not broker_url_from_environ():
        raise RuntimeError(
            "R-NO-QUEUE: FLASK_ENV=production requires a non-empty BROKER_URL or "
            "REDIS_URL (queue + worker is mandatory; see spec/architecture.spec.md)."
        )


def get_config_class() -> type[Config]:
    """按 FLASK_ENV 选择配置类；``production`` 使用 ProductionConfig。"""
    env = os.environ.get("FLASK_ENV", "").strip().lower()
    if env == "production":
        return ProductionConfig
    return Config


__all__ = [
    "Config",
    "ProductionConfig",
    "broker_url_from_environ",
    "get_config_class",
    "validate_production_broker",
]
