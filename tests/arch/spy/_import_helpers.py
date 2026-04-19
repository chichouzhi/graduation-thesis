"""供 spy 测使用的 import 辅助：失败时给出可操作的 pytest.fail 信息。"""
from __future__ import annotations

import importlib
from types import ModuleType

import pytest


def import_module_or_fail(qualified: str) -> ModuleType:
    try:
        return importlib.import_module(qualified)
    except ImportError as exc:
        pytest.fail(f"无法 import `{qualified}`：{exc}（请按 execution_plan / ADR 落地模块）")


def get_callable_or_fail(module: ModuleType, *candidates: str):
    for name in candidates:
        if hasattr(module, name):
            return getattr(module, name)
    pytest.fail(
        f"模块 `{getattr(module, '__name__', module)}` 缺少可调用的实现符号；"
        f"尝试过: {', '.join(candidates)}"
    )
