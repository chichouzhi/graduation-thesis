"""架构护栏：所有 ``enqueue_reconcile_jobs`` 调用必须显式传 ``policy_context``。"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"


def _is_enqueue_reconcile_jobs_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "enqueue_reconcile_jobs"
    if isinstance(func, ast.Attribute):
        return func.attr == "enqueue_reconcile_jobs"
    return False


def test_enqueue_reconcile_jobs_calls_must_pass_policy_context() -> None:
    violations: list[str] = []
    for py_file in APP_DIR.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _is_enqueue_reconcile_jobs_call(node):
                continue
            kw = next((k for k in node.keywords if k.arg == "policy_context"), None)
            if kw is None:
                violations.append(f"{py_file.relative_to(ROOT)}:{node.lineno} missing policy_context")
                continue
            if isinstance(kw.value, ast.Constant) and kw.value.value is None:
                violations.append(f"{py_file.relative_to(ROOT)}:{node.lineno} policy_context=None is forbidden")
    assert not violations, "enqueue_reconcile_jobs callsite violations:\n" + "\n".join(violations)
