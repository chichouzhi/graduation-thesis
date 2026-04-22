# 毕设交付 Todo List

> **文档**：[`docs/DOCUMENT-CATALOG.md`](docs/DOCUMENT-CATALOG.md)（**分类总目**）· [`docs/README.md`](docs/README.md)（`docs/` 索引）。与本清单互补；冲突以根目录 `contract.yaml` / `architecture.spec.md` / `execution_plan.md` 及 `docs/arch/ADR-*.md` 为准。

## Task OS：`architecture-task-graph.json` 中仍为 `ready` 的 AG

- **自动导出表**（从 JSON 生成）：[`unimplemented-ready-tasks.md`](unimplemented-ready-tasks.md)
- **刷新命令**（仓库根）：`python scripts/tasks/export_ready_tasks.py`；**默认** `--mark-done` 一次仅允许 **一个** id（与 `auto-run.py` 单条关账一致）；批量修补须 `TASKOS_BATCH_MARK_OK=1`
- **备忘勾选项**（与 JSON 真源并行维护；完成后请在图中标 `done` 并导出上表）：
  - [x] Milestones API + 服务补强（`AG-060`～`AG-061`、`AG-089a`～`AG-091`）
  - [x] Chat 可选：`GET /chat/jobs/{job_id}`、`GET .../stream` 占位（`AG-095`、`AG-107`）
  - [ ] 其余 `ready` 行见上表（CI 集成项等按队列继续）

## Data

### 身份与用户画像

- **实现** `users` 表及角色枚举（student/teacher/admin）与 ORM 映射，字段覆盖 `contract.yaml` 之 `UserSummary`/`UserMe` 所需最小集  
  - 依赖：无  
  - 优先级：P0  

- **实现** 学生画像、教师画像扩展表或 JSON 列，并与 `/users/me` PATCH 读写路径对齐  
  - 依赖：`users` 表与身份模型落地  
  - 优先级：P1  

### 学期与 LLM 配置

- **实现** `terms` 表含 `selection_start_at`/`selection_end_at`，与 `contract.yaml` 之 `Term`/`CreateTermRequest`/`PatchTermRequest` 对齐  
  - 依赖：无  
  - 优先级：P0  

- **实现** 按 `term_id` 绑定的 `LlmConfig` 持久化（独立表或 `terms` 扩展列二选一写死），并提供读取/更新服务层入口  
  - 依赖：`terms` 表落地  
  - 优先级：P0  

### Chat 域模型

- **实现** `conversations` 表强制 `term_id` 非空及索引，与 `ChatJobPayload.term_id` 同源约束  
  - 依赖：`terms` 表  
  - 优先级：P0  

- **实现** `messages` 表含 assistant 占位、`delivery_status` 或等价列，并在序列化层映射为 `Message.status`（`AsyncTaskStatus`）  
  - 依赖：`conversations` 表  
  - 优先级：P0  

- **实现** `chat_jobs` 表含 `job_id`、重试字段、`error_code`/`error_message`、时间戳索引（`status, created_at`）  
  - 依赖：`messages` 表  
  - 优先级：P0  

### Document 域模型

- **实现** `document_tasks` 表含 `term_id` 非空、`status`、`locked_at`、`last_completed_chunk`、`result_*`、`error_*`、`retry_count`  
  - 依赖：`terms` 表  
  - 优先级：P0  

### Topic 域模型

- **实现** `topics` 表及审核状态枚举（draft/pending_review/published/rejected/closed），与 `contract.yaml` 之 `Topic` 对齐  
  - 依赖：`terms` 表  
  - 优先级：P0  

- **实现** `topic_portraits` 或等价画像存储（含 `keywords`、`extracted_at`），与 `Topic.portrait` 序列化对齐  
  - 依赖：`topics` 表  
  - 优先级：P0  

### Selection 域模型

- **实现** `applications` 表及唯一约束（`student+term+topic`、`student+term+priority`），状态枚举与 `ApplicationFlowStatus` 对齐且与 `AsyncTaskStatus` 分离  
  - 依赖：`topics` 表、`users` 表  
  - 优先级：P0  

- **实现** `assignments` 真源表及与 `applications`、`topics` 的外键关系，支撑 accept/reject 事务  
  - 依赖：`applications` 表  
  - 优先级：P0  

- **实现** `topics.selected_count` 更新策略落点（触发器或服务内显式更新二选一写死）并在文档中说明  
  - 依赖：`assignments` 表  
  - 优先级：P0  

### Taskboard 域模型

- **实现** `milestones` 表及字段（`title`、`start_date`、`end_date`、`status`、`sort_order`、`is_overdue` 计算或存储策略写死）  
  - 依赖：`users` 表  
  - 优先级：P1  

### 迁移与种子

- **编写** Alembic（或等价）迁移脚本，覆盖上述表及索引，并在 CI 中执行 `upgrade head`  
  - 依赖：各表设计定稿  
  - 优先级：P0  

- **编写** 最小种子数据（管理员、学期、示例课题）用于本地与集成测试  
  - 依赖：迁移脚本可运行  
  - 优先级：P1  

---

## Backend

### 横切：Policy 与错误码

- **实现** `PolicyGateway`（或 `common.policy` 门面）接口：`assert_can_enqueue` 覆盖 Redis 连通、队列深度、in-flight、预算粗检  
  - 依赖：Redis 连接配置  
  - 优先级：P0  

- **实现** 统一 `ErrorEnvelope` 抛出/序列化辅助函数，错误码枚举与 `contract.yaml` 之 `ErrorEnvelope.error.code` 对齐  
  - 依赖：无  
  - 优先级：P0  

### 横切：队列入队门面

- **实现** `app/task/queue.py` 中各队列 `enqueue_*` 封装，队列名字面量仅使用 `contract.yaml` → `x-task-contracts.queues` 已声明键  
  - 依赖：Redis broker 客户端  
  - 优先级：P0  

- **配置** 同会话 `chat_jobs` 串行消费策略（Worker 单会话锁或等价），与 `execution_plan.md`「Chat 同会话多 job 顺序（真源）」及 `CHAT_JOB_ORDER`/`docs/arch/chat_job_order.md` 三选一真源一致  
  - 依赖：`enqueue(chat_jobs)` 实现  
  - 优先级：P0  

### Adapter：存储与 PDF

- **实现** `adapter.storage` 本地或对象存储适配：上传文献落盘、按 `document_task_id` 生成可读路径、返回 `storage_path`  
  - 依赖：无  
  - 优先级：P0  

- **实现** `adapter.pdf` 文本抽取接口（仅由 `use_cases`/`worker` 调用路径到达，不在 API 进程默认同步全文跑生产路径）  
  - 依赖：存储适配可读文件  
  - 优先级：P0  

### Adapter：LLM

- **实现** `adapter.llm` 客户端：超时、指数退避、有限重试次数 K 写死、可映射错误码（含 `LLM_RATE_LIMITED`）  
  - 依赖：环境变量中厂商密钥配置  
  - 优先级：P0  

- **实现** Adapter 调用前计量/扣减钩子及失败分支（与 `architecture.spec.md` M-ADAPTER-METER 对齐）  
  - 依赖：`adapter.llm` 基础调用  
  - 优先级：P1  

### Use Cases：Chat

- **实现** `use_cases.chat_orchestration` 中 `run_turn`（或等价命名）：历史拉取、系统提示与免责声明、`token` 级裁剪、输出 messages 供 Worker 调用 LLM  
  - 依赖：`messages`/`conversations` 读模型  
  - 优先级：P0  

- **实现** 受理侧只读组装函数（不触发 LLM）：根据已加载消息生成 `ChatJobPayload` 所需上下文摘要结构  
  - 依赖：`chat_orchestration` 公共纯函数部分抽取  
  - 优先级：P0  

- **编写** `docs/arch/llm_entrypoints.md` 登记本模块 LLM 入口函数名，与 CI `check_llm_entrypoints_doc` 规则对齐  
  - 依赖：`run_turn` 签名稳定  
  - 优先级：P0  

### Use Cases：Document

- **实现** `use_cases.document_pipeline`：分块计划、`chunk_index`+`stage` 幂等键、`max_chunks` 上限与 chunk 并行度配置读取  
  - 依赖：`document_tasks` 行模型  
  - 优先级：P0  

- **编写** `docs/arch/llm_entrypoints.md` 增补文献流水线 LLM 入口条目  
  - 依赖：`document_pipeline` 模块存在  
  - 优先级：P0  

### Use Cases：Topic 关键词

- **实现** `use_cases.topic_keywords`（或等价命名）：`text_snapshot` → 调用 `adapter.llm` → 结构化关键词结果（仅 Worker 路径调用）  
  - 依赖：`adapter.llm`  
  - 优先级：P0  

- **编写** `docs/arch/llm_entrypoints.md` 登记 keyword 编排入口  
  - 依赖：`topic_keywords` 模块存在  
  - 优先级：P0  

### Use Cases：Selection 对账

- **实现** `use_cases.selection_reconcile`（或 ADR 指定模块）：按 `ReconcileJobPayload.scope` 重算 `assignments` 与 `topics.selected_count` 一致性  
  - 依赖：`assignments`/`applications`/`topics` 模型  
  - 优先级：P0  

### Service：Identity

- **实现** `IdentityService`：`/auth/login`、`/auth/refresh`、`/auth/logout`、`GET/PATCH /users/me`，Access JSON + HttpOnly Refresh Cookie 行为与 `contract.yaml` 对齐  
  - 依赖：用户模型、JWT/会话扩展  
  - 优先级：P0  

### Service：Terms

- **实现** `TermService`：`GET/POST /terms`、`GET/PATCH /terms/{term_id}`、`GET/PATCH /terms/{term_id}/llm-config`，管理员 RBAC 校验  
  - 依赖：`terms`+`LlmConfig` 持久化  
  - 优先级：P0  

### Service：Taskboard

- **实现** `MilestoneService`：分页列表、创建、查询、更新、删除；教师按 `student_id` 查询时校验指导关系  
  - 依赖：`milestones` 表  
  - 优先级：P1  

### Service：Chat

- **实现** `ChatService.send_message`：`policy` → 单事务写入 user 消息与 assistant 占位（`pending`）→ `commit` → `enqueue(chat_jobs)`，失败补偿为 `failed`+`QUEUE_UNAVAILABLE`  
  - 依赖：`PolicyGateway`、`queue.enqueue_chat`、`use_cases` 受理侧组装  
  - 优先级：P0  

- **实现** `ChatService` 会话 CRUD：`POST/GET /conversations`、`GET/DELETE /conversations/{id}`，禁止 `import app.adapter`/`use_cases`/`task`  
  - 依赖：`Conversation` 模型  
  - 优先级：P0  

### Service：Document

- **实现** `DocumentService.create_task`：类型大小校验 → storage 落盘 → 插入 `document_tasks(pending)` → `policy` → `commit` → **仅** `enqueue(pdf_parse)`；入队失败补偿  
  - 依赖：`PolicyGateway`、`PdfJobPayload` 字段齐全  
  - 优先级：P0  

- **实现** `DocumentService` 列表与详情：`GET /document-tasks`、`GET /document-tasks/{task_id}`，列表不含大 `result` 字段  
  - 依赖：`document_tasks` 表  
  - 优先级：P0  

### Service：Topic

- **实现** `TopicService`：课题 CRUD、提交审核、管理员审核状态流转；Jieba 同步写画像字段；触发 `keyword_jobs` 的写路径走 `policy`→`commit`→`enqueue(keyword_jobs)`  
  - 依赖：`Topic` 模型、`PolicyGateway`  
  - 优先级：P0  

### Service：Selection

- **实现** `SelectionService`：志愿填报、撤销、改优先级、教师决策；事务维护 `assignments` 与 `selected_count`；`accept` 且 `commit` 成功后 `policy`→`enqueue(reconcile_jobs)`（`ReconcileJobPayload` 含同学期 `term_id`）  
  - 依赖：`applications`/`assignments` 模型、`queue.enqueue_reconcile`  
  - 优先级：P0  

### Service：Recommendations

- **实现** `RecommendService`：`GET /recommendations/topics` Top-N 只读打分（Jaccard 或既定公式），**禁止** `import app.adapter.llm` 与 `adapter.nlp` 在线重推理写库  
  - 依赖：`topics` 画像与学生画像可读  
  - 优先级：P1  

### Task：Worker 作业壳

- **实现** `task/chat_jobs.py`：消费 `ChatJobPayload` → 调 `use_cases.chat_orchestration` 预定入口 → 回写 assistant `content` 与状态至 `done`/`failed`；**禁止** `import app.adapter` 于 `task` 包（由 UC 内 import）  
  - 依赖：`run_turn` 入口、`chat_jobs` 表  
  - 优先级：P0  

- **实现** `task/pdf_parse_jobs.py`：消费 `pdf_parse` 队列、`PdfJobPayload`，抽取文本成功后按 ADR 调用 `use_cases.document_pipeline` 再 `enqueue(document_jobs)`  
  - 依赖：`adapter.pdf`、`document_pipeline`  
  - 优先级：P0  

- **实现** `task/document_jobs.py`：消费 `DocumentJobPayload`，按幂等键执行分块 LLM、更新 `last_completed_chunk`、聚合错误；watchdog 将超阈 `running` 置 `failed`（禁止 `running→pending`）  
  - 依赖：`document_pipeline`、`adapter.llm`  
  - 优先级：P0  

- **实现** `task/keyword_jobs.py`：消费 `KeywordJobPayload` → `use_cases.topic_keywords` → 回写 `topic_portraits`  
  - 依赖：`topic_keywords`  
  - 优先级：P0  

- **实现** `task/reconcile_jobs.py`：消费 `ReconcileJobPayload` → 调 `use_cases.selection_reconcile`（或 ADR 指定入口）→ 日志与对账结果写库或指标  
  - 依赖：`selection_reconcile` UC  
  - 优先级：P0  

- **配置** Worker 进程入口脚本（独立命令），与 `docker-compose.yml` 中 `worker` 服务同现  
  - 依赖：全部 `*_jobs` 注册到 worker  
  - 优先级：P0  

### API：各域路由

- **实现** `identity` Blueprint：`/auth/*`、`/users/me` 仅转调 `IdentityService`  
  - 依赖：`IdentityService`  
  - 优先级：P0  

- **实现** `terms` Blueprint：`/terms`、`/terms/{term_id}/llm-config` 仅转调 `TermService`  
  - 依赖：`TermService`  
  - 优先级：P0  

- **实现** `taskboard` Blueprint：`/milestones` 仅转调 `MilestoneService`  
  - 依赖：`MilestoneService`  
  - 优先级：P1  

- **实现** `chat` Blueprint：会话与消息、`POST .../messages` 返回 **202** 与 `PostUserMessageResponse`；可选 `GET /chat/jobs/{job_id}`；可选 SSE 路由返回 `ErrorEnvelope`（404/501）当未启用  
  - 依赖：`ChatService`  
  - 优先级：P0  

- **实现** `document` Blueprint：`POST /document-tasks` 返回 **202** 与 `DocumentTask`；multipart **必填** `term_id`；缺省 `task_type=summary`、`language=zh`  
  - 依赖：`DocumentService`  
  - 优先级：P0  

- **实现** `topic` Blueprint：`/topics` CRUD、submit、review，状态码与 `contract.yaml` 对齐  
  - 依赖：`TopicService`  
  - 优先级：P0  

- **实现** `selection` Blueprint：`/applications`、`/applications/{id}`、`/applications/{id}/decisions`、`/assignments`，**唯一**志愿 HTTP 归属  
  - 依赖：`SelectionService`  
  - 优先级：P0  

- **实现** `app.recommendations.api` Blueprint：`GET /recommendations/topics` 查询参数 `term_id` 必填、`explain` 布尔  
  - 依赖：`RecommendService`  
  - 优先级：P1  

- **注册** 所有 Blueprint 到 Flask 应用工厂，URL 前缀 `/api/v1` 与 `contract.yaml` servers 一致  
  - 依赖：各域 Blueprint 完成  
  - 优先级：P0  

---

## Frontend

### 认证与全局状态

- **实现** 登录页调用 `POST /auth/login`，保存 Access Token，处理 Refresh Cookie 与 401 刷新流程  
  - 依赖：后端 `identity` API 可用  
  - 优先级：P0  

- **实现** Axios（或 fetch）拦截器：自动附带 `Authorization: Bearer`、统一解析 `ErrorEnvelope`  
  - 依赖：登录流程  
  - 优先级：P0  

### 学生：推荐与志愿

- **实现** 课题列表页：调用 `GET /topics` 与 `GET /recommendations/topics?term_id=...`，展示 `RecommendationTopicItem.score` 与可选 `explain`  
  - 依赖：后端 topic、recommendations API  
  - 优先级：P1  

- **实现** 志愿填报页：`POST /applications`、`DELETE` 撤销、`PATCH` 改优先级，展示 `ApplicationFlowStatus`  
  - 依赖：后端 selection API  
  - 优先级：P0  

### 学生与教师：Chat

- **实现** 对话页：`POST .../messages` 处理 **202**，轮询 `GET .../messages` 或 `GET /chat/jobs/{job_id}` 直到 assistant `status` 为 `done`/`failed`  
  - 依赖：后端 chat API  
  - 优先级：P0  

### 学生与教师：文献任务

- **实现** 上传页：multipart 上传含 `term_id`，处理 **202**，轮询 `GET /document-tasks/{task_id}` 展示 `AsyncTaskStatus` 与结果预览  
  - 依赖：后端 document API  
  - 优先级：P0  

### 教师：课题编辑

- **实现** 课题表单：`POST/PATCH /topics`，展示 `llm_keyword_job_status` 与画像字段；错误处理 **429/503** 码文案  
  - 依赖：后端 topic API  
  - 优先级：P0  

### 教师与管理员：审核与学期

- **实现** 管理员审核页：`POST /topics/{id}/review`  
  - 依赖：后端 topic API  
  - 优先级：P0  

- **实现** 学期与 LLM 配置管理页：`/terms` 与 `/terms/{id}/llm-config`  
  - 依赖：后端 terms API  
  - 优先级：P1  

### 看板

- **实现** 学生里程碑编辑与图表视图：调用 `/milestones` CRUD  
  - 依赖：后端 taskboard API  
  - 优先级：P2  

---

## Infra

### 容器与编排

- **配置** `docker-compose.yml`：声明 `web`、`worker`、`redis`（及 `db`）服务，**同文件**出现 `worker` 与 `chat_jobs` 或 `rq`/`celery` 等消费命令关键字  
  - 依赖：Worker 启动命令确定  
  - 优先级：P0  

- **配置** 生产环境变量：`FLASK_ENV=production` 时缺 broker **启动失败**，禁止静默降级同步 LLM  
  - 依赖：`config.py` 分支  
  - 优先级：P0  

### 反向代理（可选交付）

- **编写** `deploy/nginx.conf` 片段：`client_max_body_size`、`proxy_read_timeout` 与 Gunicorn 超时一致说明  
  - 依赖：无  
  - 优先级：P2  

---

## DevOps

### CI 门禁

- **配置** CI 工作流运行 `lint-imports`（含 `architecture.spec.md` §4 全部合约）  
  - 依赖：`.importlinter` 或 `pyproject` 合约完整  
  - 优先级：P0  

- **编写** 或接入脚本：`rg-guard-api-task`、`rg-guard-task-adapter`、`rg-guard-api-model`、`rg-guard-svc-llm`、`rg-guard-uc-flask`、`rg-guard-svc-uc-signals`、`rg-guard-jobs-biz`、`rg-guard-app-examples`  
  - 依赖：无  
  - 优先级：P0  

- **实现** `scripts/ci/check_queue_contract_keys.py`：解析 `contract.yaml` 断言队列键集含 `chat_jobs`、`document_jobs`、`pdf_parse`、`keyword_jobs`、`reconcile_jobs`  
  - 依赖：`contract.yaml` 稳定  
  - 优先级：P0  

- **实现** `scripts/ci/check_api_packages_in_linter.py`：磁盘 `app/*/api` ⊆ import-linter `source_modules`  
  - 依赖：§4 合约列表  
  - 优先级：P0  

- **实现** `scripts/ci/check_policy_deny_tests.py`：校验三测存在且无裸 `pytest.skip`  
  - 依赖：对应测试文件路径约定  
  - 优先级：P0  

- **实现** `scripts/ci/check_llm_entrypoints_doc.py` 及 `--with-diff` 主分支模式  
  - 依赖：`docs/arch/llm_entrypoints.md`  
  - 优先级：P0  

- **接入** `openapi-spec-validator`（或等价）校验 `contract.yaml` 于 CI  
  - 依赖：无  
  - 优先级：P1  

### 集成测试

- **编写** `it-async-chat`：无 worker、broker 可用时 `POST .../messages` **≤800ms** 返回 **202** 且无厂商 LLM HTTP  
  - 依赖：Flask 测试客户端、Chat 路由  
  - 优先级：P0  

- **编写** `it-async-document`：`POST /document-tasks` **202**；缺 `term_id` **400**  
  - 依赖：document 路由  
  - 优先级：P0  

- **编写** `it-topic-enqueue-errors`：Topic 写路径 mock `enqueue` 抛错 → **503** + `QUEUE_UNAVAILABLE`  
  - 依赖：`TopicService`  
  - 优先级：P0  

- **编写** `it-enqueue-order`：断言 `db.session.commit` 先于 `enqueue`；`enqueue` 失败 DB 补偿  
  - 依赖：可 spy 的 session/queue  
  - 优先级：P0  

- **编写** `it-policy-deny-chat`、`it-policy-deny-document`、`it-policy-deny-topic`：Policy mock 拒绝 → **429 或 503** 且 enqueue 零调用  
  - 依赖：`PolicyGateway` 注入点  
  - 优先级：P0  

- **编写** `it-uc-skip-chain`：mock 消费 `chat_jobs`/`document_jobs` 断言调用 `app.use_cases` 预定入口  
  - 依赖：job handler 可导入  
  - 优先级：P0  

- **编写** `it-adapter-meter`：mock 计量失败 → job `failed` 或重试次数 ≤K  
  - 依赖：`adapter` 钩子  
  - 优先级：P1  

### 验收辅助

- **编写** `scripts/trigger_reconcile_enqueue.py`：打印符合 `ReconcileJobPayload` 的 JSON 供手工入队演示（不替代 Selection 生产路径）  
  - 依赖：`ReconcileJobPayload` 定义  
  - 优先级：P2  
