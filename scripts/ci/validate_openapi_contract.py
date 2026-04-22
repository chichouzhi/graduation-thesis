"""CI: validate ``spec/contract.yaml`` with ``openapi-spec-validator`` (AG-120)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    contract = root / "spec" / "contract.yaml"
    if not contract.is_file():
        print("FAIL: spec/contract.yaml not found", file=sys.stderr)
        return 2
    proc = subprocess.run(
        [sys.executable, "-m", "openapi_spec_validator", str(contract)],
        cwd=root,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: contract.yaml OpenAPI validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
