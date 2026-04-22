"""Export `ready` tasks from architecture-task-graph.json to docs/tasks/unimplemented-ready-tasks.md.

Task OS 默认 **单任务关账**：`--mark-done` 一次只允许 **一个** task id，与 `docs/tasks/auto-run.py`
「按 Enter 一次只标 done 一条」一致。若确需批量修补图，设置环境变量 ``TASKOS_BATCH_MARK_OK=1``。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "docs" / "tasks" / "architecture-task-graph.json"
OUT = ROOT / "docs" / "tasks" / "unimplemented-ready-tasks.md"


def _mark_done(data: dict, ids: set[str], ts: str) -> None:
    for t in data["tasks"]:
        if t.get("id") in ids:
            t["status"] = "done"
            t["done_at"] = ts


def main() -> int:
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    ts = datetime.now().isoformat()
    if len(sys.argv) >= 3 and sys.argv[1] == "--mark-done":
        raw = sys.argv[2]
        ids = {x.strip() for x in raw.split(",") if x.strip()}
        if len(ids) > 1 and os.environ.get("TASKOS_BATCH_MARK_OK", "").strip() != "1":
            print(
                "ERROR: --mark-done accepts only ONE task id by default "
                "(single-task mode). Use separate runs or set TASKOS_BATCH_MARK_OK=1.",
                file=sys.stderr,
            )
            return 1
        _mark_done(data, ids, ts)
        GRAPH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Marked done:", ", ".join(sorted(ids)))
    ready = [t for t in data["tasks"] if t.get("status") == "ready"]
    ready.sort(key=lambda x: (x.get("priority", "P2"), x["id"]))
    lines = [
        "# architecture-task-graph：仍为 `ready` 的 AG",
        "",
        f"**generated_at**: `{ts}`",
        "",
        "来源：`docs/tasks/architecture-task-graph.json` 中 `status == \"ready\"` 的节点。",
        "实现并验证后，请在 JSON 中将对应 `id` 标为 `done` 并写入 `done_at`，再运行本脚本刷新本表。",
        "",
        "| ID | Priority | Layer | Title | depends_on |",
        "|----|----------|-------|-------|------------|",
    ]
    for t in ready:
        deps = ", ".join(t.get("depends_on") or [])
        title = str(t.get("title", "")).replace("|", "\\|")
        tid = t["id"]
        pr = t.get("priority", "")
        layer = t.get("layer", "")
        lines.append(f"| {tid} | {pr} | {layer} | {title} | {deps} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(ready)} rows to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)
