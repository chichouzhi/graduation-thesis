"""CI: R-API-ADAPTER / §4 完整性 — 磁盘上 app/<pkg>/api 须出现在 .importlinter forbidden_api_adapter 列表中。"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def parse_linter_api_modules_from_importlinter(text: str) -> set[str]:
    """Extract `app.*.api` lines from the forbidden_api_adapter contract in .importlinter."""
    lines = text.splitlines()
    in_block = False
    modules: set[str] = set()
    for line in lines:
        if "[importlinter:contract:forbidden_api_adapter]" in line:
            in_block = True
            continue
        if in_block and line.strip().startswith("[importlinter:"):
            break
        if in_block:
            m = re.match(r"\s+(app\.\w+\.api)\s*$", line)
            if m:
                modules.add(m.group(1))
    return modules


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    app = root / "app"
    cfg = root / ".importlinter"
    if not cfg.is_file():
        print("FAIL: .importlinter missing", file=sys.stderr)
        return 2
    listed = parse_linter_api_modules_from_importlinter(cfg.read_text(encoding="utf-8"))
    if not listed:
        print("FAIL: could not parse forbidden_api_adapter source_modules from .importlinter", file=sys.stderr)
        return 2
    if not app.is_dir():
        print("SKIP: no app/")
        return 0
    on_disk: set[str] = set()
    for p in app.iterdir():
        if not p.is_dir():
            continue
        if (p / "api").is_dir():
            on_disk.add(f"app.{p.name}.api")
    missing = sorted(on_disk - listed)
    if missing:
        print("FAIL: API packages on disk missing from .importlinter forbidden_api_adapter:", file=sys.stderr)
        for m in missing:
            print(" ", m, file=sys.stderr)
        print(
            "  Fix: add each to forbidden_api_adapter, forbidden_api_use_cases, "
            "forbidden_api_task source_modules.",
            file=sys.stderr,
        )
        return 1
    print("OK: app/*/api covered by .importlinter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
