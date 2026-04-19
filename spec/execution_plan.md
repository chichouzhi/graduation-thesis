# 任务执行文档（初版）

> 依据：[毕设系统架构推导](.cursor/plans/毕设系统架构推导_8fd2e706.plan.md)（下称「设计文档」）。  
> 范围：后端分层交付顺序；**不写代码实现**。  
> 硬约束：**凡触达 `adapter.llm` 的路径，生产默认必须经 queue + worker**（见下文「LLM 异步全覆盖」）；**API 层不得调用 LLM**；**编排逻辑仅存在于 `use_cases`**（`task/*_jobs` 为薄封装，禁止复制 Prompt/分块规则）。  
> **HTTP/队列载荷以 `contract.yaml`（OpenAPI，`info.version`）为单一契约**；与 **`architecture.spec.md`** 分层门禁联合验收（契约不替代 import-linter）。  
> **三文档闭环**：凡 `.cursor/plans/毕设系统架构推导_*.plan.md` 与本文/契约/规格出现命名冲突（例如历史 **`pdf_jobs` 队列名**），以 **`contract.yaml`、`architecture.spec.md`、本文** 为更正真源。  
> **ADR 真源（与本文无冲突时的细化裁决）**：文献 **`pdf_parse` → `document_jobs` 入队时序** 见 **`docs/arch/ADR-document-pdf-parse-to-document-jobs.md`**；**`reconcile_jobs` 与 W4 / `use_cases`** 见 **`docs/arch/ADR-reconcile-jobs-and-w4.md`**。

---

## 核心四域 × 阶段覆盖矩阵

下列 **chat / document / topic / selection** 为毕设核心业务四域；每一阶段须能对应到交付物（无遗漏行）。

| 阶段 | chat | document | topic | selection |
|------|------|----------|-------|-----------|
| **1 `model`** | `conversations` / `messages`（占位、`delivery_status` 或 job 外键）、可选 `chat_jobs` | `document_tasks`（状态、锁、断点、`result_*`、`error_*`） | `topics` / `topic_portraits`（或等价 JSON 列）、`terms` | `applications`、`assignments`（真源）、`topics.selected_count` 派生说明 |
| **2 `use_cases`** | `chat_orchestration`（Prompt、裁剪、顺序策略挂钩） | `document_pipeline`（分块计划、stage、并行度语义） | `topic_keywords`（仅 Worker 调用的 LLM 编排入口） | **无 LLM 编排**；不涉及 `use_cases` 强求项（志愿规则留在 `service` + `model`） |
| **3 `service`** | `ChatService`：组装调用 `use_cases` → Policy → 事务占位 → 入队 | `DocumentService`：落盘、建任务行 → Policy → 入队 | `TopicService`：CRUD/审核链路、Jieba 同步写画像；**LLM 抽词仅入队 `keyword_jobs`** | `SelectionService`：志愿填报、教师决策、**与 `assignments` / 计数同事务**（§9.5-C） |
| **4 `task`** | `chat_jobs`：消费 → `use_cases` → `adapter.llm` → **状态回写** | **`pdf_parse` 队列**（**毕设 P0 生产默认必启**；实现模块 **`task/pdf_parse_jobs.py` 必交付**）+ `document_jobs`：解析/分块 LLM → **状态回写** | `keyword_jobs`：`use_cases` → LLM → **回写课题画像** | **`reconcile_jobs`（P0 必触发，见阶段 3 selection）**；Worker 消费 `ReconcileJobPayload` |
| **5 `api`** | conversations / messages / 可选 `GET /chat/jobs/{id}` | `document-tasks` | `/topics` 等 | `/applications`、`/assignments`（志愿 API **唯一归属 selection 蓝图**，§10.3） |

### Chat 同会话多 job 顺序（真源）

- **默认（毕设交付）**：同一 **`conversation_id`** 下多个 **`chat_jobs` 串行消费**（与 **`PostUserMessageRequest.seq` / `client_request_id`** 及 Worker 侧抢锁/单消费者策略一致；设计长文 §14.3 为细化参考）。**禁止** Worker 在 **`running` 超时** 后 **`running→pending` 再重入队**；超时 **仅** 落 **`failed`**，与 **`contract.yaml` → `x-task-contracts.x-watchdog-on-timeout`** 一致。
- **可选另一枝**「过期丢弃 / 乱序拒绝」若未在配置显式开启，则 **不在本仓库默认行为内**。

---

## LLM 异步全覆盖（检查清单）

凡下列路径在生产默认下 **调用 `adapter.llm`**，均须 **queue + worker**，**禁止**在 Gunicorn 默认 API worker 内同步阻塞等待整段生成（§14.8）。

| 能力 | 异步形态 | 说明 |
|------|----------|------|
| **Chat 回复** | `chat_jobs`（或等价队列名） | 受理：`service` 占位 + 入队；执行：`task/chat_jobs` → `use_cases` → LLM |
| **文献摘要 / 多段 LLM** | **`pdf_parse`（P0 默认必入队）** + `document_jobs` | 受理：`DocumentService` **仅**落盘与建任务行，**禁止**在 API 进程内做默认 PDF 全文解析；**生产默认**须 **`enqueue(pdf_parse)`** 再 **`enqueue(document_jobs)`**；**broker 队列名以 `contract.yaml` → `x-task-contracts.queues` 为准** |
| **课题 LLM 抽词** | `keyword_jobs` | 受理：`TopicService` 仅入队；执行：`task/keyword_jobs` → `use_cases` → LLM → 写画像 |
| **ProfileMatch / 推荐** | **不调 LLM** | 只读 DB + 内存打分；无队列要求 |
| **可选 SSE 流式** | 若交付仍须 **专用 worker 进程组** 承载 | 与 Nginx `proxy_read_timeout` 对齐；**不得**退回默认 API worker 同步长阻塞 |

---

## 角色分工：`service` / `use_cases` / `task`（必须区分）

| 层级 | 角色定位 | 允许做的事 | 禁止 / 不宜 |
|------|----------|------------|-------------|
| **`service`** | **业务入口（领域边界 + 事务 + 入队决策）** | 开事务、读写本域 `model`、调用 **`use_cases` 仅获取「组装结果 / 分块计划数据结构」**（不在此写第二套规则）、调用 **PolicyGateway**、调用 **`task.queue.enqueue`**、入队失败 **补偿** 更新 DB | 生产默认路径内 **直连 `adapter.llm`**；Chat/Document **阻塞等待** LLM 完成；**api** 直连本层以外的编排 |
| **`use_cases`** | **唯一编排层（跨步骤规则单点）** | Prompt 与消息列表构建、token 级裁剪、文献分块与 stage 计划、keyword 抽词编排、**规定**调用 adapter 的顺序与重试/降级 **策略参数**（与 Adapter 能力对齐） | `import` 任意 `*/api/`；依赖 Flask `request` |
| **`task`（`*_jobs`）** | **异步执行壳（队列消费 + 观测字段传递）** | 反序列化 payload、幂等守卫、调用 **`use_cases`**、在编排指引下调用 **`adapter`**、**回写状态与结果**、**错误分类** 写库 | 复制 `use_cases` 内已有编排；`import` `*/api/`；在 job 内手写一套 Prompt 规则 |

**调用关系（运行期，与设计一致）**

- **HTTP 受理**：`api` → **`service`** →（读侧/组装侧）**`use_cases`** → **PolicyGateway** → **DB 提交** → **`task.queue.enqueue`**。  
- **Worker 执行**：**`task/*_jobs`** → **`use_cases`** → **`adapter`**（含 `llm` / `pdf` 等）→ **DB / Storage 回写**。

---

## 阶段总览

| 顺序 | 阶段 | 核心产出 |
|------|------|----------|
| 1 | `model` | 四域持久化 + 异步任务载体 + 幂等/状态字段 |
| 2 | `use_cases` | Chat / Document / Topic(keyword) 编排；**selection 无强求** |
| 3 | `service` | 四域 `*Service`：事务、规则、Policy、入队与补偿 |
| 4 | `task` | 入队封装 + `chat_jobs` / **`pdf_parse`（P0）** / `document_jobs` / `keyword_jobs` / **`reconcile_jobs`（P0）** |
| 5 | `api` | 各域 Blueprint；**仅**转调 `service` |

**横向能力（贯穿各阶段）**：`common/policy`（PolicyGateway）、Redis broker、独立 Worker、**状态回写 / 错误码 / 幂等与 watchdog**（见阶段 4 子任务）。

---

## 阶段 1：`model`

### 目标

建立与设计文档 §11 一致的数据模型，使 **异步任务**、**占位消息**、**幂等与断点**、**selection 真源** 有持久化载体。

### 子任务

- **chat**：`conversations`（**须持久化 `term_id` 非空**，与 **`ChatJobPayload.term_id`**、LLM 配额命名空间一致；创建会话请求体见 **`contract.yaml` → `CreateConversationRequest`**）/ `messages`（assistant 占位；**对外 JSON 字段名见 `contract.yaml` 之 `Message.status`（`AsyncTaskStatus`）；库内列名若用 `delivery_status`，仅允许在 ORM/序列化层映射，禁止再引入 `msg_id` 等别名**）；可选 `chat_jobs`（`job_id`、重试审计、**`error_code`/`error_message`**）。**`ChatService` 组 `ChatJobPayload` 时 `term_id` 必须取自本会话行，禁止临时魔法常量。**
- **document**：`document_tasks`（**`term_id` 非空**、与 **`contract.yaml` → `DocumentTask.term_id`** 及队列 payload 一致；`status`、`locked_at`、`last_completed_chunk`、`result_json` / `result_storage_uri`、**`error_code`/`error_message`**）。
- **topic**：`topics`、`terms`、`topic_portraits`（或内嵌画像列）；与 **`term_id`** 绑定的 LLM 配置存储方案（单一真源，§10.1.1）。
- **selection**：`applications`（唯一约束：`student+term+topic`、`student+term+priority`；**HTTP 创建志愿须带 `term_id`，与 `contract.yaml` 之 `CreateApplicationRequest` 一致**）、`assignments`（**真源**）、`topics.selected_count`（派生与对账说明）。
- **索引**：§11.4 中与列表、轮询、worker 抢任务相关的索引（含 `chat_jobs` / `document_tasks` 按 `status, created_at, locked_at`）。
- **通用**：用户/画像/看板等支撑表（与四域验收相关部分不省略）。

### 验收标准

- 上表「四域 × model」四列均有对应表或字段说明。
- Chat / Document 状态字段支持契约：**pending → running → done | failed**（与 `contract.yaml` 之 `AsyncTaskStatus` 一致；库内若曾用 `success`/`completed`，迁移映射在实现清单中单列）。**志愿填报状态**使用 `contract.yaml` 之 **`ApplicationFlowStatus`**，**勿与** `AsyncTaskStatus` 混用（字符串值可能同为 `pending`，语义不同）。
- **selection**：ER 能体现 **接受志愿 → `assignments` + 派生计数** 的约束落点。
- 列表接口不依赖文献大字段行内存储（§10.6）。

---

## 阶段 2：`use_cases`

### 目标

实现 **应用用例层**：Chat / Document / Topic(LLM keyword) 的 **编排单点**；**无 HTTP 上下文**；供 **`service`（受理侧组装）** 与 **`task/*_jobs`（执行侧）** 共用。

### 子任务

- **chat — `chat_orchestration`**：从会话与历史构建 messages、系统角色与免责声明、**token 级裁剪**（§14.6）；**同会话多 job** 与 `seq` / `client_request_id` 的协作点（§14.3）；HTTP 可选字段见 **`contract.yaml` → `PostUserMessageRequest`**，**缺省时由服务端生成 `seq`（单调递增）**、`client_request_id` 可空。
- **document — `document_pipeline`**：分块计划、**`chunk_index` + `stage` 幂等键**语义、chunk **并行度上限** 的配置读取与遵守（§4.1、§9.1）。
- **topic — `topic_keywords`（或等价命名）**：课题 **文本快照** 输入 → 编排调用 LLM → 输出结构化关键词（**仅 Worker 路径调用**，§4.2）。
- **selection**：无独立 `use_cases` 模块为硬性要求；志愿与容量规则在 **`SelectionService` + 事务** 中实现，**不得** 为「凑层」把业务规则拆到 `api`。
- **横切约束**：`use_cases` **不** import `api`；不持有 Flask `request`；**错误语义**（可映射到 `error.code`）与 Adapter 返回对齐的设计说明占位。

### 验收标准

- chat / document / topic 三列在 **编排单点** 上均有模块落点；selection 在文档中明示 **不走 LLM、不强求 use_cases 文件**。
- Worker 与 `service` **共用**同一套编排函数，**无第二份** Prompt/分块实现（§13 第 4 条）。

---

## 阶段 3：`service`

### 目标

各域 **业务服务层**：**事务边界**、领域规则、**PolicyGateway**、**先写 DB 占位/任务行再提交后入队**（§9.2.1）；生产默认 **不调 `adapter.llm`**。

### 子任务

- **chat — `ChatService`**：  
  - 调 **`use_cases`** 做「受理侧所需」的组装结果（仅依赖已加载消息/会话，**不触发 LLM**）。  
  - **PolicyGateway**（Redis、队列深度、in-flight、预算粗检）。  
  - **单事务**：用户消息 + assistant 占位（`pending`）→ **提交** → **`enqueue(chat_jobs)`**。  
  - **入队失败补偿**：占位行 / `chat_jobs` → `failed`，写入 **`QUEUE_UNAVAILABLE`**（或等价），**禁止**长期悬挂 `pending`（§9.2.1）。
- **document — `DocumentService`**：类型大小校验 → **Storage** 落盘 → **`document_tasks(pending)`**（**须持久化 `term_id`**，与 **`contract.yaml` → `DocumentTask.term_id`**、**`PdfJobPayload`/`DocumentJobPayload`** 同源）→ Policy → **`commit` 成功后仅 `enqueue(pdf_parse)`**（P0，队列名以 **`contract.yaml` → `x-task-contracts.queues`** 为准）；**`document_jobs`** 须在 **`pdf_parse` worker 成功路径** 经 **`use_cases.document_pipeline`** 再 **`enqueue`**（**禁止**在 API 线程内默认同步全文解析；**细裁决**见 **`docs/arch/ADR-document-pdf-parse-to-document-jobs.md`**）；**`task_type` / `language` 未上传时的默认值与 `contract.yaml` 一致**（`summary`、`zh`）；**入队失败** 同补偿条款。
- **topic — `TopicService`**：课题 CRUD、审核状态机；画像 **唯一写入口**；Jieba **同步**；**生产默认 LLM 抽词仅 `enqueue(keyword_jobs)`**；**禁止**同步 `LLMAdapter`（§4.2）；**触发入队的写路径**（如创建/更新草稿）在 Policy 失败或入队失败时返回 **`contract.yaml` 已列之 429/503 + `error.code`**。
- **selection — `SelectionService`**：志愿填报/撤销/改优先级；从 **`terms` 只读** 读窗口；教师 **accept/reject**；**单事务** 维护 **`assignments` 真源** 与 **`topics.selected_count`**（或触发器/对账任务，与设计择一写死）；**并发下容量与 TOCTOU** 在事务/锁策略中落子（§11.2.4、§14.2 思路借鉴到同步域）。**`reconcile_jobs`（P0）**：在 **`accept` 成功且事务 `commit` 成功后**，**须** 与三域 LLM 入队一致：**先** 经 **`PolicyGateway`（或与 `task.queue.enqueue` 内对 `reconcile_jobs` 队列名执行的同等 broker/深度/Rules 检查，二者实现择一并写死）**，**再** **`enqueue(reconcile_jobs)`**（`ReconcileJobPayload`：`scope=by_term` 且 **`term_id` 与志愿同学期**）；**禁止**无任何背压检查的裸 **`enqueue(reconcile_jobs)`**；**禁止**仅依赖「将来可能写的 Cron」作为唯一触发；**staging/验收配置禁止关闭** 该入队（开发机可通过 `settings` 显式开关，默认开启）。
- **其它域**：`IdentityService`、`TermService`、`RecommendService`（**只读、无 LLM**）、`MilestoneService` 等按设计补齐。

### 验收标准

- 四域均有 **`service` 子任务** 描述；其中 **selection** 显式包含 **事务与真源** 要求。
- **Chat / Document / Topic(LLM)**：**Policy → enqueue** 齐全；HTTP **202**（Chat：`job_id` + 占位消息；Document：任务 id + `pending`）；若历史代码曾用 200，迁移以本文件与 `contract.yaml` 为准统一 **202**。
- **禁止**：`ChatService` / `DocumentService` / `TopicService` 在生产默认路径 **同步阻塞** `adapter.llm`（§14.8）。
- **入队顺序**：先 **DB 提交** 再 `enqueue`；失败可恢复、无「队列有消息但库无行」。

---

## 阶段 4：`task`（queue + worker）

### 目标

**Redis（或同类 broker）+ 独立 Worker**；**分队列 / 分 worker 组** 隔离 chat、document(pdf/llm)、keyword（§14.1）；Job **薄**，负责 **执行、回写、容错**。

### 子任务

- **基础设施**：`task/queue.py` 统一 `enqueue`；队列名、broker、**按队列维度的背压阈值** 与部署说明对齐（§14.1）。
- **chat — `task/chat_jobs.py`**：  
  - 消费 **`ChatJobPayload`**；**抢占** 时将消息或 job 标为 `running`（与契约一致）。  
  - 调用 **`use_cases` → `adapter.llm`**；**TOCTOU**：Adapter 前 **二次计量/原子扣减**，失败则 **有限重试** 后置 `failed`（§14.2）。  
  - **状态回写**：assistant `content`、`delivery_status` 或 `chat_jobs.status` 直至 **`done`/`failed`**；**降级文案** 策略与 `error_code` 落库。  
  - **watchdog（写死）**：`chat_jobs` / assistant 占位在 **`running` 且超 worker 配置阈** 时 **一律** **`failed`**（**禁止** `running→pending`；与 **`contract.yaml` → `x-task-contracts.x-watchdog-on-timeout`** 一致）。  
  - **错误处理**：厂商限流/超时映射到 **`LLM_RATE_LIMITED`** 等与 API 约定一致；**禁止**无限重试整 job。
- **document — `task/pdf_parse_jobs.py`（**P0 必交付**，消费 **`pdf_parse` 队列**）+ `document_jobs.py`**：  
  - **幂等**：以 **`document_task_id + chunk_index (+stage)`** 为键；重复消费 **跳过或安全重放**（§11.2.11）。  
  - **状态回写**：`pending` → `running` → `done`/`failed`；**断点字段** `last_completed_chunk` 更新；大结果 **指针** 写回。  
  - **并行度**：chunk 级 in-flight **≤ 配置上限**；与全站槽位叠加（§4.1）。  
  - **watchdog（写死）**：`document_tasks` / job 在 **`running` 且 `locked_at` 超阈** 时 **一律** 置 **`failed`**（**禁止** `running→pending` 重入队；与 **`contract.yaml` → `x-task-contracts.x-watchdog-on-timeout`** 一致）。  
  - **错误处理**：单 chunk 失败 **不得** 触发无限整任务风暴；**错误信息** 可聚合到任务行。
- **topic — `task/keyword_jobs.py`**：`use_cases` → LLM → **回写 `topic_portraits` / 画像列**；失败写入可观测字段；**禁止**在 job 内绕过 `use_cases` 调 LLM。
- **selection — `task/reconcile_jobs.py`（P0）**：消费 **`ReconcileJobPayload`**，对账 **`assignments` 与 `topics.selected_count`**（§9.5-C）；**触发源** 见 **阶段 3 `SelectionService`**（**accept 成功后必入队**）。**仅内部队列**；无 REST；可不使用 `AsyncTaskStatus` 持久化（与 **`contract.yaml` → `x-task-contracts`** 说明一致）。
- **进程约束**：Worker **禁止** `import` `*/api/`；回写不依赖 Flask `request`（§14.3）。
- **观测**：`request_id` / `job_id` / `document_task_id` / `conversation_id` 打点到结构化日志（§14.6）。

### 验收标准

- **所有 LLM 调用**均发生在 Worker 内且经过 **`use_cases`**（§9.3 图注）；API 进程无长阻塞。
- **状态回写 / 错误码 / 幂等 / watchdog** 在上文子任务中均有对应条目且可测试。
- 背压与队列不可用：**Policy** 与 **补偿** 行为可对照 **`architecture.spec.md`** 与 **`contract.yaml`** 验收。

---

## 阶段 5：`api`

### 目标

HTTP **接口层**：校验、鉴权、序列化、状态码；**仅**调用同域 **`service`**。

### 子任务

- **HTTP 路由与 `contract.yaml` paths 对齐**（含 **identity**：`/auth/*`、`/users/me`；**terms**：`/terms`、`/terms/{term_id}/llm-config`；**taskboard**：`/milestones`；以及 chat、document、topic、selection、`/recommendations/topics`）。**推荐接口** Blueprint 包名 **须为 `app.recommendations.api`**（与 **`architecture.spec.md` §4 import-linter 源模块列表** 一致）。设计文档 §10、§10.8 为细化参考。
- **统一错误体** `error.code`（`QUEUE_UNAVAILABLE`、`POLICY_QUEUE_DEPTH`、`LLM_RATE_LIMITED` 等）。
- **Chat POST messages**：**202** + `job_id` + user/assistant 占位。
- **Document POST**：**202** + 任务 id + `pending`（与 `contract.yaml` 一致）。
- **禁止**：`import app.adapter`、`import app.use_cases`（§8.1）。

### 验收标准

- 四域 **均有对外 HTTP 入口** 且 **仅** 触及 `service`。
- CI / import-linter 可证 **`api` 对 `adapter`/`use_cases` 零依赖**（§14.7）。
- 前端仅 HTTPS 访问 REST；不暴露 Redis/Worker 管理面（§3）。

---

## 跨阶段验收（整体验收）

- **四域**：chat / document / topic / selection 在 **model → service → api** 全链路可追溯；**LLM 仅** 经 **queue + worker + use_cases**（topic 仅 `keyword_jobs`）。
- **职责分离**：`service` 为业务入口与事务/入队；`use_cases` 为编排单点；`task` 为执行壳与回写。
- **可靠性**：入队补偿、worker 侧失败分类、幂等与 watchdog 可演示。
- **一致性**：selection 接受路径 **`assignments` / `selected_count`** 与设计 §9.5-C 一致；**`reconcile_jobs` 须在验收中演示至少一次消费**（accept 后入队）。**兜底演示**（无完整 UI 时）：运行 **`python scripts/trigger_reconcile_enqueue.py`** 打印符合 **`ReconcileJobPayload`** 的 JSON，经测试 harness / broker 控制台入队，**仅**用于验收「Worker 至少消费一次」——**不**免除阶段 3 **`accept` 成功后生产路径必 `enqueue(reconcile_jobs)`** 的义务。

---

## 交付顺序 vs 依赖方向（修正说明）

**推荐实现顺序（自底向上）**：`model` → `use_cases` → `service`（含入队调用）→ `task` 中 job 与 worker 启动脚本 → `api`。

**运行期依赖方向（不等于实现顺序）**：

```text
api  ──►  service  ──►  model、policy、task.queue（仅入队）
                         │
                         └──► use_cases（受理侧只读组装）

worker  ──►  task/*_jobs  ──►  use_cases  ──►  adapter  ──►  外部 MaaS 等
                │                │
                └────────────────┴──►  model / Storage（状态回写）
```

`task` 包中的 **queue 封装** 被 **`service` 与 worker 进程** 共用；**`api` 不依赖 worker**，仅依赖 **`service`**。
