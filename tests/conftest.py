"""Session-wide defaults so host env (e.g. FLASK_ENV=production) does not break tests."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _default_non_production_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
