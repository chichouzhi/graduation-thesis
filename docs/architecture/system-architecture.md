# 系统架构设计（基于 spec + contract）

> **文档导航**：[分类总目](../DOCUMENT-CATALOG.md) · [文档索引](../README.md) · [规范提取（完整）](../requirements/spec-extraction-full.md) · [架构任务图（JSON）](../tasks/architecture-task-graph.json) · [架构任务图（分层 MD）](../tasks/architecture-task-graph.md)  
> **真源**：`spec/architecture.spec.md`、`spec/contract.yaml`、`spec/execution_plan.md`。  
> **模块依赖 DAG（Graphviz）**：[`system-architecture-modules.dot`](./system-architecture-modules.dot)。

---

## 0. 应用引导（bootstrap）与任务图对齐

本节补全 **`architecture-task-graph.json` 中 `layer: "bootstrap"`**（如 **AG-001**）在架构视图中的落点；实现细则仍以 **`spec/architecture.spec.md`**（路径 glob、§1.3 基础设施）与 **任务图各条 `title`** 为准。

| 主题 | 约定 |
|------|------|
| **应用工厂** | 使用 Flask **Application Factory**：在 **`app` 包**内提供 **`create_app`**（常见为 `app/__init__.py`），返回已配置、可挂到 WSGI 的 `Flask` 实例；**禁止**把业务域路由堆在单一巨型 `routes.py` 而无域包边界（域划分见下节「模块划分」表）。 |
| **AG-001 边界** | **骨架**：可加载配置、建立扩展占位钩子、健康检查或根路径等**非业务域**路由均可；**不在此条**注册 **`/api/v1` 下八大域 Blueprint 空壳**——该交付属于任务图 **AG-004**，避免与「无业务域路由」的验收口径冲突。 |
| **横切文件** | `app/config.py`、`app/extensions.py`（及 **`app/common/**`**）为各层可引基础设施，与 **`spec/architecture.spec.md` §1.3** 一致；**DB 迁移 / JWT 等挂载细节**以任务图 **AG-002** 及后续条为准，本文不展开。 |
| **进程与入口** | **PROC_API** 为运行该 Flask 应用的 API worker（见下「进程视图」）；仓库级 **`wsgi.py`**、`Dockerfile` **CMD**、或 **`python -m flask`** 等入口须**调用工厂**而非散落全局 `app` 单例（具体文件名以仓库为准，**须可被 CI/本地一条命令启动**）。 |

**文档完备性说明**：若仅依赖本节 + 分层图 + spec，应能判断 AG-001 是否「只做工厂与骨架、域路由留给 AG-004」；若任务图 `title` 与本文表格冲突，**以任务图 + spec 为裁决**。

---

## 1. 分层架构图（文字版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  HTTP 边界（OpenAPI / contract.yaml paths）                                  │
│  identity | terms | taskboard | chat | document | topic | selection |      │
│  recommendations（只读）                                                     │
│  职责：鉴权、校验、序列化、状态码；仅调用同域 service                         │
│  禁止：import adapter / use_cases / task / ORM models 业务读写              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │  W1：API → SVC
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Service 层（领域入口：事务 + 规则 + Policy + 入队决策）                      │
│  IdentityService | TermService | MilestoneService                            │
│  ChatService | DocumentService | TopicService | SelectionService             │
│  RecommendService（只读聚合，无 LLM）                                       │
│  允许：model、common.policy、use_cases（仅受理侧组装/计划数据结构）           │
│        app.task.queue（enqueue_*）                                         │
│  禁止（生产默认）：直连 adapter.llm；阻塞等待整段 LLM 后返回 HTTP              │
└───────┬─────────────────────┬──────────────────────────────┬───────────────┘
        │ W2                  │ W3                           │
        │ 函数调用             │ 仅入队门面                    │
        ▼                     ▼                              …
┌──────────────────┐   ┌─────────────────────────────────────────────────────┐
│  use_cases       │   │  task.queue（enqueue；队列名与 contract 一致）        │
│  唯一编排层       │   │  禁止：API / *_jobs 绕过 SVC 与 queue 约定直接入队       │
│  chat_orchestration │  禁止：task 包 import adapter                         │
│  document_pipeline  │                                                    │
│  topic_keywords       │   ┌──────────────────────────────────────────────┐   │
│  （及 reconcile 等   │   │  PROC_WORKER：task/*_jobs                     │   │
│   ADR 规定的 UC 入口） │   │  薄壳：payload → UC → 状态/结果回写 DB         │   │
└────────┬─────────┘   │   │  每个 *_jobs 必须调用 app.use_cases（W4）       │   │
         │ W5          │   └───────────────────────┬────────────────────────┘   │
         ▼             │                           │ W4                          │
┌────────────────┐     │                           └──────────► use_cases ───────►│
│  adapter       │     │                                        （再 W5）adapter  │
│  llm | pdf     │     └──────────────────────────────────────────────────────────┘
│  nlp | storage │
└────────┬───────┘
         │ 外部系统 / 存储
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  model（各域 ORM/持久化）+ DB；API 不得直连业务读写                          │
└─────────────────────────────────────────────────────────────────────────────┘

横切：common（Policy 门面等）、extensions、config；第三方库按 spec 各层可引用基础设施。
```

### 进程视图（与分层正交）

| 进程 | 职责 |
|------|------|
| **PROC_API** | Flask/Gunicorn API worker：**受理与查询**；**不得**在请求线程内同步阻塞等 LLM 整段生成。 |
| **PROC_WORKER** | 消费 broker 队列；**adapter.llm** 主生成路径须在 **Worker 栈** 内经 **use_cases** 到达。 |

---

## 2. Service 拆分

| Service | 职责摘要 |
|---------|----------|
| **IdentityService** | 登录/刷新/登出；`/users/me`；令牌与 Cookie 策略与架构 spec 一致。 |
| **TermService** | `/terms` CRUD；`/terms/{id}/llm-config`；角色可见范围裁剪。 |
| **MilestoneService** | `/milestones`；教师按 `student_id` 查询时的指导关系校验。 |
| **ChatService** | 会话与消息；发消息：**UC 组装** → **Policy** → 占位写库 **commit** → **`enqueue(chat_jobs)`** → **202**。 |
| **DocumentService** | 校验、Storage、`document_tasks`；Policy → commit → **`enqueue(pdf_parse)`**；`document_jobs` 在 pdf 成功路径再入队（ADR）。 |
| **TopicService** | 课题 CRUD、审核；**Jieba 同步**；生产默认 **仅 `enqueue(keyword_jobs)`** 做 LLM 抽词。 |
| **SelectionService** | 志愿与 **assignments** 真源、**selected_count**；**accept + commit** 后 Policy/同等检查 → **`enqueue(reconcile_jobs)`（P0）**。 |
| **RecommendService** | **`GET /recommendations/topics`**：只读打分；**禁止** llm / 用 nlp 替代 Topic 写路径。 |

**说明**：Selection **不强制**独立 `use_cases` 文件；但 **`reconcile_jobs` 消费须 W4**（job → UC），与 [`../arch/ADR-reconcile-jobs-and-w4.md`](../arch/ADR-reconcile-jobs-and-w4.md) 一致。

---

## 3. Module 划分

| 域包 | 典型结构 |
|------|----------|
| `app.identity` | `api` → `service` → `models` |
| `app.terms` | `api` → `service` → `models` |
| `app.taskboard` | `api` → `service` → `models` |
| `app.chat` | `api` → `service` → `models` |
| `app.document` | `api` → `service` → `models` |
| `app.topic` | `api` → `service` → `models` |
| `app.selection` | `api` → `service` → `models` |
| `app.recommendations` | `api` + `service`（只读；包名须为 `app.recommendations.api`） |
| `app.use_cases` | chat / document / topic（及 ADR 规定的 reconcile 等 UC 入口） |
| `app.task` | `queue`；`chat_jobs`、`pdf_parse_jobs`、`document_jobs`、`keyword_jobs`、`reconcile_jobs` |
| `app.adapter` | `llm`、`pdf`、`nlp`、`storage` |
| `app.common` | PolicyGateway（或等价门面）等 |

---

## 4. 数据流（主路径）

1. **Chat 发消息**：API → ChatService → UC（组装）→ Policy → DB 占位 → commit → enqueue(`chat_jobs`) → **202**。Worker：`chat_jobs` → UC → llm → 回写。
2. **Document 上传**：API → DocumentService → Storage + `document_tasks` → Policy → commit → enqueue(`pdf_parse`) → **202**；成功后经 UC 编排 enqueue(`document_jobs`)（ADR）。
3. **Topic 抽词**：API → TopicService → Jieba；需 LLM 时 Policy → commit → enqueue(`keyword_jobs`)。Worker：UC → llm → portrait。
4. **Selection accept**：API → SelectionService → 事务更新 assignments / 计数 → Policy → commit → enqueue(`reconcile_jobs`)。Worker：UC → 对账回写。
5. **Recommendations**：API → RecommendService → 只读 DB，**无队列、无 LLM**。
6. **Policy 拒绝**：429/503 + `ErrorEnvelope`，**enqueue 不调用**。
7. **入队失败**：占位已提交则补偿 **failed + QUEUE_UNAVAILABLE**（或契约等价）。

---

## 5. API 边界

| 项 | 约定 |
|----|------|
| 基路径 | `spec/contract.yaml`：`/api/v1`。 |
| 异步受理 | `POST .../messages`、`POST /document-tasks`：**202**；API worker **不等** LLM 完成。 |
| 错误体 | 全局 **ErrorEnvelope**；与 Policy/队列枚举一致。 |
| SSE | `GET .../stream` **可选**；未启用 **404/501** 且 JSON **ErrorEnvelope**。 |
| 内部队列 | **reconcile_jobs** **无 REST**；仅内部 enqueue。 |
| 路由实现 | **仅**调用同域 **service**；不得穿透 **use_cases / task / adapter / models**。 |

---

## 6. 模块依赖 DAG

- **机器可读边表**：见 **`system-architecture-modules.dot`**（`digraph`：`rankdir=TB`，实线表示 **允许** 的依赖方向：上层模块依赖下层）。
- **禁止边**（勿在 DOT 中实现为依赖）：`*.api` → `use_cases|adapter|task|models`；`task` → `adapter|*.api`；`use_cases` → `*.api|flask.request`；`recommendations` → `adapter.llm` 及「nlp 替代 Topic 写路径」；Chat/Document/Topic 的 `*.service` → `adapter.llm`（生产默认）。

渲染示例（需本机安装 Graphviz）：

```bash
dot -Tpng docs/architecture/system-architecture-modules.dot -o docs/architecture/system-architecture-modules.png
dot -Tsvg docs/architecture/system-architecture-modules.dot -o docs/architecture/system-architecture-modules.svg
```

---

## 7. 相关文档索引

| 文档 | 用途 |
|------|------|
| [`DOCUMENT-CATALOG.md`](../DOCUMENT-CATALOG.md) | **全库文档分类总目** |
| [`README.md`](../README.md) | **`docs/` 索引**与阅读顺序 |
| `spec/architecture.spec.md` | 分层门禁、CI、Policy、队列一致性 |
| `spec/contract.yaml` | HTTP 形状、状态码、队列与 payload 真源 |
| `spec/execution_plan.md` | 阶段交付与四域矩阵 |
| [`architecture-task-graph.json`](../tasks/architecture-task-graph.json) | 原子任务 DAG（`depends_on`） |
| [`architecture-task-graph.md`](../tasks/architecture-task-graph.md) | 任务图分层可读版（可由脚本重生成） |
| [`ADR-document-pdf-parse-to-document-jobs.md`](../arch/ADR-document-pdf-parse-to-document-jobs.md) | pdf_parse → document_jobs 时序 |
| [`ADR-reconcile-jobs-and-w4.md`](../arch/ADR-reconcile-jobs-and-w4.md) | reconcile 与 W4 / UC |
| [`spec-extraction-full.md`](../requirements/spec-extraction-full.md) | 功能/非功能/边界/NOT IN SCOPE 汇总 |

---

## 8. 任务图 `layer` 与文档路由（其余条目是否「有处可查」）

`architecture-task-graph.json` 中每条仅有 **`title` + `layer` + `depends_on`** 级摘要；**不要求** `system-architecture.md` 逐条复述 AG 编号。下表说明各 **layer** 应优先读哪些真源，用于判断「剩余条目」是否在文档体系内**有明确落点**（而非缺文档）。

| `layer` | 主要真源（按推荐阅读顺序） | 完备性说明 |
|---------|-----------------------------|------------|
| **`bootstrap`** | 本文 **§0**、`spec/architecture.spec.md` §0～§1.3、`architecture-task-graph` 对应 `title` | **已显式对齐** AG-001/004 边界。 |
| **`common`** | `spec/architecture.spec.md` §2（R-API-*、Policy、ErrorEnvelope 相关）、`spec/contract.yaml`（错误码/枚举）、本文 **§1 图** | 规则与契约 **足**；具体类名以任务 `title` + 契约为准。 |
| **`model`** | **`spec/execution_plan.md` 阶段 1**、`spec/contract.yaml`（Schema/必填字段）、本文 **§1 底「model」** | **最细**：表名、状态机、与契约字段对齐在 execution_plan 与 contract。 |
| **`adapter`** | 本文 **§3**（`app.adapter` 子包）、**§6 DOT**、`spec/architecture.spec.md`（W5、R-SVC-LLM、R-REC-LLM 等） | **概念与边界足**；厂商/SDK 细节不在架构视图展开，由实现与 ADR 补充。 |
| **`use_cases`** | **`spec/execution_plan.md` 阶段 2**、本文 **§1「唯一编排层」**、**R-UC-ONLY**（`docs/arch/llm_entrypoints.md` 等脚本契约） | **足**；单条 UC 文件名以任务图 + execution_plan 为准。 |
| **`task_queue`** | `spec/contract.yaml` → `x-task-contracts.queues`、`spec/architecture.spec.md`（W3、R-QUEUE-ISO）、本文 **§1 task.queue** | 队列键与入队边 **足**。 |
| **`jobs` / `worker_runtime`** | **`spec/execution_plan.md` 阶段 4**、本文 **§1 PROC_WORKER**、`spec/architecture.spec.md`（M-CHAIN-WORKER、R-UC-SKIP、R-TASK-API）、**§6 DOT** | **足**；各 `*_jobs.py` 职责以 execution_plan + 任务 `title` 为准。 |
| **`service`** | 本文 **§2 Service 表**、**§4 数据流**、**`spec/execution_plan.md` 阶段 3**、**contract** 对应路径语义 | **足**；与 REST 一一对照以 contract 路径为准。 |
| **`document_enqueue_chain`** | [`ADR-document-pdf-parse-to-document-jobs.md`](../arch/ADR-document-pdf-parse-to-document-jobs.md)、本文 **§4 文献路径** | **足**（ADR 为时序真源）。 |
| **`api`** | 本文 **§5**、`spec/contract.yaml`（paths/响应码）、**`spec/execution_plan.md` 阶段 5** | **足**；具体路由方法以 OpenAPI 为准。 |
| **`api_optional`** | 本文 **§5** SSE 行、contract 若含 stream 路径 | **刻意从简**（可选能力）。 |
| **`ci_docs`** | **`spec/architecture.spec.md` §5（CI 矩阵与脚本名）**、仓库 **`scripts/`**、**`.github/workflows/`**、任务 `title`（如集成测名、`openapi-spec-validator`） | **分散但可验收**：不在本文展开每条 AG；以 **spec §5 + 实际脚本** 为执行真源。 |

**总结**：除 **`bootstrap`** 曾需在本文 **§0** 单列外，其余 layer 在 **`execution_plan` + `architecture.spec` + `contract.yaml` + 本文 §1～§6 + ADR** 中均有对应；**`ci_docs`** 不追求在 `system-architecture.md` 内逐条复述，属预期。**单条 AG 的验收细目**仍以 **任务图 `title` + 上述真源交叉检索** 为准，不要求 `architecture-task-graph.md` 正文长于 JSON。
