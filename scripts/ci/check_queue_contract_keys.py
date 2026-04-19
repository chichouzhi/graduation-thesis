"""CI: assert spec/contract.yaml x-task-contracts.queues contains required keys (architecture.spec R-QUEUE-ISO)."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED = ("chat_jobs", "document_jobs", "pdf_parse", "keyword_jobs", "reconcile_jobs")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    contract = root / "spec" / "contract.yaml"
    if not contract.is_file():
        print("FAIL: spec/contract.yaml not found", file=sys.stderr)
        return 2
    data = yaml.safe_load(contract.read_text(encoding="utf-8"))
    try:
        queues = data["x-task-contracts"]["queues"]
    except (KeyError, TypeError):
        print("FAIL: x-task-contracts.queues missing", file=sys.stderr)
        return 1
    if not isinstance(queues, dict):
        print("FAIL: queues is not a mapping", file=sys.stderr)
        return 1
    missing = [k for k in REQUIRED if k not in queues]
    if missing:
        print(f"FAIL: missing queue keys: {missing}. Present: {sorted(queues)}", file=sys.stderr)
        return 1
    print("OK: queue keys", ", ".join(REQUIRED))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
