# ADR：`reconcile_jobs` 与 W4（`*_jobs` → `use_cases`）的一致性

## 状态

**已采纳**（消除 `architecture.spec.md` **§1.1 W4** 与 **§3 M-CHAIN-WORKER** 在「是否每个 job 都须进 `UC`」上的表述张力）。

## 背景

- **W4** 要求：每个 **`task/*_jobs.py`** 在消费路径上须调用 **`app.use_cases`**（便于 grep/审计）。  
- **M-CHAIN-WORKER** 正文仅枚举 **`chat_jobs` / `document_jobs` / `keyword_jobs`** 须经 **`UC`→`adapter`** 的集成断言。  
- **`reconcile_jobs`** 不调 LLM、不进入 `adapter.llm`，但对 **`assignments` 与 `topics.selected_count`** 的修复顺序仍属 **编排**（与 **R-TASK-BIZ**「禁止在 job 内写第二套业务编排」一致：编排应在 **`UC`**）。

## 决策

1. **新增薄编排模块**（命名建议二选一，实现时写死其一）：  
   - `app/use_cases/selection_reconcile.py`，或  
   - `app/use_cases/reconciliation.py`  
   对外暴露 **单一入口**（示例名）：**`run(payload: ReconcileJobPayload)`**（载荷形状与 **`contract.yaml` → `ReconcileJobPayload`** 一致；Python 侧可用 dataclass/TypedDict）。

2. **`task/reconcile_jobs.py`**  
   - 仅负责：反序列化、幂等键/`reconcile_job_id` 守卫、调用 **`use_cases` 上述入口**、结构化日志、**状态/审计写回**（若有表）、错误映射。  
   - **禁止**：在 job 文件内实现完整对账 SQL/规则而不经 `UC`；**禁止** `import app.adapter`（**R-UC-SKIP** 不变）。

3. **`M-CHAIN-WORKER` 的解读**  
   - 枚举三项为 **「须断言经 `UC` 调 LLM/adapter」** 的 P0 集成范围。  
   - **`reconcile_jobs`** 仍须满足 **W4**（**`*_jobs` → `UC` 至少一次调用**），**不要求** **`adapter`** 调用链。

4. **与 `execution_plan` 阶段 3 的关系**  
   - **`SelectionService`** 在 **`accept` 事务 `commit` 成功后** `enqueue(reconcile_jobs)` 的义务 **不变**；对账算法 **不** 迁到 `SVC` 复制第二套。

## 后果

- **CI**：`rg`「每个 `*_jobs.py` 含 `use_cases`」对 **`reconcile_jobs`** 同样生效，无需豁免。  
- **`docs/arch/llm_entrypoints.md`**：在 **「非 LLM Worker 编排」** 表登记本入口（见该文件第二节）；**不**将本入口计入 LLM 台账行，除非未来错误地引入 `adapter.llm`。  
- **可选后续**：在 **`architecture.spec.md` 的 M-CHAIN-WORKER** 中增加一句「`reconcile_jobs` 须调 `UC`、不调 `adapter`」以与 W4 完全一致（本 ADR 为直至该修订前的真源）。

## 审阅

- 架构：`architecture.spec.md` **R-TASK-BIZ**、**R-UC-SKIP**、**R-TASK-API**、**R-UC-API**。  
- 计划：`execution_plan.md` 阶段 3 **selection**、阶段 4 **`reconcile_jobs`**。  
- 契约：`contract.yaml` **`ReconcileJobPayload`**、**`x-task-contracts.queues.reconcile_jobs`**。
