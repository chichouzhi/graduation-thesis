"""Flask 配置对象。

生产环境 broker URL 等强校验见任务图 AG-003；本文件仅提供工厂可加载的最小配置。
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Final

# 与队列客户端对齐：优先显式 broker，其次常见 Redis 直连 URL（R-NO-QUEUE）
_ENV_BROKER_KEYS: Final[tuple[str, ...]] = ("BROKER_URL", "REDIS_URL")
_DEV_DEFAULT_SECRET_KEY: Final[str] = "dev-only-change-in-production-please-use-32+bytes"
_KNOWN_PLACEHOLDER_SECRETS: Final[frozenset[str]] = frozenset(
    {
        _DEV_DEFAULT_SECRET_KEY,
        "change-me-to-32-bytes-minimum",
    }
)
_KNOWN_PLACEHOLDER_RUNTIME_VALUES: Final[frozenset[str]] = frozenset(
    {
        "<set-a-unique-secret-with-at-least-32-characters>",
        "<set-a-unique-jwt-secret-with-at-least-32-characters>",
        "<set-your-openai-compatible-api-key>",
    }
)
_MIN_SECRET_LENGTH: Final[int] = 32


def _int_from_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(str(raw).strip())


def _positive_int_from_env(name: str, default: int, *, minimum: int = 1) -> int:
    """读取正整数配置：缺省/空白用 ``default``；无法解析为整数时用 ``default``；小于 ``minimum`` 时钳制到 ``minimum``。"""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        v = int(str(raw).strip())
    except ValueError:
        return default
    return max(int(minimum), v)


def _float_from_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def _string_from_env(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = str(raw).strip()
    if not value:
        return default
    return value


def _bool_from_env(name: str, default: bool) -> bool:
    """读取布尔配置：支持 1/true/yes/on 与 0/false/no/off。"""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return bool(default)
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return bool(default)


class Config:
    """默认配置（开发可用环境变量覆盖）。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", _DEV_DEFAULT_SECRET_KEY)
    TESTING = False

    # Flask-SQLAlchemy / Flask-Migrate（AG-002）
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-JWT-Extended
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        os.environ.get("SECRET_KEY", _DEV_DEFAULT_SECRET_KEY),
    )
    # Identity access token TTL (seconds); AG-052 default aligns with architecture draft.
    ACCESS_TOKEN_EXPIRES_IN = _positive_int_from_env("ACCESS_TOKEN_EXPIRES_IN", 3600, minimum=1)
    # Identity refresh token & cookie defaults; AG-053.
    REFRESH_TOKEN_EXPIRES_IN = _positive_int_from_env("REFRESH_TOKEN_EXPIRES_IN", 1209600, minimum=1)
    REFRESH_TOKEN_COOKIE_NAME = os.environ.get("REFRESH_TOKEN_COOKIE_NAME", "refresh_token")
    REFRESH_TOKEN_COOKIE_PATH = os.environ.get("REFRESH_TOKEN_COOKIE_PATH", "/api/v1/auth")
    REFRESH_TOKEN_COOKIE_SAMESITE = os.environ.get("REFRESH_TOKEN_COOKIE_SAMESITE", "Lax")
    REFRESH_TOKEN_COOKIE_SECURE = _bool_from_env("REFRESH_TOKEN_COOKIE_SECURE", True)
    MAX_CONTENT_LENGTH = _positive_int_from_env("MAX_CONTENT_LENGTH", 16 * 1024 * 1024, minimum=1)

    # chat_orchestration：上下文 token 预算（粗估，见 use_cases.chat_orchestration）；可由 CHAT_CONTEXT_TOKEN_BUDGET 覆盖
    CHAT_CONTEXT_TOKEN_BUDGET = _positive_int_from_env("CHAT_CONTEXT_TOKEN_BUDGET", 8192, minimum=1)

    # document_pipeline：summarize_chunk 同级并行度上界（in-flight ≤ 此值）；见 execution_plan / architecture.spec
    DOCUMENT_CHUNK_MAX_PARALLEL = _positive_int_from_env("DOCUMENT_CHUNK_MAX_PARALLEL", 4, minimum=1)
    LLM_PROVIDER = str(os.environ.get("LLM_PROVIDER", "mock")).strip() or "mock"
    LLM_HTTP_API_KEY = str(os.environ.get("LLM_HTTP_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    LLM_HTTP_BASE_URL = str(os.environ.get("LLM_HTTP_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").strip()
    LLM_HTTP_MODEL = str(os.environ.get("LLM_HTTP_MODEL") or os.environ.get("OPENAI_MODEL") or "").strip()
    LLM_HTTP_TIMEOUT_S = _float_from_env("LLM_HTTP_TIMEOUT_S", 60.0)


class ProductionConfig(Config):
    """生产：必须配置 broker，否则进程不得启动（architecture.spec R-NO-QUEUE）。"""

    DEBUG = False
    PRODUCTION_EXPLICIT_KEYS: tuple[str, ...] = ()


def _config_class_of(config: type[Config] | Config) -> type[Config]:
    if isinstance(config, type):
        return config
    return type(config)


def is_production_config(config: type[Config] | Config) -> bool:
    """判断配置是否为 ProductionConfig 或其子类，支持类和实例。"""
    return issubclass(_config_class_of(config), ProductionConfig)


def _is_base_production_config(config: type[Config] | Config) -> bool:
    return isinstance(config, type) and config is ProductionConfig


def broker_url_from_environ() -> str:
    """从环境变量读取 broker URL（去首尾空白）；未配置则为空串。"""
    for key in _ENV_BROKER_KEYS:
        raw = os.environ.get(key)
        if raw is not None and raw.strip():
            return raw.strip()
    return ""


def _llm_provider_from_environ() -> str:
    return str(os.environ.get("LLM_PROVIDER", "")).strip()


def _llm_http_api_key_from_environ() -> str:
    return str(os.environ.get("LLM_HTTP_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()


def _llm_http_base_url_from_environ() -> str:
    return str(os.environ.get("LLM_HTTP_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").strip()


def _llm_http_model_from_environ() -> str:
    return str(os.environ.get("LLM_HTTP_MODEL") or os.environ.get("OPENAI_MODEL") or "").strip()


def _secret_key_from_environ() -> str:
    return str(os.environ.get("SECRET_KEY", "")).strip()


def _jwt_secret_key_from_environ() -> str:
    return str(os.environ.get("JWT_SECRET_KEY", "")).strip()


def _database_url_from_runtime(*, production: bool) -> str:
    _ = production
    default = "sqlite:///:memory:"
    return _string_from_env("DATABASE_URL", default)


def _secret_key_from_runtime(*, production: bool) -> str:
    default = "" if production else _DEV_DEFAULT_SECRET_KEY
    return _string_from_env("SECRET_KEY", default)


def _jwt_secret_key_from_runtime(*, production: bool) -> str:
    raw = _jwt_secret_key_from_environ()
    if raw:
        return raw
    if production:
        return ""
    return _secret_key_from_runtime(production=False)


def _llm_provider_from_runtime(*, production: bool) -> str:
    default = "" if production else "mock"
    return _string_from_env("LLM_PROVIDER", default)


def _string_config_value(config: Mapping[str, object], key: str) -> str:
    value = config.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def _class_declares_explicit_key(config_class: type[Config], key: str) -> bool:
    keys = vars(config_class).get("PRODUCTION_EXPLICIT_KEYS", ())
    return key in {str(item) for item in keys}


def _has_explicit_config_value(config: type[Config] | Config, key: str) -> bool:
    if not isinstance(config, type) and key in vars(config):
        return True
    config_class = _config_class_of(config)
    for cls in config_class.__mro__:
        if key not in vars(cls):
            continue
        if cls in {Config, ProductionConfig}:
            return False
        for marker_cls in config_class.__mro__:
            if marker_cls in {Config, ProductionConfig}:
                continue
            if _class_declares_explicit_key(marker_cls, key):
                return True
            if marker_cls is cls:
                break
        return False
    return False


def _has_non_base_config_value(config: type[Config] | Config, key: str) -> bool:
    if not isinstance(config, type) and key in vars(config):
        return True
    config_class = _config_class_of(config)
    for cls in config_class.__mro__:
        if key not in vars(cls):
            continue
        return cls not in {Config, ProductionConfig}
    return False


def production_runtime_overrides(config: type[Config] | Config) -> dict[str, str]:
    """兼容旧调用方：生产运行时覆盖委托给通用运行时覆盖。"""
    return {
        key: value
        for key, value in runtime_config_overrides(config).items()
        if key in {"SECRET_KEY", "JWT_SECRET_KEY", "BROKER_URL"}
    }


def runtime_config_overrides(config: type[Config] | Config) -> dict[str, object]:
    """为当前运行环境重新计算 env-backed 配置，避免导入时捕获旧值。"""
    overrides: dict[str, object] = {}
    production = is_production_config(config)
    preserve = _has_explicit_config_value if production else _has_non_base_config_value

    if not preserve(config, "SECRET_KEY"):
        overrides["SECRET_KEY"] = _secret_key_from_runtime(production=production)

    if not preserve(config, "JWT_SECRET_KEY"):
        overrides["JWT_SECRET_KEY"] = _jwt_secret_key_from_runtime(production=production)

    if not preserve(config, "SQLALCHEMY_DATABASE_URI"):
        overrides["SQLALCHEMY_DATABASE_URI"] = _database_url_from_runtime(production=production)

    if not preserve(config, "BROKER_URL"):
        overrides["BROKER_URL"] = broker_url_from_environ()

    if not preserve(config, "LLM_PROVIDER"):
        overrides["LLM_PROVIDER"] = _llm_provider_from_runtime(production=production)

    if not preserve(config, "LLM_HTTP_API_KEY"):
        overrides["LLM_HTTP_API_KEY"] = _llm_http_api_key_from_environ()

    if not preserve(config, "LLM_HTTP_BASE_URL"):
        overrides["LLM_HTTP_BASE_URL"] = _llm_http_base_url_from_environ()

    if not preserve(config, "LLM_HTTP_MODEL"):
        overrides["LLM_HTTP_MODEL"] = _llm_http_model_from_environ()

    if not preserve(config, "LLM_HTTP_TIMEOUT_S"):
        overrides["LLM_HTTP_TIMEOUT_S"] = _float_from_env("LLM_HTTP_TIMEOUT_S", 60.0)

    return overrides


def llm_runtime_overrides(config: type[Config] | Config) -> dict[str, object]:
    """兼容旧调用方：委托给通用运行时覆盖。"""
    return {
        key: value
        for key, value in runtime_config_overrides(config).items()
        if key.startswith("LLM_")
    }


def _validate_production_secret(key: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"Production requires an explicit {key}")
    if _looks_like_placeholder_value(value) or value in _KNOWN_PLACEHOLDER_SECRETS:
        raise RuntimeError(f"Production rejects placeholder {key}")
    if len(value) < _MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"Production requires {key} to be at least {_MIN_SECRET_LENGTH} characters long"
        )


def _normalize_llm_provider(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _looks_like_placeholder_value(value: str) -> bool:
    normalized = value.strip().lower()
    if value in _KNOWN_PLACEHOLDER_RUNTIME_VALUES:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    return False


def _validate_production_llm_runtime(values: Mapping[str, object]) -> None:
    provider = _normalize_llm_provider(_string_config_value(values, "LLM_PROVIDER"))
    if not provider:
        raise RuntimeError("Production requires an explicit LLM_PROVIDER")
    if provider == "mock":
        raise RuntimeError("Production does not allow LLM_PROVIDER=mock")
    if provider != "openai_compatible":
        raise RuntimeError(f"Production does not support LLM_PROVIDER={provider}")

    api_key = _string_config_value(values, "LLM_HTTP_API_KEY")
    base_url = _string_config_value(values, "LLM_HTTP_BASE_URL")
    model = _string_config_value(values, "LLM_HTTP_MODEL")
    if not api_key:
        raise RuntimeError("Production requires LLM_HTTP_API_KEY when LLM_PROVIDER is openai_compatible")
    if _looks_like_placeholder_value(api_key):
        raise RuntimeError("Production rejects placeholder LLM_HTTP_API_KEY")
    if not base_url:
        raise RuntimeError("Production requires LLM_HTTP_BASE_URL when LLM_PROVIDER is openai_compatible")
    if not model:
        raise RuntimeError("Production requires LLM_HTTP_MODEL when LLM_PROVIDER is openai_compatible")


def validate_production_runtime_requirements(config: type[Config] | Config, values: Mapping[str, object]) -> None:
    """若选用生产配置，则要求最终生效的 broker 与关键 secrets 都显式配置。"""
    if not is_production_config(config):
        return
    secret_key = _string_config_value(values, "SECRET_KEY")
    jwt_secret_key = _string_config_value(values, "JWT_SECRET_KEY")
    broker_url = _string_config_value(values, "BROKER_URL")
    _validate_production_secret("SECRET_KEY", secret_key)
    _validate_production_secret("JWT_SECRET_KEY", jwt_secret_key)
    if not broker_url:
        raise RuntimeError(
            "R-NO-QUEUE: FLASK_ENV=production requires a non-empty BROKER_URL or "
            "REDIS_URL (queue + worker is mandatory; see spec/architecture.spec.md)."
        )
    _validate_production_llm_runtime(values)


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
    "is_production_config",
    "llm_runtime_overrides",
    "runtime_config_overrides",
    "production_runtime_overrides",
    "validate_production_runtime_requirements",
]
