# 规范提取（完整版）

> **文档导航**：[分类总目](../DOCUMENT-CATALOG.md) · [文档索引](../README.md) · [系统架构](../architecture/system-architecture.md) · [REST 子表](./spec-extraction-rest-paths.md) · [后台任务子表](./spec-extraction-background-tasks.md)  
> **真源**：`spec/architecture.spec.md`、`spec/contract.yaml`、`spec/execution_plan.md`。  
> **目的**：功能清单、非功能需求、边界条件、NOT IN SCOPE 的单一汇总。

---

## 1. 功能清单（按域与载体）

### 1.1 Identity（身份）

- 登录：`POST /auth/login`（Access JSON；Refresh 与 HttpOnly Cookie 与 `architecture.spec` 一致，由实现落地）。
- 刷新令牌：`POST /auth/refresh`。
- 登出：`POST /auth/logout`（作废 Refresh、清除 Cookie 与架构 spec 一致）。
- 当前用户：`GET /users/me`。
- 更新当前用户：`PATCH /users/me`（含学生/教师画像等）。

### 1.2 Terms（学期与 LLM 配置）

- 学期列表：`GET /terms`（角色可见范围由实现裁剪）。
- 新建学期：`POST /terms`（管理员）。
- 学期详情：`GET /terms/{term_id}`。
- 更新学期与选题窗口：`PATCH /terms/{term_id}`。
- 按学期 LLM 配置：`GET`、`PATCH /terms/{term_id}/llm-config`（与 `term_id` 绑定的单一真源）。

### 1.3 Taskboard（里程碑）

- 里程碑列表：`GET /milestones`（`student_id`、`from_date`/`to_date`、分页；教师查学生须校验指导关系）。
- 创建里程碑：`POST /milestones`（学生）。
- 单条里程碑：`GET`、`PATCH`、`DELETE /milestones/{milestone_id}`。

### 1.4 Chat（会话与异步回复）

- 会话列表：`GET /conversations`（当前用户、分页）。
- 新建会话：`POST /conversations`（必填 `term_id`；可选 `title`、`context_type`、`context_ref_id`）。
- 会话元数据：`GET /conversations/{conversation_id}`。
- 删除/归档会话：`DELETE /conversations/{conversation_id}`（契约标注可选实现）。
- 历史消息：`GET /conversations/{conversation_id}/messages`（分页、`order`、`after_message_id`/`before_message_id` 游标）。
- 发送用户消息：`POST /conversations/{conversation_id}/messages`（**HTTP 202**；`job_id`、`user_message`、`assistant_message`；请求 `content`，可选 `client_request_id`、`seq`）。
- 查询 Chat 异步任务：`GET /chat/jobs/{job_id}`（可选，与 `ChatJob` 对齐）。
- 可选 SSE：`GET /conversations/{conversation_id}/stream`（可选交付；专用 worker；错误为 JSON `ErrorEnvelope`）。

### 1.5 Document（文献任务）

- 上传并创建任务：`POST /document-tasks`（`multipart/form-data`；必填 `file`、`term_id`；可选 `task_type`、`language`；默认 `summary`/`zh`；**HTTP 202**）。
- 任务列表：`GET /document-tasks`（分页；列表项无大 `result`）。
- 单任务详情：`GET /document-tasks/{task_id}`（`task_id` === `document_task_id`）。

**与 REST 配套的交付能力（execution_plan / ADR）**

- 生产默认：`DocumentService` 落盘 + 建 `document_tasks` → **先 `enqueue(pdf_parse)`（P0）**，再在成功路径经编排 **`enqueue(document_jobs)`**（细则以 [`../arch/ADR-document-pdf-parse-to-document-jobs.md`](../arch/ADR-document-pdf-parse-to-document-jobs.md) 为准）。
- Worker：**`pdf_parse_jobs.py`（P0 必交付）** + **`document_jobs`**；分阶段/分块幂等、状态与断点回写。

### 1.6 Topic（课题与审核）

- 课题列表：`GET /topics`（`status`、`teacher_id`、`term_id`、`q`、分页）。
- 创建课题：`POST /topics`（草稿；**LLM 抽词走 `keyword_jobs`**；Policy 失败 **429**、入队失败 **503** 等）。
- 课题详情：`GET /topics/{topic_id}`。
- 更新课题：`PATCH /topics/{topic_id}`（可触发 `keyword_jobs`；错误码同 POST）。
- 删除/撤回：`DELETE /topics/{topic_id}`（仅允许状态内）。
- 提交审核：`POST /topics/{topic_id}/submit`。
- 管理员审核：`POST /topics/{topic_id}/review`（`approve`/`reject` + 可选 `comment`）。

**计划隐含**

- 画像写路径：**Jieba 同步** + 生产默认 **`keyword_jobs`** 调 LLM；响应可含 `llm_keyword_job_id` / `llm_keyword_job_status`。

### 1.7 Selection（志愿填报与指导关系）

- 创建志愿：`POST /applications`。
- 志愿列表：`GET /applications`。
- 撤销志愿：`DELETE /applications/{application_id}`。
- 修改志愿：`PATCH /applications/{application_id}`。
- 教师决策：`POST /applications/{application_id}/decisions`（返回 `application` 与可选 `assignment`）。
- 指导关系列表：`GET /assignments`。
- 指导关系详情：`GET /assignments/{assignment_id}`。

**计划隐含**

- `SelectionService`：**单事务**维护 **`assignments` 真源**与 **`topics.selected_count`**（或等价）；教师 **`accept` 且 `commit` 成功后 P0 须 `enqueue(reconcile_jobs)`**（经 Policy 或与 `enqueue` 同等检查，二者择一写死）。
- **`reconcile_jobs`**：仅内部队列；消费 `ReconcileJobPayload`；**无公开 REST**。

### 1.8 Recommendations（只读）

- 课题推荐：`GET /recommendations/topics`（**必填** `term_id`；`top_n`、`explain`；**不调 LLM**）。

### 1.9 横切与契约级行为

- **PolicyGateway**（或等价）：Chat / Document / Topic 入队写路径及 **`enqueue(reconcile_jobs)`** 前须通过；拒绝时 **429/503** 与 **`error.code`** 对齐契约。
- **入队与 DB**：**`commit` → `enqueue`**；`enqueue` 失败补偿 **`failed` + `QUEUE_UNAVAILABLE`**（或等价）；禁止长期悬挂 **`pending`**。
- **异步状态**：**`AsyncTaskStatus`**：`pending` → `running` → `done` | `failed`**；watchdog 超时 **仅 `failed`**，禁止 `running→pending` 再入队。
- **错误体**：**`ErrorEnvelope`**（`error.code` / `message` / 可选 `details`）。
- **队列声明**：`contract.yaml` → **`x-task-contracts.queues`** 须含 **`chat_jobs`、`pdf_parse`、`document_jobs`、`keyword_jobs`、`reconcile_jobs`**。
- **命名**：资源 ID 一律 `*_id`；禁止契约 **`forbidden_aliases`**（`msg_id`、`conv_id`、`tid`、`uid`）。

### 1.10 Worker / 编排（非 HTTP）

- **`chat_jobs`**：消费 `ChatJobPayload` → **必经 `use_cases`** → LLM → 回写；同会话顺序与真源文档/配置一致（默认串行）。
- **`keyword_jobs`**：消费 `KeywordJobPayload` → **`use_cases`** → LLM → 回写课题画像。
- **`reconcile_jobs`**：消费 `ReconcileJobPayload`；对账 **`assignments` 与 `topics.selected_count`**。

### 1.11 数据模型支撑（execution_plan 阶段 1）

- Chat：`conversations`（**`term_id` 非空**）、`messages`、可选 **`chat_jobs`**。
- Document：**`document_tasks`**（含 `term_id`、锁、断点、结果指针、错误字段）。
- Topic：`topics`、`terms`、**`topic_portraits`**（或等价）、学期绑定的 LLM 配置。
- Selection：**`applications`**（唯一约束等）、**`assignments`（真源）**、**`topics.selected_count`** 派生/对账。
- 通用：用户/画像/索引等（计划要求与四域验收相关部分不省略）。

---

## 2. 非功能需求

### 2.1 性能与响应

- Chat / Document 受理：未启动 Worker、broker 可用时，**≤800ms** 返回 **202**，且 HTTP 层无厂商 LLM 请求（`architecture.spec` §5.1）。
- Topic 触发入队写路径：规范用例要求无 LLM HTTP；入队失败 **503 + `QUEUE_UNAVAILABLE`**。

### 2.2 可用性与部署

- 生产默认：Chat、Document（多段 LLM）、默认 PDF 解析、课题 LLM 抽词须 **broker + 独立 Worker**；禁止以 **`ThreadPoolExecutor`** 作为生产默认替代队列。
- **`FLASK_ENV=production`** 缺 broker：**启动失败**，不得静默降级同步 LLM。
- 部署清单须体现 **worker** 与队列实现关键字，或 **`docs/deploy.md`** + CI 检测（**R-NO-QUEUE**）。

### 2.3 架构可机检

- 分层：`API` → `SVC` only；禁止 `API` → `adapter` / `use_cases` / `task` / ORM `models` 直连；`**_jobs` 不得 `import adapter` 或 `api`**；**`use_cases` 不得 `api`/Flask `request`**。
- **`PROC_API`** 不得同步阻塞等 LLM；**`SVC` 生产默认不得直连 `adapter.llm`**；**推荐域不得** `adapter.llm` 或在线 **`adapter.nlp`** 替代 Topic 画像写路径。
- 编排仅在 **`use_cases`**；**[`../arch/llm_entrypoints.md`](../arch/llm_entrypoints.md)** 须存在且与 PR 联动。
- CI：`import-linter`、rg-guard、`check-queue-keys`、`check-policy-deny-tests`、三域 Policy deny 集成测（禁止长期 **`pytest.skip`**）；建议 **`openapi-spec-validator`**。

### 2.4 可靠性

- **R-QUEUE-CONSIST**：先 DB 再入队；失败补偿；僵尸 **`pending`** 探针（如 **30 分钟**阈值与 spec 同步）。
- **R-CHAT-JOB-ORDER**：同会话多 job 串行或过期丢弃须在三处真源之一写死。
- **M-ADAPTER-METER（P1）**：计量/扣减；有限重试或 `failed`。

### 2.5 安全与角色

- 契约错误码含 `ROLE_FORBIDDEN`、`UNAUTHORIZED` 等；学期列表、里程碑、推荐等 **角色/关系裁剪**由实现负责。

### 2.6 可观测性

- `request_id` / `job_id` / `document_task_id` / `conversation_id` 等结构化日志（execution_plan 阶段 4）。

---

## 3. 边界条件

- 消息列表：**`after_message_id` 与 `before_message_id` 不得同请求并用**（否则 **400**）。
- Document multipart：**`term_id` 必填**；未传 **`task_type`/`language`** 默认 **`summary`/`zh`**。
- 推荐：**`term_id` query 必填**。
- **`AsyncTaskStatus`** 与 **`ApplicationFlowStatus`** 语义独立；响应 schema 须区分。
- DB 历史字段 `success`/`completed`：序列化映射为 **`done`**。
- **`Message.status`**：仅 assistant 异步必填；user/system 可为 `null`。
- Watchdog：**禁止** `running→pending` 再入队。
- 同会话「过期丢弃/乱序拒绝」：**未**在配置显式开启则 **非本仓库默认**。
- **`reconcile_jobs`**：无 REST；队列名仍须在契约声明；**禁止**仅以将来 Cron 为唯一触发。
- **`ReconcileJobPayload`**：`scope=by_term` 时 **`term_id` 必填**。
- **W3b**：本仓库默认 **关闭**；启用须 ADR + linter/CI 同步。
- SSE 未启用：**404/501** 须 JSON **`ErrorEnvelope`**。
- **`app/` 不得 import `examples/`**。

---

## 4. 禁止扩展内容（NOT IN SCOPE，规范明示）

1. **`API`**：不得依赖 **`adapter`**、**`use_cases`**、**`app.task`**、**ORM `models` 业务读写**；**`PROC_API`** 不得同步阻塞完成 LLM 再返回。
2. **`app/task`**：不得 **`import app.adapter`**；不得 **`import` 任意 `**/api/**`**。
3. **`use_cases`**：不得 **`flask.request`** 或 **`api`**；测试夹具不得在 `app/use_cases/`。
4. **生产默认**：不得以 **`ThreadPoolExecutor`** 替代 **broker + Worker** 作为 LLM/默认 PDF 主路径。
5. **`ChatService`/`DocumentService`/`TopicService`**：生产默认不得 **直连 `adapter.llm`**；**不接受** service 层 **`# arch-waiver`**；调试须在 **脚本/`examples/`**，且 **`app` 不得 import `examples`**。
6. **推荐域**：不得 **`adapter.llm`**；不得 **`adapter.nlp` 在线重推理**替代 Topic **Jieba + `keyword_jobs`** 真源。
7. **`*_jobs`**：不得复制 **`use_cases`** 级编排；单文件 **>120 行**须 **`arch-review:long-job:`**（P1）。
8. **`reconcile_jobs`**：禁止 **裸 enqueue**（无 Policy/同等检查）；禁止 **仅 Cron** 为唯一触发。
9. **Watchdog**：禁止 **`running→pending`** 再入队。
10. **同会话非串行策略**：未显式配置则 **非默认交付**。
11. **W3b**：**非**默认交付假设。
12. **SSE**：**非**强制部署能力。
13. **`DELETE /conversations/...`**：**可选**实现。
14. **`reconcile_jobs` 持久化 `AsyncTaskStatus`**：实现择一；payload **不携带** status（契约说明）。
15. **Selection**：**无**强制独立 **`use_cases` 文件**；规则 **不得**拆到 **`api`**。
16. **CI**：禁止长期 **`pytest.skip`** 占位 P0 Policy 测。
17. **命名**：禁止使用契约 **`forbidden_aliases`**。

---

## 5. 拆分文档索引

| 文件 | 内容 |
|------|------|
| [spec-extraction-rest-paths.md](./spec-extraction-rest-paths.md) | 仅 HTTP 路径与方法、要点 |
| [spec-extraction-background-tasks.md](./spec-extraction-background-tasks.md) | 队列、Worker、内部编排与数据流（无对外 REST 或跨 REST 的交付项） |
| [DOCUMENT-CATALOG.md](../DOCUMENT-CATALOG.md) | 全库文档分类总目 |
| [README.md](../README.md) | `docs/` 索引与阅读顺序 |
