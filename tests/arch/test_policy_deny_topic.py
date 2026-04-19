"""R-POLICY-SVC / §5 it-policy-deny-topic — 有 app/ 后实现真实 Flask 集成断言。"""
from __future__ import annotations

from pathlib import Path


def test_policy_deny_topic() -> None:
    root = Path(__file__).resolve().parents[2]
    if not (root / "app").is_dir():
        return
    raise AssertionError(
        "Implement: mock PolicyGateway deny → Topic 写路径触发入队时 429/503; "
        "enqueue spy 零调用（architecture.spec.md §5）。"
    )
