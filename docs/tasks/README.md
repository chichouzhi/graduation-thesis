# 任务编排（Task OS）

本目录用 **机器可读 DAG**（`architecture-task-graph.json`）分解毕设落地步骤，并用 **`auto-run.py`** 每次只向 Cursor 暴露 **一条** 当前任务（`queue.json`），避免一次对话做太多事、难以验收。

**冲突裁决**：实现口径仍以仓库根目录 **`spec/contract.yaml`**、**`spec/architecture.spec.md`**、**`spec/execution_plan.md`** 为准；任务条目标题是摘要，细节以规范与代码为准。

---

## 文件职责

| 文件 | 职责 |
|------|------|
| **`architecture-task-graph.json`** | **唯一进度真源**：每个任务的 `status`（`ready` / `running` / `done` / `blocked`）、`depends_on`、`priority` 等。 |
| **`queue.json`** | **当前派发给 AI 的一条任务**（由脚本写入，**不要**当进度本手改）。 |
| **`.task.lock`** | 防止多终端同时跑编排脚本；异常退出可能残留，可按 README 故障排除处理。 |
| **`auto-run.py`** | **单任务串行循环**：选下一个可执行任务 → 写 `queue.json` → 标 `running` → 等人按 Enter → **仅**标该条 `done` → 再选下一条；**禁止**并发多条 `running`、**不会**在启动时把全部 `running` 批量打回 `ready`。 |
| **`architecture-task-graph.md`** | 由 `scripts/gen_architecture_task_graph_md.py` 从 JSON **生成**，勿手改正文。 |
| **`todolist.md`** | 人类可读实现清单，与任务图互补；**范围裁决**以当前 `queue.json` 中的 `task` 为准。 |

---

## 快速开始

### 1. 校验任务图（改 JSON 后、提交前）

在**仓库根目录**执行：

```bash
python docs/tasks/auto-run.py --validate-only
```

成功时打印 `OK: task graph valid`。  
该检查已接入：

```bash
python scripts/check_rules.py
```

（规则展示名：`DOCS-TASK-GRAPH`。）

### 2. 交互式推进（终端 + Cursor）

1. 仓库根目录执行：

   ```bash
   python docs/tasks/auto-run.py
   ```

2. 终端会打印 **当前任务 id/title**，以及一段 **可复制到 Cursor 的提示词**（见下节）。

3. 在 Cursor 聊天中 **粘贴** 该提示词（或你自己保存的模板），让 Agent 只完成 `queue.json` 中的那一条。

4. 在 Cursor 里确认实现与自测都满意后，回到 **运行脚本的终端**，按 **Enter**，脚本会把该任务标为 `done` 并选下一条。

5. 重复直到脚本退出（没有可执行的 `ready` 任务）。

**单任务 / 不并发约定**

- 任意时刻任务图中 **`running` 至多一条**；若 JSON 里出现多条 `running`，脚本会 **直接报错退出**，需人工改图。
- 若上一轮异常中断（Ctrl+C），图中可能残留 **一条** `running` 且无锁：下次启动脚本会把 **这一条** 降回 `ready` 再重新派发（**不会**把无关任务一并 reopen）。
- Cursor 侧：**每一轮对话只完成当前 `queue.json` 的一条 AG**；不要用同一轮 diff 批量把多条任务标 `done`。批量修补图请用 `TASKOS_BATCH_MARK_OK=1` 且仅限运维场景（见 `scripts/tasks/export_ready_tasks.py` 说明）。

### 3. 环境变量（可选）

| 变量 | 含义 | 默认 |
|------|------|------|
| **`TASKOS_LOCK_STALE_HOURS`** | `.task.lock` 超过该小时数视为陈旧；启动时若需回收孤儿 `running` 会先删陈旧锁 | `48` |
| **`TASKOS_BATCH_MARK_OK`** | 设为 `1` 时允许 `scripts/tasks/export_ready_tasks.py --mark-done` 一次写多个 id（默认禁止，与单任务模式一致） | （未设置） |

---

## Cursor 提示词（推荐直接复制）

**单一真源**：中文主提示词与 `auto-run.py` 顶部的 `CURSOR_PROMPT_ZH` 字符串一致；若修改措辞请**同时改**脚本与本文档本节。

将下面整块复制到 Cursor 聊天（运行 `auto-run.py` 时终端也会打印同一段）：

```text
你正在执行 Task OS 派发的单条任务（与终端里的 auto-run.py 配对）。

【强约束：先做条件完备验证，再改仓库；禁止空跑与假完成】

1) 读取 docs/tasks/queue.json
   - 若文件不存在、JSON 无法解析、缺少顶层键 task、或 task 为空/非对象：
     → 在回复中写明原因；停止执行本任务（不要假装已完成）。
   - 「ALL TASKS COMPLETED」只能由终端里的 auto-run.py 在任务图耗尽时打印；你不得在聊天中用该句表示本任务状态。
   - **单任务**：本轮对话与本轮 diff **只**服务 `queue.json` 中的这一条 AG；**禁止**在同一轮把其它 `ready` 任务标为 `done`、禁止批量改 `architecture-task-graph.json` 关多条任务（关账仅由本终端按 Enter 触发、一次一条）。

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

9) 严禁：聊天中输出「ALL TASKS COMPLETED」；在步骤 2 已阻塞时仍改仓库；无阻塞却无仓库变更即结束；多任务混做；**一次合并关闭多条 AG** 或顺带实现其它 `queue.json` 外的任务。进度由人类在运行本脚本的终端按 Enter 后才记为 done；未完成前不要假定对方已按 Enter。
```

**为何先做条件完备验证**：避免在 `queue` 损坏、真源缺失或 task 与 spec 明显冲突时仍改仓库；阻塞时允许零 diff，由人类修复环境或任务图后再跑。**为何不把「必须改代码」写死**：任务图里含文档/CI/配置类条目，交付物应是**可提交的仓库变更**，不限定为 `.py`。**为何收紧 stub**：与 `spec/`、TDD 与 import-linter 等门禁一致，避免「占位骗过对话」。

### 英文短版（可选）

```text
You are executing exactly one task from Task OS.

1. Read docs/tasks/queue.json
2. Implement only the object in the `task` field; do not expand scope to other AG-xx items.
3. Prefer evidence from spec/contract.yaml and spec/architecture.spec.md when unclear.
4. Summarize changed paths and how you verified. The human presses Enter in the auto-run terminal to mark the task done.
```

---

## 任务状态与依赖

- **`depends_on`**：所列任务 id **均为 `done`** 后，本任务才可能被选中（`status` 为 `ready` 且依赖满足）。
- **`priority`**：`P0` 先于 `P1` 先于 `P2`（同优先级时按脚本内稳定排序）。
- **`recover`**：若上次异常退出导致某条停在 `running`，下次启动脚本会把异常的 `running` 重置为 `ready` 再调度（仍建议人工确认未误标 done）。

---

## 故障排除

| 现象 | 处理 |
|------|------|
| 报错已有任务在跑 / `.task.lock` 存在 | 确认没有第二个终端在跑 `auto-run.py`；若已卡死，删除 `docs/tasks/.task.lock` 后重试。 |
| 锁长期不释放 | 调小 `TASKOS_LOCK_STALE_HOURS` 做测试，或等待超过默认陈旧时间后自动清除。 |
| `queue.json` 与记忆不一致 | 以 **`architecture-task-graph.json`** 为准；重新运行脚本会重写 `queue.json`。 |
| 校验失败 | 根据 `--validate-only` 或 `check_rules.py` 的报错修 JSON（重复 id、未知依赖、环、`status`/`priority`/`depends_on` 类型等）。 |

---

## 与 CI 的关系

- `python docs/tasks/auto-run.py --validate-only`：任务图结构校验。  
- `python scripts/check_rules.py`：包含上述校验及其它架构静态规则。

---

## 相关链接

- 文档总目：[docs/DOCUMENT-CATALOG.md](../DOCUMENT-CATALOG.md)  
- 任务图 Markdown 生成：`python scripts/gen_architecture_task_graph_md.py`
