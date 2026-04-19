"""Emit docs/tasks/architecture-task-graph.md from docs/tasks/architecture-task-graph.json."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "docs" / "tasks" / "architecture-task-graph.json"
    dst = root / "docs" / "tasks" / "architecture-task-graph.md"
    data = json.loads(src.read_text(encoding="utf-8"))
    tasks: list[dict] = data["tasks"]

    layer_order: list[str] = []
    seen: set[str] = set()
    for t in tasks:
        layer = str(t["layer"])
        if layer not in seen:
            seen.add(layer)
            layer_order.append(layer)

    by_layer: dict[str, list[dict]] = {layer: [] for layer in layer_order}
    for t in tasks:
        by_layer[str(t["layer"])].append(t)

    lines: list[str] = []
    lines.append("# 架构任务图（分层 Todo）\n\n")
    lines.append(
        "> **文档导航**：[分类总目](../DOCUMENT-CATALOG.md) · [文档索引](../README.md) · "
        "[系统架构](../architecture/system-architecture.md) · [规范提取（完整）](../requirements/spec-extraction-full.md) · "
        "[JSON 真源](./architecture-task-graph.json)\n\n"
    )
    lines.append(
        "机器可读真源：[architecture-task-graph.json](./architecture-task-graph.json)"
        "（`tasks[].depends_on` 即 DAG 边：所列 **全部** 前置任务完成后方可开始本项）。\n\n"
    )
    lines.append("约束：每项 **原子**（预估 **≤2 天**）、**禁止合并**为多交付物；优先级 **P0 / P1 / P2**。\n\n")
    lines.append("---\n")

    for layer in layer_order:
        lines.append(f"\n## 分层：`{layer}`\n")
        for t in by_layer[layer]:
            deps = t.get("depends_on") or []
            dep_str = "无" if not deps else ", ".join(str(x) for x in deps)
            lines.append(f"\n### {t['id']}\n\n")
            lines.append(f"- **标题**：{t['title']}\n")
            lines.append(f"- **优先级**：{t['priority']}\n")
            lines.append(f"- **耗时上限**：{t['max_duration_days']} 天\n")
            lines.append(f"- **依赖**：{dep_str}\n")

    dst.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {dst} ({len(tasks)} tasks)")


if __name__ == "__main__":
    main()
