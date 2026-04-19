import os
import sys

# 可由 CI / scripts/ci_self_test.py 注入，例如：ARCH_SCORE=75
_raw = os.environ.get("ARCH_SCORE", "").strip()
score = int(_raw) if _raw else 90

if score < 80:
    print("FAIL: Score too low:", score)
    sys.exit(1)
else:
    print("OK: Score", score)