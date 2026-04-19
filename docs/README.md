# 文档索引

本目录存放**衍生说明**、**任务与清单**、**架构视图**。契约与门禁的**最高真源**在仓库 **`spec/`** 目录（与 `docs/` 并列）。

**全库文档分类总目**：[**DOCUMENT-CATALOG.md**](./DOCUMENT-CATALOG.md)

---

## 仓库目录结构（`spec/` + `docs/`）

| 路径 | 类别 | 内容 |
|------|------|------|
| [`../spec/`](../spec/) | **规范真源** | `contract.yaml`、`architecture.spec.md`、`execution_plan.md`（见 [`spec/README.md`](../spec/README.md)） |
| [`requirements/`](./requirements/) | 需求提炼 | `spec-extraction-*.md` |
| [`architecture/`](./architecture/) | 系统架构视图 | `system-architecture.md`、`system-architecture-modules.dot` |
| [`tasks/`](./tasks/) | 任务 DAG + 实现清单 | `architecture-task-graph.*`、`todolist.md` |
| [`arch/`](./arch/) | 架构决策 / 入口表 | ADR、`llm_entrypoints.md`（**勿改路径**：CI 硬编码） |
| `docs/` 根 | 导航 | `README.md`（本文件）、`DOCUMENT-CATALOG.md` |

---

## 文档类别速览

| 类别 | 代表路径 |
|------|----------|
| 规范真源 | `spec/contract.yaml`、`spec/architecture.spec.md`、`spec/execution_plan.md` |
| 需求提炼 | `docs/requirements/spec-extraction-*.md` |
| 架构视图 | `docs/architecture/system-architecture.md`、`docs/architecture/system-architecture-modules.dot` |
| 决策 / 入口表 | `docs/arch/ADR-*.md`、`docs/arch/llm_entrypoints.md` |
| 任务 DAG / 实现清单 | `docs/tasks/architecture-task-graph.*`、`docs/tasks/todolist.md` |
| 设计底稿 | `.cursor/plans/*.plan.md` |
| 工程门禁 | `.importlinter`、`.github/workflows/ci.yml` |
| 协作规则 | `.cursor/rules/*.mdc` |

---

## 建议阅读顺序

1. **规范真源**（[`spec/`](../spec/)）：`contract.yaml` → `architecture.spec.md` → `execution_plan.md`
2. **需求全景**：[requirements/spec-extraction-full.md](./requirements/spec-extraction-full.md)
3. **系统架构**：[architecture/system-architecture.md](./architecture/system-architecture.md) + [architecture/system-architecture-modules.dot](./architecture/system-architecture-modules.dot)
4. **落地任务图**：[tasks/architecture-task-graph.json](./tasks/architecture-task-graph.json) / [tasks/architecture-task-graph.md](./tasks/architecture-task-graph.md)
5. **实现清单**：[tasks/todolist.md](./tasks/todolist.md)
6. **ADR**：[arch/](./arch/) 按需查阅

---

## 规范真源（`spec/`，不在 `docs/` 内）

| 路径 | 内容 |
|------|------|
| [`../spec/contract.yaml`](../spec/contract.yaml) | OpenAPI：HTTP 形状、错误码、`AsyncTaskStatus`、队列与 payload |
| [`../spec/architecture.spec.md`](../spec/architecture.spec.md) | 分层、禁止/必须规则、CI 矩阵、与契约联动说明 |
| [`../spec/execution_plan.md`](../spec/execution_plan.md) | 四域 × 阶段交付、异步与 Worker 验收要点 |

---

## `docs/arch/`（架构决策 / 运维真源）

目录说明：[arch/README.md](./arch/README.md)

| 文件 | 用途 |
|------|------|
| [ADR-document-pdf-parse-to-document-jobs.md](./arch/ADR-document-pdf-parse-to-document-jobs.md) | `pdf_parse` → `document_jobs` 时序 |
| [ADR-reconcile-jobs-and-w4.md](./arch/ADR-reconcile-jobs-and-w4.md) | `reconcile_jobs` 与 W4 / `use_cases` |
| [ADR-W3b-uc-enqueue.md](./arch/ADR-W3b-uc-enqueue.md) | W3b（UC 入队）启用时的评审与工具链 |
| [llm_entrypoints.md](./arch/llm_entrypoints.md) | LLM 编排唯一入口表（R-UC-ONLY；须随 UC 变更更新） |

---

## 脚本与生成物

| 路径 | 说明 |
|------|------|
| [`../scripts/gen_architecture_task_graph_md.py`](../scripts/gen_architecture_task_graph_md.py) | 根据 `docs/tasks/architecture-task-graph.json` 生成 `docs/tasks/architecture-task-graph.md` |

```bash
python scripts/gen_architecture_task_graph_md.py
```

Graphviz 渲染模块图（需本机安装 `dot`）：

```bash
dot -Tsvg docs/architecture/system-architecture-modules.dot -o docs/architecture/system-architecture-modules.svg
```

---

## `todolist.md` 与架构任务图

- **`docs/tasks/todolist.md`**：偏**数据模型与实现清单**（历史主线）。
- **`docs/tasks/architecture-task-graph.*`**：偏**架构分层与模块落地的原子任务 DAG**（与 `docs/architecture/system-architecture.md` 对齐）。

二者互补；冲突时以 **`spec/` 三份真源** + **`docs/arch/` ADR** 为准。
