"""验收/CI 兜底：打印一条符合 contract 的 reconcile_jobs 载荷（供手工或集成 harness 入队）。

execution_plan 要求 accept 后须 enqueue(reconcile_jobs)；在无完整 selection UI 时，
可用本脚本生成的 JSON 调用实现侧的 enqueue CLI 或 Redis 控制台完成「至少一次消费」演示。
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path


def main() -> int:
    payload = {
        "reconcile_job_id": str(uuid.uuid4()),
        "scope": "by_term",
        "term_id": "<term_id>",
        "request_id": str(uuid.uuid4()),
    }
    out = {"queue": "reconcile_jobs", "payload": payload}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    repo = Path(__file__).resolve().parents[2]
    if not (repo / "app").is_dir():
        print(
            "\nNOTE: no app/ yet — paste payload into your broker admin or "
            "wire this JSON in integration tests when queue.enqueue exists.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
