# 文档总目（分类汇总）

> 本文档按**类别**汇总仓库内与毕设相关的**可读说明、规范、决策与清单**；路径均为相对仓库根目录，除非另行标注。  
> **冲突裁决**：以 **`spec/contract.yaml`**、**`spec/architecture.spec.md`**、**`spec/execution_plan.md`** 为最高优先级，其次为 **`docs/arch/ADR-*.md`**。

---

## 仓库目录速览（`spec/` + `docs/`）

| 路径 | 类别 | 说明 |
|------|------|------|
| **`spec/`** | **规范真源** | 契约、架构门禁规格、阶段交付计划（见 [`spec/README.md`](../spec/README.md)） |
| **`docs/requirements/`** | 需求提炼 | 从规范归纳的功能/REST/后台任务面 |
| **`docs/architecture/`** | 系统架构视图 | 分层说明 + Graphviz 模块依赖图 |
| **`docs/tasks/`** | 任务与清单 | 原子任务 DAG、`todolist.md`（实现清单） |
| **`docs/arch/`** | 架构决策 / 入口表 | ADR、`llm_entrypoints.md`（**路径保持**，与 CI、`check_llm_entrypoints_doc.py` 硬编码一致） |
| **`docs/` 根** | 导航 | `README.md`、`DOCUMENT-CATALOG.md`（本文件） |

子目录导读：[spec/README.md](../spec/README.md) · [requirements/README.md](./requirements/README.md) · [architecture/README.md](./architecture/README.md) · [tasks/README.md](./tasks/README.md) · [arch/README.md](./arch/README.md)

---

## 一、规范与契约（真源，`spec/`）

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`spec/contract.yaml`](../spec/contract.yaml) | **接口与任务契约** | OpenAPI：REST 路径、Schema、`ErrorEnvelope`、`AsyncTaskStatus`、`x-task-contracts.queues` 与各 Job Payload。 |
| [`spec/architecture.spec.md`](../spec/architecture.spec.md) | **架构门禁规格** | 分层白名单/禁止规则、Policy、队列一致性、CI 矩阵、与契约的联动说明。 |
| [`spec/execution_plan.md`](../spec/execution_plan.md) | **阶段交付计划** | 四域 × model/use_cases/service/task/api；异步与 Worker 验收表述。 |

---

## 二、需求提炼（`docs/requirements/`）

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`docs/requirements/spec-extraction-full.md`](./requirements/spec-extraction-full.md) | **需求全景** | 功能清单、非功能需求、边界条件、NOT IN SCOPE。 |
| [`docs/requirements/spec-extraction-rest-paths.md`](./requirements/spec-extraction-rest-paths.md) | **HTTP 面** | 仅 REST 路径与方法表（相对 `/api/v1`）。 |
| [`docs/requirements/spec-extraction-background-tasks.md`](./requirements/spec-extraction-background-tasks.md) | **异步与队列面** | 队列键、Payload、状态机、Service/Worker 行为、与 REST 对应关系。 |

---

## 三、系统架构与设计视图（`docs/architecture/`）

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`docs/architecture/system-architecture.md`](./architecture/system-architecture.md) | **架构说明** | 分层文字图、Service 拆分、模块划分、数据流、API 边界。 |
| [`docs/architecture/system-architecture-modules.dot`](./architecture/system-architecture-modules.dot) | **模块依赖图（Graphviz）** | 允许依赖边；需 `dot` 渲染为 svg/png。 |

---

## 四、架构决策与运维真源（`docs/arch/`）

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`docs/arch/ADR-document-pdf-parse-to-document-jobs.md`](./arch/ADR-document-pdf-parse-to-document-jobs.md) | **ADR** | `pdf_parse` → `document_jobs` 时序与实现边界。 |
| [`docs/arch/ADR-reconcile-jobs-and-w4.md`](./arch/ADR-reconcile-jobs-and-w4.md) | **ADR** | `reconcile_jobs` 与 W4、`use_cases` 关系。 |
| [`docs/arch/ADR-W3b-uc-enqueue.md`](./arch/ADR-W3b-uc-enqueue.md) | **ADR** | W3b（UC 入队）启用条件与工具链同步要求。 |
| [`docs/arch/llm_entrypoints.md`](./arch/llm_entrypoints.md) | **运维/评审表** | LLM 编排唯一入口（R-UC-ONLY）；须随 `app/use_cases` 变更更新。 |

---

## 五、任务分解与执行清单

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`docs/tasks/architecture-task-graph.json`](./tasks/architecture-task-graph.json) | **原子任务 DAG（机器可读）** | `tasks[].depends_on` 为前置边；每项 ≤2 天粒度。 |
| [`docs/tasks/architecture-task-graph.md`](./tasks/architecture-task-graph.md) | **原子任务（分层可读）** | 由脚本自 JSON 生成，勿手改正文。 |
| [`docs/tasks/todolist.md`](./tasks/todolist.md) | **实现清单（数据/域）** | 表结构、迁移、域实现等历史主线；与架构任务图互补。 |

**生成脚本**：

| 路径 | 说明 |
|------|------|
| [`scripts/gen_architecture_task_graph_md.py`](../scripts/gen_architecture_task_graph_md.py) | `docs/tasks/architecture-task-graph.json` → `docs/tasks/architecture-task-graph.md`。 |

---

## 六、设计推导与历史底稿

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`.cursor/plans/毕设系统架构推导_8fd2e706.plan.md`](../.cursor/plans/毕设系统架构推导_8fd2e706.plan.md) | **规划/推导长文** | 被 `spec/architecture.spec.md` / `spec/execution_plan.md` 引用；若与真源冲突以 `spec/` 为准。 |

---

## 七、工程门禁与配置（「配置即文档」）

| 路径 | 类别说明 | 摘要 |
|------|----------|------|
| [`.importlinter`](../.importlinter) | **Import 分层合约** | 与 `spec/architecture.spec.md` §4 对齐的 forbidden 边。 |
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | **CI 流水线** | 自动化检查入口；细则条文仍以 `spec/architecture.spec.md` §5 为准。 |

---

## 八、协作与编辑器规则

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`.cursor/rules/tdd.mdc`](../.cursor/rules/tdd.mdc) | **Cursor 规则** | TDD / 测试相关约束（本仓库 AI 与本地协作）。 |

---

## 九、索引与入口（导航）

| 文档 | 类别说明 | 摘要 |
|------|----------|------|
| [`README.md`](../README.md) | **仓库入口** | 指向 `docs/README.md`。 |
| [`docs/README.md`](./README.md) | **`docs/` 索引** | 目录结构、阅读顺序、`docs/arch/` 表、脚本命令。 |
| [`docs/DOCUMENT-CATALOG.md`](./DOCUMENT-CATALOG.md) | **本文** | 全库文档分类总目。 |

---

## 十、非 Markdown 但属「规范载体」

| 路径 | 类别说明 |
|------|----------|
| [`spec/contract.yaml`](../spec/contract.yaml) | OpenAPI YAML，可与 `openapi-spec-validator` 校验（见 `spec/architecture.spec.md` CI 建议）。 |

---

## 维护说明

- 新增 **ADR**：放入 **`docs/arch/`**，并在本节与 [`docs/README.md`](./README.md) 补充一行。  
- 新增 **需求/架构视图文档**：放入 **`docs/requirements/`** 或 **`docs/architecture/`**，并更新本文件与 `docs/README.md`。  
- **`docs/tasks/architecture-task-graph.md`**：仅通过 `scripts/gen_architecture_task_graph_md.py` 由 JSON 再生，避免与 JSON 漂移。  
- **勿移动 `docs/arch/` 下被 CI 与 `spec/architecture.spec.md` 引用的文件名**（如 `llm_entrypoints.md`）。  
- **勿移动 `spec/` 下三份真源文件名**；若改名须同步 `tests/`、`scripts/ci/check_queue_contract_keys.py`、`scripts/check_rules.py` 等所有硬编码路径。
