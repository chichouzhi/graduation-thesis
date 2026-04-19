# 规范提取 — 后台任务与队列子表

> **文档导航**：[分类总目](../DOCUMENT-CATALOG.md) · [文档索引](../README.md) · [规范提取（完整）](./spec-extraction-full.md) · [REST 子表](./spec-extraction-rest-paths.md) · [系统架构](../architecture/system-architecture.md)  
> **真源**：`spec/contract.yaml`（`x-task-contracts`、各 `*Payload`）、`spec/execution_plan.md`、`spec/architecture.spec.md`。  
> **不含**对外 REST 路径表（见 [spec-extraction-rest-paths.md](./spec-extraction-rest-paths.md)）。完整上下文见 [spec-extraction-full.md](./spec-extraction-full.md)。

---

## 1. 契约声明的队列（`x-task-contracts.queues`）

| 队列键 | Payload schema（契约组件） | 消费方 / 备注 |
|--------|---------------------------|---------------|
| `chat_jobs` | `ChatJobPayload` | `task/chat_jobs` → **`use_cases`** → `adapter.llm`；HTTP 受理 **202** |
| `pdf_parse` | `PdfJobPayload` | **`task/pdf_parse_jobs.py`（P0 必交付）**；生产默认 **必入队**；无 chunk_index |
| `document_jobs` | `DocumentJobPayload` | `task/document_jobs`；分块/阶段；在 `pdf_parse` 成功路径再入队（ADR 细则） |
| `keyword_jobs` | `KeywordJobPayload` | `task/keyword_jobs` → **`use_cases`** → LLM → 回写课题画像 |
| `reconcile_jobs` | `ReconcileJobPayload` | **无公开 REST**；`SelectionService` **accept 且 commit 成功后 P0 入队**；对账 `assignments` 与 `topics.selected_count` |

---

## 2. 载荷必填字段摘要（实现/测试对齐用）

### `ChatJobPayload`

`job_id`, `conversation_id`, `user_message_id`, `assistant_message_id`, `term_id`, `user_id`；可选 `client_request_id`, `seq`, `request_id`, `dispatch_attempt`。

### `PdfJobPayload`

`document_task_id`, `user_id`, `storage_path`, `term_id`；`stage` 默认 `pdf_extract`。

### `DocumentJobPayload`

`document_task_id`, `user_id`, `storage_path`, `term_id`；`task_type`（summary/conclusions/compare）、`language`（zh/en）、`chunk_index`、`stage`（extract / summarize_chunk / aggregate / finalize）等。

### `KeywordJobPayload`

`keyword_job_id`, `topic_id`, `term_id`, `text_snapshot`, `requested_by_user_id`；可选 `request_id`, `retry_count`, `max_attempts`。

### `ReconcileJobPayload`

`reconcile_job_id`, `scope`（`by_term` | `full_table`）；`scope=by_term` 时 **`term_id` 必填**；可选 `request_id`。

---

## 3. 异步状态机（契约扩展）

- **状态**：`pending` → `running` → `done` | `failed`（**`AsyncTaskStatus`**）。
- **`x-watchdog-on-timeout`**：`running` 超时 **仅** → **`failed`**；**禁止** `running→pending` 再入队。
- **`pending` → `failed`**：`enqueue_failed_compensation` 触发（契约 `state_machines`）。
- **`reconcile_jobs`**：可不使用 **`AsyncTaskStatus`** 持久化（实现择一写死）。

---

## 4. 服务层与 Worker 行为（execution_plan / architecture）

### 4.1 入队与 Policy

- **顺序**：**Policy**（或同等）→ **`db.session.commit()`** → **`enqueue`**（**M-POLICY-ENQUEUE**）。
- **Chat**：用户消息 + assistant 占位（`pending`）→ 提交 → **`enqueue(chat_jobs)`**；失败补偿 **`failed` + `QUEUE_UNAVAILABLE`**。
- **Document**：落盘 + `document_tasks(pending)` → Policy → **commit 后 `enqueue(pdf_parse)`（P0）**；**`document_jobs`** 在 **`pdf_parse` 成功路径** 经 **`use_cases.document_pipeline`** 再入队。
- **Topic**：Jieba **同步**；生产默认 **仅 `enqueue(keyword_jobs)`** 调 LLM；禁止 **`TopicService` 同步 `LLMAdapter`**。
- **Selection**：**`accept` 成功 commit 后**须 **`enqueue(reconcile_jobs)`**（前经 Policy 或与 enqueue 同等 broker/深度检查，**二者择一写死**）；禁止裸 enqueue；禁止 **仅 Cron** 为唯一触发。

### 4.2 Worker 约束

- **路径**：`**_jobs` → `use_cases` → `adapter`**；**`app/task` 不得 `import app.adapter`**。
- **`*_jobs`**：薄封装（校验、调用 UC、状态回写、错误映射）；**不得**复制 Prompt/分块/重试决策等编排。
- **禁止**：Worker **`import */api/**`**；不得无限重试整 job。

### 4.3 横切

- **同 `conversation_id` 多 `chat_jobs`**：默认 **串行消费**（真源见 `docs/arch/chat_job_order.md`（若存在）、`app/config.py` 或 `spec/execution_plan.md` 固定小节）。
- **Topic 画像真源**：**Jieba + `keyword_jobs`**；**推荐域不得**用 LLM/NLP 在线重推理替代。
- **观测**：`request_id` / `job_id` / `document_task_id` / `conversation_id` 等结构化日志。

---

## 5. 与 REST 的对应关系（便于联调）

| 用户动作（REST） | 典型后台队列 |
|------------------|--------------|
| `POST .../messages` | `chat_jobs` |
| `POST /document-tasks` | `pdf_parse` →（成功路径）`document_jobs` |
| `POST`/`PATCH /topics`（触发抽词写路径） | `keyword_jobs` |
| `POST .../decisions`（accept） | **`reconcile_jobs`（P0，无 REST）** |
| `GET /recommendations/topics` | **无队列**（同步只读） |
