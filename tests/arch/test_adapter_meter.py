"""§5 it-adapter-meter（P1）：静态子集 — ``use_cases`` 无无限重试裸循环。"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


def test_it_adapter_meter_no_while_true_in_use_cases():
    root = Path(__file__).resolve().parents[2]
    uc = root / "app" / "use_cases"
    assert uc.is_dir()
    for path in uc.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"while\s+True\b", text):
            pytest.fail(
                f"while True in {path.relative_to(root)} — add bounded retry or PR note per architecture.spec M-ADAPTER-METER"
            )
