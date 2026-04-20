"""Application root package.

分层目录（architecture.spec §0；非 ``app/api`` 单包）：

* **api** — ``app.<domain>.api``（如 ``app.chat.api``）
* **service** — ``app.<domain>.service``
* **model** — ``app.<domain>.model`` 与 ``app.model``
* **use_cases** — ``app.use_cases``
* **task** — ``app.task``（含 ``queue``、``*_jobs``）
* **adapter** — ``app.adapter``（含 ``llm`` 等）
* **worker** — ``app.worker``（进程语义占位，与 ``PROC_WORKER`` 对齐）
"""
from __future__ import annotations

from flask import Flask

from app.config import Config, ProductionConfig, broker_url_from_environ, get_config_class, validate_production_broker
from app.extensions import init_extensions


def _register_api_blueprints(app: Flask) -> None:
    """AG-004：挂载 ``/api/v1`` 下八大域 Blueprint 空壳（路由见各域 ``routes.py``）。"""
    from app.chat.api import bp as chat_bp
    from app.document.api import bp as document_bp
    from app.identity.api import bp as identity_bp
    from app.recommendations.api import bp as recommendations_bp
    from app.selection.api import bp as selection_bp
    from app.taskboard.api import bp as taskboard_bp
    from app.terms.api import bp as terms_bp
    from app.topic.api import bp as topic_bp

    for blueprint in (
        identity_bp,
        terms_bp,
        taskboard_bp,
        chat_bp,
        document_bp,
        topic_bp,
        selection_bp,
        recommendations_bp,
    ):
        app.register_blueprint(blueprint)


def create_app(config: type[Config] | None = None) -> Flask:
    """Flask 应用工厂。

    AG-001：非业务域路由（``/``、``/health``）。AG-004：``/api/v1`` 下八大域 Blueprint 空壳。
    **app/extensions.py** 扩展挂载见 **AG-002**。
    """
    app = Flask(__name__)
    cfg = config or get_config_class()
    validate_production_broker(cfg)
    app.config.from_object(cfg)
    if cfg is ProductionConfig:
        app.config["BROKER_URL"] = broker_url_from_environ()
    init_extensions(app)
    from app.identity import model as _identity_model  # noqa: F401 — register ``users`` ORM (AG-008)
    from app.terms import model as _terms_model  # noqa: F401 — register ``terms`` ORM (AG-009)
    from app.chat import model as _chat_model  # noqa: F401 — register chat ORM (AG-011/AG-012)
    from app.document import model as _document_model  # noqa: F401 — register ``document_tasks`` ORM (AG-014)
    from app.topic import model as _topic_model  # noqa: F401 — register ``topics`` + ``portrait_json`` ORM (AG-015/AG-016)
    from app.selection import model as _selection_model  # noqa: F401 — applications (AG-017) / assignments (AG-018)
    from app.taskboard import model as _taskboard_model  # noqa: F401 — milestones ORM (AG-019)

    _register_api_blueprints(app)

    @app.get("/")
    def _root() -> tuple[dict[str, str], int]:
        return {"service": "graduation-design-assistant", "status": "ok"}, 200

    @app.get("/health")
    def _health() -> tuple[dict[str, str], int]:
        return {"status": "healthy"}, 200

    return app


__all__ = ["create_app"]
