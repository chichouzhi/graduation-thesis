"""最小脚手架检查：与 import-linter / check_rules 去重（不做 api→adapter 等已由 linter 覆盖的扫描）。"""
from __future__ import annotations

import sys
from pathlib import Path


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    app = root / "app"
    if not app.is_dir():
        print("SKIP: no app/ directory")
        return 0
    if not (app / "use_cases").is_dir():
        fail("Missing app/use_cases layer (architecture.spec §0 UC)")
    print("OK: minimal scaffold (use_cases present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
