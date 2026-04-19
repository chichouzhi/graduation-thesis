"""CI: R-POLICY-SVC — policy deny 三测文件须存在；有 app/ 时跑 pytest 且禁止 skip 占位。"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FILES = (
    "tests/arch/test_policy_deny_chat.py",
    "tests/arch/test_policy_deny_document.py",
    "tests/arch/test_policy_deny_topic.py",
)

SKIP_PAT = re.compile(r"pytest\.skip\(|@pytest\.mark\.skip\b")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    for rel in FILES:
        p = root / rel
        if not p.is_file():
            print(f"FAIL: missing {rel}", file=sys.stderr)
            return 1
        if SKIP_PAT.search(p.read_text(encoding="utf-8")):
            print(f"FAIL: {rel} must not use pytest.skip / @pytest.mark.skip", file=sys.stderr)
            return 1

    if not (root / "app").is_dir():
        print("SKIP: no app/ — policy deny pytest not required")
        return 0

    paths = [str(root / rel) for rel in FILES]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--tb=no"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(out, file=sys.stderr)
        return proc.returncode
    print("OK: policy deny tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
