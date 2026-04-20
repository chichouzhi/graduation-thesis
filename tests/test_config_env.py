"""环境变量数值解析：正整数钳制（避免并行度/token 预算为 0 导致 UC 校验失败）。"""
from __future__ import annotations

import pytest

from app.config import _positive_int_from_env


def test_positive_int_env_missing_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_POS_INT", raising=False)
    assert _positive_int_from_env("TEST_POS_INT", 42, minimum=1) == 42


def test_positive_int_env_zero_clamps_to_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_POS_INT", "0")
    assert _positive_int_from_env("TEST_POS_INT", 4, minimum=1) == 1


def test_positive_int_env_negative_clamps_to_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_POS_INT", "-3")
    assert _positive_int_from_env("TEST_POS_INT", 4, minimum=1) == 1


def test_positive_int_env_invalid_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_POS_INT", "not-a-number")
    assert _positive_int_from_env("TEST_POS_INT", 7, minimum=1) == 7
