"""CI (P0): docs/arch/llm_entrypoints.md must exist and be non-trivial (R-UC-ONLY)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--with-diff",
        action="store_true",
        help="If app/use_cases changed in git diff, require doc changed too (staging CI).",
    )
    args = p.parse_args()

    root = Path(__file__).resolve().parents[2]
    doc = root / "docs" / "arch" / "llm_entrypoints.md"
    if not doc.is_file():
        print("FAIL: docs/arch/llm_entrypoints.md missing", file=sys.stderr)
        return 1
    text = doc.read_text(encoding="utf-8").strip()
    if len(text) < 80:
        print("FAIL: llm_entrypoints.md too short", file=sys.stderr)
        return 1
    if "|" not in text:
        print("FAIL: llm_entrypoints.md must contain a markdown table (|)", file=sys.stderr)
        return 1

    if args.with_diff:
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            print("WARN: git not available, skip --with-diff", file=sys.stderr)
            print("OK: llm_entrypoints.md")
            return 0
        if out.returncode != 0:
            print("WARN: git diff failed, skip --with-diff", file=sys.stderr)
            print("OK: llm_entrypoints.md")
            return 0
        names = out.stdout.splitlines()
        uc = any(n.replace("\\", "/").startswith("app/use_cases/") for n in names)
        doc_hit = any(n.replace("\\", "/").endswith("docs/arch/llm_entrypoints.md") for n in names)
        if uc and not doc_hit:
            print("FAIL: use_cases changed but llm_entrypoints.md not in same diff", file=sys.stderr)
            return 1

    print("OK: llm_entrypoints.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
