import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

LOCK_STALE_DEFAULT_HOURS = 48

# 复制到 Cursor 的提示词（与 docs/tasks/README.md 保持一致）
CURSOR_PROMPT_ZH = """你正在执行 Task OS 派发的单条任务（与终端里的 auto-run.py 配对）。

【强约束：先做条件完备验证，再改仓库；禁止空跑与假完成】

1) 读取 docs/tasks/queue.json
   - 若文件不存在、JSON 无法解析、缺少顶层键 task、或 task 为空/非对象：
     → 在回复中写明原因；停止执行本任务（不要假装已完成）。
   - 「ALL TASKS COMPLETED」只能由终端里的 auto-run.py 在任务图耗尽时打印；你不得在聊天中用该句表示本任务状态。

2) 条件完备验证（**先于**对仓库任意文件的增删改；本步仅允许读取与检索，不得提交实现性 diff）
   - 校验 `task.id`、`task.title` 均存在且为非空字符串；否则等同 1) 失败并停止。
   - 确认下列真源**在仓库内存在且可读**（路径相对仓库根）：至少 `spec/contract.yaml`、`spec/architecture.spec.md`。若 task 涉及分层/阶段语义，还须可读 `spec/execution_plan.md`、`docs/architecture/system-architecture.md`（含 **§8 任务图 layer→文档路由** 时可对照 `task.layer`）。
   - 若关键真源缺失、或 `title`/`layer` 与真源存在**无法调和**的冲突、或你从仓库**静态即可判定**前置工程事实不满足（例如依赖的模块尚不存在且本 task 不应承担「顺带创建」）：**仅输出下方格式中的【Preconditions】说明阻塞，【Changes】写「无（未改仓库）」**，并停止，不要硬写占位代码凑数。
   - 若条件满足：在【Preconditions】用一行写「已满足：…」（可简述已核对的文件），**再进入**步骤 3～6。

3) 复述（须在最终回复的【Task】节中体现）：
   Task ID: <id>
   Task Title: <title>

4) 任务锁定：当前 task 是唯一允许推进的工作项。禁止跳过、禁止在未产生交付物时声称已完成、禁止同一轮顺带执行其它 AG-* 条目。

5) 交付物（**仅**在步骤 2 未声明阻塞时执行）：必须对仓库产生与本 task 直接相关的可提交变更（代码、测试、配置，或 task 明文要求的文档/脚本路径）。禁止仅输出分析说明而不改仓库。
   - 信息不足：在已满足步骤 2 的前提下，按需只读上述真源；做最小可行实现。
   - stub/占位仅在不违反上述规范与仓库既有门禁（测试、import-linter、contract 等）时允许；若无法同时满足，回到「说明阻塞」路径，不要编造通过门禁的假实现。

6) 实现策略：最小改动；优先只触及 task 涉及路径；保持结构可被 CI/本地命令理解。

7) 完成标准：无阻塞时须至少一处与 task 相关的仓库变更，且【How to Test】可复制执行；若步骤 2 已阻塞则无此要求。

8) 输出格式（严格使用以下小节标题；阻塞时【Changes】可为「无（未改仓库）」、【How to Test】可为「N/A」）：

【Task】
- ID: …
- Title: …

【Preconditions】
- 已满足：…  /  或  阻塞：…（须具体）

【Changes】
- 路径 — 简要说明（每行一条）

【How to Test】
- 可复制的命令或步骤

【Limitations】
- 无则写「无」

9) 严禁：聊天中输出「ALL TASKS COMPLETED」；在步骤 2 已阻塞时仍改仓库；无阻塞却无仓库变更即结束；多任务混做。进度由人类在运行本脚本的终端按 Enter 后才记为 done；未完成前不要假定对方已按 Enter。"""

# -------------------------------------------------
# Base path (stable)
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

TASK_FILE = BASE_DIR / "architecture-task-graph.json"
QUEUE_FILE = BASE_DIR / "queue.json"
LOCK_FILE = BASE_DIR / ".task.lock"

ALLOWED_STATUS = frozenset({"ready", "running", "done", "blocked"})
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


# -------------------------------------------------
# Utils
# -------------------------------------------------
def now():
    return datetime.now().isoformat()


# -------------------------------------------------
# Load tasks (safe)
# -------------------------------------------------
def load_tasks():
    if not TASK_FILE.exists():
        raise FileNotFoundError(f"Task file not found: {TASK_FILE}")

    with open(TASK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "tasks" not in data:
        raise ValueError("Invalid schema: missing 'tasks' key")

    return data


# -------------------------------------------------
# Save tasks (preserve full document; atomic replace)
# -------------------------------------------------
def save_tasks(data):
    if "tasks" not in data:
        raise ValueError("save_tasks: data must include 'tasks'")
    tmp = TASK_FILE.with_suffix(TASK_FILE.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(TASK_FILE)


# -------------------------------------------------
# Graph validation (fail fast)
# -------------------------------------------------
def validate_task_graph(data):
    errors = []
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("'tasks' must be a list")
        return errors

    ids = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            errors.append(f"tasks[{i}] is not an object")
            continue
        tid = t.get("id")
        if not tid:
            errors.append(f"tasks[{i}] missing id")
        else:
            ids.append(tid)
        st = t.get("status")
        if st not in ALLOWED_STATUS:
            errors.append(f"{tid or i}: invalid status {st!r}")
        pr = t.get("priority")
        if pr is not None and pr not in PRIORITY_ORDER:
            errors.append(f"{tid or i}: invalid priority {pr!r} (expected P0/P1/P2)")
        deps = t.get("depends_on")
        if deps is not None and not isinstance(deps, list):
            errors.append(f"{tid or i}: depends_on must be a list")
        elif isinstance(deps, list):
            for j, dep in enumerate(deps):
                if not isinstance(dep, str):
                    errors.append(f"{tid or i}: depends_on[{j}] must be a string")

    if len(ids) != len(set(ids)):
        dup = [k for k, v in Counter(ids).items() if v > 1]
        errors.append(f"duplicate task ids: {dup}")

    task_map = {t["id"]: t for t in tasks if isinstance(t, dict) and "id" in t}
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id", "?")
        deps = t.get("depends_on", [])
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if not isinstance(dep, str):
                continue
            if dep not in task_map:
                errors.append(f"{tid}: unknown dependency {dep!r}")

    graph = defaultdict(list)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        tid = t.get("id")
        if not tid:
            continue
        deps = t.get("depends_on", [])
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if isinstance(dep, str) and dep in task_map:
                graph[dep].append(tid)

    visited = set()
    rec = set()

    def dfs_cycle(u):
        if u in rec:
            return True
        if u in visited:
            return False
        rec.add(u)
        for v in graph.get(u, []):
            if dfs_cycle(v):
                return True
        rec.remove(u)
        visited.add(u)
        return False

    for n in task_map:
        if n not in visited and dfs_cycle(n):
            errors.append("dependency graph contains a cycle")
            break

    return errors


# -------------------------------------------------
# Dependency check
# -------------------------------------------------
def is_ready(task, task_map):
    for dep in task.get("depends_on", []):
        if task_map.get(dep, {}).get("status") != "done":
            return False
    return True


# -------------------------------------------------
# Find next task (DAG-safe)
# -------------------------------------------------
def select_next_task(tasks):
    task_map = {t["id"]: t for t in tasks}

    ready = []
    for t in tasks:
        if t.get("status") != "ready":
            continue
        if is_ready(t, task_map):
            ready.append(t)

    if not ready:
        return None

    ready.sort(key=lambda x: (
        PRIORITY_ORDER.get(x.get("priority", "P2"), 9),
        x.get("max_duration_days", 999),
        x.get("id", ""),
    ))

    return ready[0]


# -------------------------------------------------
# Lock system (prevent double run; stale lock auto-clear)
# -------------------------------------------------
def _lock_stale_seconds() -> float:
    raw = os.environ.get("TASKOS_LOCK_STALE_HOURS", str(LOCK_STALE_DEFAULT_HOURS))
    try:
        hours = float(raw)
    except ValueError:
        hours = float(LOCK_STALE_DEFAULT_HOURS)
    return max(60.0, hours * 3600.0)


def _lock_is_stale() -> bool:
    try:
        raw = LOCK_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    parts = raw.split("|", 1)
    if len(parts) != 2:
        return True
    try:
        locked_at = datetime.fromisoformat(parts[1].strip())
    except ValueError:
        return True
    age = (datetime.now() - locked_at).total_seconds()
    return age > _lock_stale_seconds()


def acquire_lock(task_id):
    if LOCK_FILE.exists():
        if _lock_is_stale():
            LOCK_FILE.unlink(missing_ok=True)
        if LOCK_FILE.exists():
            running = LOCK_FILE.read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(
                f"Task already running (delete {LOCK_FILE} if stuck, "
                f"or set TASKOS_LOCK_STALE_HOURS): {running}"
            )

    LOCK_FILE.write_text(f"{task_id}|{now()}", encoding="utf-8")


def release_lock():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink(missing_ok=True)


# -------------------------------------------------
# Queue writer (atomic)
# -------------------------------------------------
def write_queue(task):
    tmp = QUEUE_FILE.with_suffix(".tmp")

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"task": task}, f, indent=2, ensure_ascii=False)

    tmp.replace(QUEUE_FILE)


# -------------------------------------------------
# Detect stuck tasks (auto recovery)
# -------------------------------------------------
def recover_stuck_tasks(tasks):
    for t in tasks:
        if t.get("status") == "running":
            t["status"] = "ready"
    return tasks


# -------------------------------------------------
# Mark done
# -------------------------------------------------
def mark_done(tasks, task_id):
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            t["done_at"] = now()
    return tasks


# -------------------------------------------------
# Main loop
# -------------------------------------------------
def main():
    print("Task OS v2.2 starting...")

    while True:
        data = load_tasks()
        tasks = data["tasks"]

        err = validate_task_graph(data)
        if err:
            print("Task graph validation failed:", file=sys.stderr)
            for e in err:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)

        tasks = recover_stuck_tasks(tasks)

        next_task = select_next_task(tasks)

        if not next_task:
            print("ALL TASKS COMPLETED (no ready task with satisfied dependencies)")
            save_tasks(data)
            break

        task_id = next_task["id"]

        print(f"\nNEXT: {task_id} | {next_task['title']}")

        try:
            acquire_lock(task_id)

            write_queue(next_task)

            for t in tasks:
                if t["id"] == task_id:
                    t["status"] = "running"

            save_tasks(data)

            print("")
            print("--- Cursor 提示词（整段复制到聊天）---")
            print(CURSOR_PROMPT_ZH)
            print("--- end ---")
            print("")
            print(f"Queue file (relative to repo root): docs/tasks/{QUEUE_FILE.name}")

            input("Press ENTER in this terminal after Cursor finishes this task...")

            mark_done(tasks, task_id)
            save_tasks(data)

            print(f"DONE: {task_id}")

        except KeyboardInterrupt:
            print("\nInterrupted. Task left as running; next run will reset stuck running to ready.")
            raise
        finally:
            release_lock()

        time.sleep(0.2)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Task OS: dequeue one ready task into queue.json for Cursor; advance on ENTER.",
    )
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate architecture-task-graph.json (schema, ids, deps, cycles) and exit.",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    if args.validate_only:
        data = load_tasks()
        err = validate_task_graph(data)
        if err:
            print("Task graph validation failed:", file=sys.stderr)
            for e in err:
                print(f"  - {e}", file=sys.stderr)
            raise SystemExit(1)
        print("OK: task graph valid")
        raise SystemExit(0)
    main()
