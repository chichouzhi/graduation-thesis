"""CI: forbid app/** importing examples/ (architecture.spec R-APP-EXAMPLES)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PAT = re.compile(
    r"(from\s+examples\b|import\s+examples\b|from\s+examples\.|import\s+examples\.)",
    re.M,
)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    app = root / "app"
    if not app.is_dir():
        print("SKIP: no app/ directory")
        return 0
    bad = []
    for path in app.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if PAT.search(text):
            bad.append(str(path.relative_to(root)))
    if bad:
        print("FAIL: app must not import examples:", file=sys.stderr)
        for b in bad:
            print(" ", b, file=sys.stderr)
        return 1
    print("OK: no examples import in app/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
