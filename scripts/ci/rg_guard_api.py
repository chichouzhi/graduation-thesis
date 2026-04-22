"""CI: R-API-ADAPTER + R-API-UC — API 层不得 import ``adapter`` / ``use_cases``。

对齐 ``architecture.spec.md`` §5 ``rg-guard-api``：
``rg "from app\\.(adapter|use_cases)\\b" app/ -g "**/api/**/*.py"``（零命中）。
纯 Python 扫描，不依赖本机 ``rg`` 可执行文件。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PAT = re.compile(
    r"(from\s+app\.(adapter|use_cases)\b|import\s+app\.(adapter|use_cases)\b)",
    re.M,
)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    app = root / "app"
    if not app.is_dir():
        print("SKIP: no app/ directory")
        return 0
    bad: list[str] = []
    for path in app.rglob("*.py"):
        rel = path.relative_to(app)
        parts = rel.parts
        if len(parts) < 2 or parts[1] != "api":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if PAT.search(text):
            bad.append(str(path.relative_to(root)))
    if bad:
        print("FAIL: API must not import app.adapter or app.use_cases:", file=sys.stderr)
        for b in bad:
            print(" ", b, file=sys.stderr)
        return 1
    print("OK: rg-guard-api (no adapter/use_cases in **/api/**/*.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
