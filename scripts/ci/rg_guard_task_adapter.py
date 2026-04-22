"""CI: R-UC-SKIP / W6 — ``app/task`` 不得直连 ``app.adapter``。

对齐 ``architecture.spec.md`` §5 ``rg-guard-task-adapter``：
``rg "from app\\.adapter|import app\\.adapter" app/task -g "**/*.py"``（零命中）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PAT = re.compile(r"(from\s+app\.adapter\b|import\s+app\.adapter\b)", re.M)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    task = root / "app" / "task"
    if not task.is_dir():
        print("SKIP: no app/task directory")
        return 0
    bad: list[str] = []
    for path in task.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if PAT.search(text):
            bad.append(str(path.relative_to(root)))
    if bad:
        print("FAIL: app/task must not import app.adapter:", file=sys.stderr)
        for b in bad:
            print(" ", b, file=sys.stderr)
        return 1
    print("OK: rg-guard-task-adapter (no app.adapter in app/task/**/*.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
