"""AG-003 / R-NO-QUEUE：production 缺 broker URL 时 ``create_app`` 失败。"""
from __future__ import annotations

import os

import pytest


_UNSET = object()


@pytest.fixture(autouse=True)
def _default_llm_http_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_HTTP_API_KEY", "test-api-key")
    monkeypatch.setenv("LLM_HTTP_BASE_URL", "https://api.example.invalid/v1")
    monkeypatch.setenv("LLM_HTTP_MODEL", "test-model")


def _set_production_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    secret: str | object = _UNSET,
    jwt_secret: str | object = _UNSET,
    broker: str | object = _UNSET,
    redis_url: str | object = _UNSET,
    llm_provider: str | object = "openai_compatible",
    llm_http_api_key: str | object = "test-api-key",
    llm_http_base_url: str | object = "https://api.example.invalid/v1",
    llm_http_model: str | object = "test-model",
    flask_env: str | object = "production",
) -> None:
    if flask_env is _UNSET:
        monkeypatch.delenv("FLASK_ENV", raising=False)
    else:
        monkeypatch.setenv("FLASK_ENV", str(flask_env))

    if secret is _UNSET:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", str(secret))

    if jwt_secret is _UNSET:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET_KEY", str(jwt_secret))

    if broker is _UNSET:
        monkeypatch.delenv("BROKER_URL", raising=False)
    else:
        monkeypatch.setenv("BROKER_URL", str(broker))

    if redis_url is _UNSET:
        monkeypatch.delenv("REDIS_URL", raising=False)
    else:
        monkeypatch.setenv("REDIS_URL", str(redis_url))

    if llm_provider is _UNSET:
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("LLM_PROVIDER", str(llm_provider))

    if llm_http_api_key is _UNSET:
        monkeypatch.delenv("LLM_HTTP_API_KEY", raising=False)
    else:
        monkeypatch.setenv("LLM_HTTP_API_KEY", str(llm_http_api_key))

    if llm_http_base_url is _UNSET:
        monkeypatch.delenv("LLM_HTTP_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("LLM_HTTP_BASE_URL", str(llm_http_base_url))

    if llm_http_model is _UNSET:
        monkeypatch.delenv("LLM_HTTP_MODEL", raising=False)
    else:
        monkeypatch.setenv("LLM_HTTP_MODEL", str(llm_http_model))


def test_production_without_broker_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
    )

    with pytest.raises(RuntimeError, match="R-NO-QUEUE"):
        create_app()


def test_production_rejects_known_placeholder_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="change-me-to-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_production_rejects_env_example_secret_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="<set-a-unique-secret-with-at-least-32-characters>",
        jwt_secret="production-jwt-secret-key-32-bytes",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_production_rejects_env_example_llm_api_key_placeholder(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
        llm_http_api_key="<set-your-openai-compatible-api-key>",
    )

    with pytest.raises(RuntimeError, match="LLM_HTTP_API_KEY"):
        create_app()


def test_production_rejects_short_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="too-short",
    )

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app()


def test_production_requires_llm_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
        llm_provider=_UNSET,
        llm_http_api_key=_UNSET,
        llm_http_base_url=_UNSET,
        llm_http_model=_UNSET,
    )

    with pytest.raises(RuntimeError, match="LLM_PROVIDER"):
        create_app()


def test_production_requires_llm_http_api_key_for_http_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
        llm_provider="openai_compatible",
        llm_http_api_key=_UNSET,
    )

    with pytest.raises(RuntimeError, match="LLM_HTTP_API_KEY"):
        create_app()


def test_production_bootstraps_openai_compatible_llm_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.adapter.llm.openai_compatible_http import OpenAiCompatibleHttpClient

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
    )

    app = create_app()

    assert isinstance(app.extensions["llm_client"], OpenAiCompatibleHttpClient)


def test_production_with_broker_url_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        broker="redis://localhost:6379/0",
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
    )

    app = create_app()
    assert app.config["BROKER_URL"] == "redis://localhost:6379/0"
    assert app.config["SECRET_KEY"] == "production-secret-key-32-bytes-minimum"
    assert app.config["JWT_SECRET_KEY"] == "production-jwt-secret-key-32-bytes"


def test_production_accepts_redis_url_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    _set_production_env(
        monkeypatch,
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
        redis_url="redis://redis:6379/1",
    )

    app = create_app()
    assert app.config["BROKER_URL"] == "redis://redis:6379/1"


def test_explicit_production_config_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    _set_production_env(
        monkeypatch,
        secret="production-secret-key-32-bytes-minimum",
        jwt_secret="production-jwt-secret-key-32-bytes",
    )

    with pytest.raises(RuntimeError, match="R-NO-QUEUE"):
        create_app(config=ProductionConfig)


def test_base_production_config_uses_current_env_over_stale_imported_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "stale-imported-secret-key-value-32-bytes")
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", "stale-imported-jwt-secret-value-32-bytes")
    monkeypatch.setattr(ProductionConfig, "BROKER_URL", "redis://stale-imported-broker:6379/4", raising=False)
    _set_production_env(
        monkeypatch,
        secret="current-env-secret-key-value-32-bytes",
        jwt_secret="current-env-jwt-secret-key-value-32-bytes",
        broker="redis://current-env-broker:6379/3",
    )

    app = create_app(config=ProductionConfig)

    assert app.config["SECRET_KEY"] == "current-env-secret-key-value-32-bytes"
    assert app.config["JWT_SECRET_KEY"] == "current-env-jwt-secret-key-value-32-bytes"
    assert app.config["BROKER_URL"] == "redis://current-env-broker:6379/3"


def test_base_production_config_instance_fails_closed_when_current_env_secrets_are_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "stale-imported-secret-key-value-32-bytes")
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", "stale-imported-jwt-secret-value-32-bytes")
    monkeypatch.setattr(ProductionConfig, "BROKER_URL", "redis://stale-imported-broker:6379/4", raising=False)
    _set_production_env(monkeypatch, broker="redis://current-env-broker:6379/3")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=ProductionConfig())


def test_base_production_config_instance_preserves_explicit_instance_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    cfg = ProductionConfig()
    cfg.SECRET_KEY = "instance-secret-key-value-32-bytes"
    cfg.JWT_SECRET_KEY = "instance-jwt-secret-key-value-32-bytes"
    cfg.BROKER_URL = "redis://instance-broker:6379/8"

    _set_production_env(
        monkeypatch,
        secret="env-secret-key-value-32-bytes-minimum",
        jwt_secret="env-jwt-secret-key-value-32-bytes-minimum",
        broker="redis://env-broker:6379/7",
    )

    app = create_app(config=cfg)

    assert app.config["SECRET_KEY"] == "instance-secret-key-value-32-bytes"
    assert app.config["JWT_SECRET_KEY"] == "instance-jwt-secret-key-value-32-bytes"
    assert app.config["BROKER_URL"] == "redis://instance-broker:6379/8"


def test_base_production_config_instance_explicit_none_values_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    cfg = ProductionConfig()
    cfg.SECRET_KEY = None
    cfg.JWT_SECRET_KEY = None
    cfg.BROKER_URL = None

    _set_production_env(
        monkeypatch,
        secret="env-secret-key-value-32-bytes-minimum",
        jwt_secret="env-jwt-secret-key-value-32-bytes-minimum",
        broker="redis://env-broker:6379/7",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=cfg)


def test_production_uses_runtime_secret_env_values_after_import(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "runtime-secret-key-after-import-32b")
    monkeypatch.setenv("JWT_SECRET_KEY", "runtime-jwt-secret-key-after-import-32b")

    app = create_app()

    assert app.config["SECRET_KEY"] == "runtime-secret-key-after-import-32b"
    assert app.config["JWT_SECRET_KEY"] == "runtime-jwt-secret-key-after-import-32b"


def test_production_subclass_uses_runtime_secrets_and_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import Config, ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setattr(Config, "SECRET_KEY", "stale-imported-config-secret-key-value-32b")
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", "stale-imported-config-jwt-secret-key-value-32b")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("SECRET_KEY", "subclass-production-secret-key-value-32b")
    monkeypatch.setenv("JWT_SECRET_KEY", "subclass-production-jwt-secret-key-value-32b")

    app = create_app(config=CustomProductionConfig)

    assert app.config["BROKER_URL"] == "redis://localhost:6379/9"
    assert app.config["SECRET_KEY"] == "subclass-production-secret-key-value-32b"
    assert app.config["JWT_SECRET_KEY"] == "subclass-production-jwt-secret-key-value-32b"


def test_production_subclass_inheriting_stale_non_default_secrets_without_env_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import Config, ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setattr(Config, "SECRET_KEY", "stale-imported-config-secret-key-value-32b")
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", "stale-imported-config-jwt-secret-key-value-32b")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/9")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=CustomProductionConfig)


def test_production_subclass_inheriting_stale_non_default_secrets_uses_current_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import Config, ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setattr(Config, "SECRET_KEY", "stale-imported-config-secret-key-value-32b")
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", "stale-imported-config-jwt-secret-key-value-32b")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("SECRET_KEY", "runtime-subclass-secret-key-value-32b")
    monkeypatch.setenv("JWT_SECRET_KEY", "runtime-subclass-jwt-secret-key-value-32b")

    app = create_app(config=CustomProductionConfig)

    assert app.config["SECRET_KEY"] == "runtime-subclass-secret-key-value-32b"
    assert app.config["JWT_SECRET_KEY"] == "runtime-subclass-jwt-secret-key-value-32b"


def test_production_subclass_inheriting_stale_production_broker_without_env_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setattr(ProductionConfig, "BROKER_URL", "redis://stale-production-broker:6379/2", raising=False)
    monkeypatch.setenv("SECRET_KEY", "runtime-subclass-secret-key-value-32b")
    monkeypatch.setenv("JWT_SECRET_KEY", "runtime-subclass-jwt-secret-key-value-32b")
    monkeypatch.delenv("BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(RuntimeError, match="R-NO-QUEUE"):
        create_app(config=CustomProductionConfig)


def test_production_subclass_inheriting_stale_production_broker_uses_current_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setattr(ProductionConfig, "BROKER_URL", "redis://stale-production-broker:6379/2", raising=False)
    monkeypatch.setenv("SECRET_KEY", "runtime-subclass-secret-key-value-32b")
    monkeypatch.setenv("JWT_SECRET_KEY", "runtime-subclass-jwt-secret-key-value-32b")
    monkeypatch.setenv("BROKER_URL", "redis://runtime-production-broker:6379/3")

    app = create_app(config=CustomProductionConfig)

    assert app.config["BROKER_URL"] == "redis://runtime-production-broker:6379/3"


def test_production_leaf_subclass_of_env_backed_base_uses_current_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig, _DEV_DEFAULT_SECRET_KEY

    _set_production_env(
        monkeypatch,
        secret="captured-base-secret-key-value-32b",
        jwt_secret="captured-base-jwt-secret-key-value-32b",
        broker="redis://captured-base-broker:6379/4",
    )

    class EnvBackedBaseProductionConfig(ProductionConfig):
        SECRET_KEY = os.environ.get("SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)
        JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)
        BROKER_URL = os.environ.get("BROKER_URL", "")

    class LeafProductionConfig(EnvBackedBaseProductionConfig):
        pass

    _set_production_env(
        monkeypatch,
        secret="runtime-leaf-secret-key-value-32b",
        jwt_secret="runtime-leaf-jwt-secret-key-value-32b",
        broker="redis://runtime-leaf-broker:6379/5",
    )

    app = create_app(config=LeafProductionConfig)

    assert app.config["SECRET_KEY"] == "runtime-leaf-secret-key-value-32b"
    assert app.config["JWT_SECRET_KEY"] == "runtime-leaf-jwt-secret-key-value-32b"
    assert app.config["BROKER_URL"] == "redis://runtime-leaf-broker:6379/5"


def test_production_leaf_subclass_of_env_backed_base_fails_closed_when_runtime_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig, _DEV_DEFAULT_SECRET_KEY

    _set_production_env(
        monkeypatch,
        secret="captured-base-secret-key-value-32b",
        jwt_secret="captured-base-jwt-secret-key-value-32b",
        broker="redis://captured-base-broker:6379/4",
    )

    class EnvBackedBaseProductionConfig(ProductionConfig):
        SECRET_KEY = os.environ.get("SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)
        JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)
        BROKER_URL = os.environ.get("BROKER_URL", "")

    class LeafProductionConfig(EnvBackedBaseProductionConfig):
        pass

    _set_production_env(monkeypatch)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=LeafProductionConfig)


def test_production_subclass_instance_inheriting_stale_non_default_secrets_without_env_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import Config, ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setattr(Config, "SECRET_KEY", "stale-imported-config-secret-key-value-32b")
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", "stale-imported-config-jwt-secret-key-value-32b")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/9")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=CustomProductionConfig())


def test_explicit_production_subclass_values_are_preserved_without_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = "config-secret-key-value-32-bytes-minimum"
        JWT_SECRET_KEY = "config-jwt-secret-key-value-32-bytes-minimum"
        BROKER_URL = "redis://config-broker:6379/5"

    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")
    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")

    app = create_app(config=CustomProductionConfig)

    assert app.config["BROKER_URL"] == "redis://config-broker:6379/5"
    assert app.config["SECRET_KEY"] == "config-secret-key-value-32-bytes-minimum"
    assert app.config["JWT_SECRET_KEY"] == "config-jwt-secret-key-value-32-bytes-minimum"


def test_partial_production_explicit_keys_only_preserve_marked_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY",)
        SECRET_KEY = "config-secret-key-value-32-bytes-minimum"
        JWT_SECRET_KEY = "config-jwt-secret-key-value-32-bytes-minimum"
        BROKER_URL = "redis://config-broker:6379/5"

    _set_production_env(
        monkeypatch,
        secret="env-secret-key-value-32-bytes-minimum",
        jwt_secret="env-jwt-secret-key-value-32-bytes-minimum",
        broker="redis://env-broker:6379/7",
    )

    app = create_app(config=CustomProductionConfig)

    assert app.config["SECRET_KEY"] == "config-secret-key-value-32-bytes-minimum"
    assert app.config["JWT_SECRET_KEY"] == "env-jwt-secret-key-value-32-bytes-minimum"
    assert app.config["BROKER_URL"] == "redis://env-broker:6379/7"


def test_production_subclass_explicit_none_secret_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = None
        JWT_SECRET_KEY = "config-jwt-secret-key-value-32-bytes-minimum"
        BROKER_URL = "redis://config-broker:6379/5"

    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=CustomProductionConfig)


def test_production_subclass_explicit_none_jwt_secret_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = "config-secret-key-value-32-bytes-minimum"
        JWT_SECRET_KEY = None
        BROKER_URL = "redis://config-broker:6379/5"

    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app(config=CustomProductionConfig)


def test_production_subclass_explicit_none_broker_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = "config-secret-key-value-32-bytes-minimum"
        JWT_SECRET_KEY = "config-jwt-secret-key-value-32-bytes-minimum"
        BROKER_URL = None

    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")

    with pytest.raises(RuntimeError, match="R-NO-QUEUE"):
        create_app(config=CustomProductionConfig)


def test_child_production_subclass_preserves_inherited_parent_explicit_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class ParentProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = "parent-config-secret-key-value-32-bytes"
        JWT_SECRET_KEY = "parent-config-jwt-secret-key-value-32-bytes"
        BROKER_URL = "redis://parent-config-broker:6379/8"

    class ChildProductionConfig(ParentProductionConfig):
        pass

    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")
    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")

    app = create_app(config=ChildProductionConfig)

    assert app.config["BROKER_URL"] == "redis://parent-config-broker:6379/8"
    assert app.config["SECRET_KEY"] == "parent-config-secret-key-value-32-bytes"
    assert app.config["JWT_SECRET_KEY"] == "parent-config-jwt-secret-key-value-32-bytes"


def test_child_marker_can_make_inherited_parent_values_authoritative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class ParentProductionConfig(ProductionConfig):
        SECRET_KEY = "parent-config-secret-key-value-32-bytes"
        JWT_SECRET_KEY = "parent-config-jwt-secret-key-value-32-bytes"
        BROKER_URL = "redis://parent-config-broker:6379/8"

    class ChildProductionConfig(ParentProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")

    _set_production_env(
        monkeypatch,
        secret="env-secret-key-value-32-bytes-minimum",
        jwt_secret="env-jwt-secret-key-value-32-bytes-minimum",
        broker="redis://env-broker:6379/7",
    )

    app = create_app(config=ChildProductionConfig)

    assert app.config["SECRET_KEY"] == "parent-config-secret-key-value-32-bytes"
    assert app.config["JWT_SECRET_KEY"] == "parent-config-jwt-secret-key-value-32-bytes"
    assert app.config["BROKER_URL"] == "redis://parent-config-broker:6379/8"


def test_child_production_subclass_inheriting_parent_default_secret_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import create_app
    from app.config import ProductionConfig, _DEV_DEFAULT_SECRET_KEY

    class ParentProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = _DEV_DEFAULT_SECRET_KEY
        JWT_SECRET_KEY = "parent-config-jwt-secret-key-value-32-bytes"
        BROKER_URL = "redis://parent-config-broker:6379/8"

    class ChildProductionConfig(ParentProductionConfig):
        pass

    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")
    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=ChildProductionConfig)


def test_production_config_instance_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = "instance-config-secret-key-value-32-bytes"
        JWT_SECRET_KEY = "instance-config-jwt-secret-key-value-32-bytes"
        BROKER_URL = "redis://instance-config-broker:6379/6"

    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")
    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")

    app = create_app(config=CustomProductionConfig())

    assert app.config["BROKER_URL"] == "redis://instance-config-broker:6379/6"
    assert app.config["SECRET_KEY"] == "instance-config-secret-key-value-32-bytes"
    assert app.config["JWT_SECRET_KEY"] == "instance-config-jwt-secret-key-value-32-bytes"


def test_production_subclass_instance_rejects_default_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig, _DEV_DEFAULT_SECRET_KEY

    class CustomProductionConfig(ProductionConfig):
        PRODUCTION_EXPLICIT_KEYS = ("SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL")
        SECRET_KEY = _DEV_DEFAULT_SECRET_KEY
        JWT_SECRET_KEY = "instance-config-jwt-secret-key-value-32-bytes"
        BROKER_URL = "redis://instance-config-broker:6379/6"

    monkeypatch.setenv("BROKER_URL", "redis://env-broker:6379/7")
    monkeypatch.setenv("SECRET_KEY", "env-secret-key-value-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-jwt-secret-key-value-32-bytes-minimum")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=CustomProductionConfig())


def test_production_subclass_rejects_missing_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import ProductionConfig

    class CustomProductionConfig(ProductionConfig):
        pass

    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/9")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "subclass-production-jwt-secret-key-value-32b")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config=CustomProductionConfig)


def test_production_without_secret_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "production-jwt-secret-key-32-bytes")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_production_without_jwt_secret_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "production-secret-key-32-bytes-minimum")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app()


def test_production_rejects_default_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import _DEV_DEFAULT_SECRET_KEY

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)
    monkeypatch.setenv("JWT_SECRET_KEY", "production-jwt-secret-key-32-bytes")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_production_rejects_default_jwt_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import _DEV_DEFAULT_SECRET_KEY

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "production-secret-key-32-bytes-minimum")
    monkeypatch.setenv("JWT_SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app()

