# 架构约束规格（可自动检测版）

> 依据：[毕设系统架构推导](.cursor/plans/毕设系统架构推导_8fd2e706.plan.md)。  
> 目标：为 **import-linter**、**静态 grep**、**调用链分析（可选）**、**集成测试** 提供 **可机器执行** 的条文；每条规则含 **描述 / 违规示例 / 检测方式**。

### 与 `contract.yaml`、`execution_plan.md` 的联动（非替代）

| 文档 | 与本 spec 的关系 |
|------|------------------|
| **`contract.yaml`** | 约定 **HTTP 状态码与 JSON 形状**（如 Chat/Document 受理 **202**、`AsyncTaskStatus`、`term_id`、Policy 失败 **429/503** 与 `error.code`）；**不能**替代本文的 **import 分层** 与 **`PROC_API` 不调 LLM** 检测。 |
| **`execution_plan.md`** | 交付顺序与四域矩阵；**P0 禁止/必须** 以本文 **§2～§8** 为最高优先级。 |
| **`docs/arch/ADR-*.md`** | 对 **`execution_plan` / 契约** 的歧义作 **裁决真源**；当前见 **`ADR-document-pdf-parse-to-document-jobs.md`**（文献双队列时序）、**`ADR-reconcile-jobs-and-w4.md`**（`reconcile_jobs` 与 **W4**）。 |

**建议 CI 增补**：`openapi-spec-validator`（或等价）校验 `contract.yaml`；集成测试将 **契约 202/429/503** 与 **R-SYNC-LLM**、**M-POLICY-ENQUEUE**、**R-QUEUE-CONSIST** 同流水线执行。`import-linter` 的 `source_modules` 须覆盖 **全部** `app.*.api` 包（含 **identity、terms、taskboard** 等，见仓库实际路径）。另见 **§5**：`rg-guard-app-examples`、`check-api-packages-in-linter`、`check-policy-deny-tests`。

---

## 0. 路径与符号约定（检测前配置）

以下 glob 以仓库根下 `app/` 为例；若目录不同，在 CI 中单点替换变量 `APP_PKG=app`。

| 符号 | Glob / 说明 |
|------|-------------|
| **`API`** | `app/**/api/**/*.py` |
| **`SVC`** | `app/**/service/**/*.py` |
| **`UC`** | `app/use_cases/**/*.py` |
| **`TASK`** | `app/task/**/*.py`（含 `queue.py`、`*_jobs.py`） |
| **`ADAPTER`** | `app/adapter/**/*.py` |
| **`LLM`** | `app/adapter/llm/**/*.py` 及 `adapter.llm` 包内公开入口（按实现调整子路径） |

**进程标签（用于语义测试，非文件路径）**

| 标签 | 含义 |
|------|------|
| **`PROC_API`** | 运行 Flask/Gunicorn **API worker** 的进程（执行 HTTP 请求路径） |
| **`PROC_WORKER`** | 消费 **Redis 队列** 的 **独立 Worker** 进程 |

---

## 1. 分层调用白名单（ALLOWLIST）

本节定义 **允许** 的跨层依赖与调用意图；**未列出的跨层依赖默认需人工豁免或判违规**（除 `common`、`extensions`、`model` 等下方说明）。**可机器验收**的跨层边界以 **§2～§3** 中带「检测方式」的规则、**§4 import-linter**、**§5 CI 表**、**§7～§8** 中带检测条目的规则为准；本节其余句为 **架构意图**，不单独作为 CI fail 依据。

### 1.1 依赖边（import / 调用关系）

| # | 允许边 | 含义 | 收紧条件（建议写进 lint） |
|---|--------|------|---------------------------|
| W1 | **`API` → `SVC`** ✅ | HTTP 仅转调同域 `service` | `API` **不得** import `TASK`、`ADAPTER`、`UC`（见 **R-API-TASK**、禁止规则） |
| W2 | **`SVC` → `UC`** ✅ | 业务入口调用编排（组装、计划、执行前准备） | 仅 **函数调用**；`SVC` **不得** 复制 `UC` 内 Prompt/分块代码；**检测**：**R-UC-ONLY** ② + **W2-DUP** |
| W3 | **`SVC` → `TASK`（仅 `queue` 门面）** ✅ | 入队由事务提交后的 **enqueue** 完成 | **推荐**：仅允许 `from app.task import queue` 或 `from app.task.queue import enqueue_*`；**禁止** `SVC` import `app.task.chat_jobs` 等 `*_jobs` 模块 |
| W3b | **`UC` → `TASK`（可选）** ✅ | 若团队将「入队」下沉为纯函数门面 | **仅**允许 `app/task/queue.py`（或与 `queue` 同级的 `enqueue` 模块）；**禁止** `UC` import 任意 `*_jobs.py` |
| W4 | **`TASK/*_jobs` → `UC`** ✅ | Worker 消费路径先进入编排 | 每个 job 文件 **必须** 存在对 `app.use_cases` 的调用（可由 grep/审计脚本检查） |
| W5 | **`UC` → `ADAPTER`** ✅ | 编排末端调 NLP/PDF/Storage/**LLM** | **`UC` → `LLM`** 须在 **Worker 进程调用栈** 中到达（见 **R-SYNC**、集成测试）；**禁止**在 **`PROC_API`** 栈内触发 |
| W6 | **`TASK` → `app.adapter`** ❌ | **显式禁止边**（**非**允许项；与 **R-UC-SKIP** 同义） | **`app/task` 包内任意模块**（含 `*_jobs.py`、`queue.py`）**不得** `import` **`app.adapter`**；凡 `adapter`（`llm`/`pdf`/`nlp`/`storage`）**仅**能由 **`UC`** 模块 import；**检测**：§4 **`forbidden_task_adapter`** + §5 **`rg-guard-task-adapter`** |

**说明**：**W1～W5、W3b** 为允许边；**W6** 为 **显式禁止边**，与表题「白名单」并列展示仅为 **编号对照**，检测以 **§2 R-UC-SKIP** 与 **import-linter forbidden** 为准。

**W3b 默认**：本仓库毕设交付 **默认关闭 W3b**（仅 **W3** `SVC` → `app.task.queue`）。若启用 **W3b**，须 **`docs/arch/ADR-W3b-uc-enqueue.md`** 评审结论、**import-linter** 与 CI 开关 **同步写死**，禁止「代码已用 UC 入队、文档仍写仅 SVC」的漂移。

### 1.2 与用户表述的对照表

| 你的表述 | 本 spec 落点 |
|----------|--------------|
| `api → service` ✅ | **W1**：`API` → `SVC` |
| `service → use_cases` ✅ | **W2**：`SVC` → `UC` |
| `use_cases → task` ✅ | **W3b**（可选）：`UC` → `task/queue` **仅**；若实现选择 **仅** `SVC` 入队，则在 CI 关闭 W3b、保留 **W3** |
| `task/*_jobs → use_cases → adapter.*` ✅ | **唯一合法**链路；**`app/task` 直连 `app.adapter`（任意子包）** 属 **R-UC-SKIP** / **W6** |
| `api → adapter` ❌ | **R-API-LLM**、**R-API-ADAPTER** |

### 1.3 允许全员引用的「基础设施」（不视为跨层违规）

以下模块 **各层均可 import**（除非另有规则禁止）：`app/common/**`、`app/extensions.py`、`app/config.py`、各域 `model`、第三方库。

---

## 2. 禁止规则（DENY）：描述 + 违规示例 + 检测方式

严重级别：**P0** 阻断合并；**P1** 警告或里程碑前清零。

---

### R-API-ADAPTER（P0）— `API` 不得依赖 `ADAPTER`

| 字段 | 内容 |
|------|------|
| **规则描述** | `API` 层模块 **不得** `import` `app.adapter` 及其子包（含 `llm`、`pdf`、`nlp`、`storage`）。HTTP 边界不得触碰外部集成。 |
| **违规示例** | `app/chat/api/routes.py` 内写 `from app.adapter.llm import ErnieClient` 或 `import app.adapter as adp`。 |
| **检测方式** | ① **import-linter** 合约：`forbidden_import` 源 `app.**.*.api` → 目标 `app.adapter`；② **ripgrep**：`rg "from app\\.adapter|import app\\.adapter" app/ -g"**/api/**/*.py"` 命中即失败。 |

---

### R-API-LLM（P0）— `API` 不得调用 `adapter.llm`（含间接）

| 字段 | 内容 |
|------|------|
| **规则描述** | 任意 **`PROC_API`** 请求处理代码路径上，**不得** 调用大模型完成接口（含 `complete`、`chat`、`invoke` 等封装名，以 `adapter/llm` 对外 API 为准）；**含** `SVC` **经** `UC` **间接** 在 **同一请求线程** 内触发 LLM（**亦禁**，与 **R-SYNC-LLM** 叠加）。 |
| **违规示例** | 路由里 `get_llm_client().chat(...)`；`from app.use_cases import x` 再在 `api` 调 `x` 且该函数内部调 LLM（**双重违规**：`api→uc` 亦禁）。 |
| **检测方式** | ① **R-API-ADAPTER** + **R-API-UC**（静态）；② **§5.1 最小集成用例**（**必跑**，语义兜底，含动态 import 无法静态拦的路径）；③ **AST 关键字列表**（**非门禁**，仅 PR 辅助，误报由维护者忽略）。 |

---

### R-API-UC（P0）— `API` 不得 import `use_cases`

| 字段 | 内容 |
|------|------|
| **规则描述** | `API` **不得** `import app.use_cases`；编排入口必须在 **`SVC`**。 |
| **违规示例** | `routes.py`：`from app.use_cases.chat_orchestration import build_messages`。 |
| **检测方式** | **import-linter** 禁止 `app.**.*.api` → `app.use_cases`；**rg** `from app\\.use_cases|import app\\.use_cases` 于 `**/api/**/*.py`。 |

---

### R-API-TASK（P0）— `API` 不得 import `app.task`（含 `queue` / `*_jobs`）

| 字段 | 内容 |
|------|------|
| **规则描述** | `API` **不得** `import app.task` 及其子模块；**入队** 仅允许经 **`SVC` → `task.queue`**（与 **W1**、**W3** 一致），禁止路由层 **绕过 `service` 直接 `enqueue`**。 |
| **违规示例** | `routes.py`：`from app.task.queue import enqueue_chat_job`。 |
| **检测方式** | ① **import-linter**：**§4 `forbidden_api_task`**；② **`rg-guard-api-task`**：`rg "from app\\.task\\b|import app\\.task\\b" app/ -g "**/api/**/*.py"` —— **零命中**。 |

---

### R-API-MODEL（P0）— `API` 不得直连 ORM 模型包（须经 `SVC`）

| 字段 | 内容 |
|------|------|
| **规则描述** | `API` **不得** `import` **`app.<domain>.models`**、**`app.models`** 等 **ORM 实体包** 以执行业务读写；持久化入口须在 **`SVC`**。 |
| **违规示例** | `routes.py`：`from app.chat.models import Message` 后 `db.session.add(...)`。 |
| **检测方式** | **`rg-guard-api-model`**：`rg "from app\\.\\w+\\.models import|import app\\.\\w+\\.models|from app\\.models import|import app\\.models" app/ -g "**/api/**/*.py"` —— **零命中**。 |

---

### R-APP-EXAMPLES（P0）— `app/` 不得 import `examples/`

| 字段 | 内容 |
|------|------|
| **规则描述** | 生产包 **`app/**`** **不得** `import` **`examples`**（演示脚本与 API 分层隔离）。 |
| **违规示例** | `from examples.chat_demo import ...` 出现在 `app/chat/service/foo.py`。 |
| **检测方式** | **`rg-guard-app-examples`**：`python scripts/ci/rg_guard_app_examples.py`（无 `app/` 时 **SKIP**；有 `app/` 时 **零命中**）。 |

---

### R-SYNC-LLM（P0）— 禁止在 `PROC_API` 同步阻塞调用 LLM

| 字段 | 内容 |
|------|------|
| **规则描述** | **Chat / Document / Topic-LLM** 的生产默认路径：**禁止**在 API worker 内 **同步等待** LLM 整段生成结束后再返回 HTTP（**无论** import、`UC` 中转或动态加载如何绕）。 |
| **违规示例** | `ChatService.send_message` 内直接 `llm.complete(...)` 并 `return 200`；`DocumentService` 在上传请求线程内 `for chunk in chunks: llm.summarize(...)` 全跑完再响应；`ChatService` 调 `use_cases.run_turn_sync(...)` 内调 LLM。 |
| **检测方式** | ① **§5.1 最小集成用例**（**P0 门禁**）：未启动 Worker、broker 可用时 **Chat POST**、**Document POST** 须在 **≤800ms** 返回 **202**，且 **无** 对厂商 LLM 端点的 HTTP（`httpx`/`responses`/`pytest-httpserver` 等断言）；② **`rg` 启发式（P1 告警，非唯一依据）**：`complete\(|\.chat\(|invoke\(` 出现在 `app/**/service/**/*.py` 且同文件 **无** `enqueue` 子串时 **CI warn** 或 **fail**（由仓库 `pyproject`/`Makefile` 择一写死）。 |

---

### R-TASK-BIZ（P0）— `TASK/*_jobs` 不得包含业务编排逻辑

| 字段 | 内容 |
|------|------|
| **规则描述** | `*_jobs.py` **仅** 做：payload 校验/观测字段、调用 **`UC`**、**状态回写**、错误映射；**不得** 内含 Prompt 模板字符串、分块算法、上下文裁剪、重试策略决策等 **与 `UC` 重复** 的编排。 |
| **违规示例** | `chat_jobs.py` 内 50 行 `messages = [{"role":"system","content":"你是…"}]` + 自行拼 user；`document_jobs.py` 内重复计算 chunk 大小与 `UC` 不一致。 |
| **检测方式** | ① **`rg-guard-jobs-biz`（P0）**：在 `app/task/` 下对所有 `*_jobs*.py` 执行 **`rg "PROMPT_|CHUNK_SIZE" <file>`** 与 **`rg 'role"\\s*:\\s*"system"' <file>`**（PowerShell/bash 按 shell 转义调整）——均须 **零命中**；② **行数门禁（P1）**：单 `*_jobs.py` **>120 行** → CI fail，除非 PR 描述含 **`arch-review:long-job:`** 理由；③ **字符串重复扫描（P2）**：`UC`/`TASK` 相同 **≥64 字符** 常量块 → fail（可选脚本）。 |

---

### R-UC-SKIP（P0）— 禁止 `TASK` 包跳过 `UC` 直连 `app.adapter`

| 字段 | 内容 |
|------|------|
| **规则描述** | Chat / Document / Keyword 的 **主生成路径** 必须经过 **`UC`** 再进入 **`app.adapter`**（含 **`llm`/`pdf`/`nlp`/`storage`**）；**`app/task` 下任意模块** **不得** `import` **`app.adapter`**（**`queue.py` 同约束**）。 |
| **违规示例** | `chat_jobs.py`：`from app.adapter.llm import client`；`document_jobs.py`：`from app.adapter.pdf import ...`。 |
| **检测方式** | ① **import-linter**：**§4 `forbidden_task_adapter`**（`app.task` → `app.adapter`，**无豁免**）；② **`rg-guard-task-adapter`**：`rg "from app\\.adapter|import app\\.adapter" app/task -g "**/*.py"` —— **零命中**；③ **编排必经 `UC`**：见 **M-CHAIN-WORKER** ②③。 |

---

### R-NO-QUEUE（P0）— LLM 主路径必须使用 **queue + worker**

| 字段 | 内容 |
|------|------|
| **规则描述** | Chat、Document（多段 LLM）、课题 LLM 抽词：**必须** `enqueue` → **独立 `PROC_WORKER`** 消费；**禁止**「仅进程内 `ThreadPoolExecutor`」作为 **生产默认**（设计 §7.4）。 |
| **违规示例** | 生产配置下 `if not redis: run_llm_in_thread_same_process()` 且为默认分支；无 Redis 时静默同步调 LLM。 |
| **检测方式** | ① **集成/E2E**：生产类 `config` 下启动应用，断言存在 **broker URL** 且 Chat/Document **enqueue** 被调用（`spy` on `enqueue`）；② **环境门禁**：`FLASK_ENV=production` 时若缺 broker **启动失败** 而非降级同步 LLM；③ **部署清单（P0）**：仓库根 **`docker-compose.yml`** / **`compose.yaml`** / **`Procfile`** 须 **`rg`** 到 **`worker`** 与 **`chat_jobs`|`rq`|`celery`** **同文件共现**；若无 compose，须在 **`docs/deploy.md`** 描述 **systemd** 等 worker 启动且 **CI** 对该文件 **`rg`** 上述关键字 —— **未命中则 fail**（禁止仅以口头评审替代）。 |

---

### R-UC-ONLY（P0）— `use_cases` 是唯一编排层

| 字段 | 内容 |
|------|------|
| **规则描述** | Prompt 组装、历史裁剪、文献分块与 stage 计划、keyword 抽词流程、LLM 调用 **顺序与分支** 仅存在于 **`UC`**；`**SVC`** 与 **`*_jobs`** 不得维护第二套编排。 |
| **违规示例** | `topic_service.py` 内自建 `def _llm_extract_keywords(text): ...` 与 `use_cases/topic_keywords.py` 并存且逻辑分叉。 |
| **检测方式** | ① **R-TASK-BIZ** + **W2-DUP**；② **`rg-guard-svc-uc-signals`**：`rg "system_prompt|messages\\s*=\\s*\\[" app/ -g "**/service/**/*.py"` —— **命中→CI fail**，修复：删除或迁至 **`app/use_cases/`**；③ **LLM 编排唯一入口表（P0）**：**`docs/arch/llm_entrypoints.md` 必须存在且非空**（见 **`check-llm-entrypoints-doc`**）；**CI** 在 `git diff` 触及 **`app/use_cases/**`** 时 **必须** 同时出现该文档的 diff（**`git diff --name-only` 双列校验**，可用 `scripts/ci/check_llm_entrypoints_doc.py --with-diff` 扩展）。 |

---

### R-SVC-LLM（P0）— `SVC` 生产默认不得同步调用 `adapter.llm`

| 字段 | 内容 |
|------|------|
| **规则描述** | `ChatService` / `DocumentService` / `TopicService`：**禁止**在生产默认路径 **直连** `LLMAdapter` 完成生成；Topic 抽词须 **`keyword_jobs`**。 |
| **违规示例** | `TopicService.on_save`：`LLMClient().extract_keywords(...)` 同步返回。 |
| **检测方式** | ① **`rg-guard-svc-llm`**：`rg "adapter\\.llm|from app\\.adapter.*llm" app/ -g "**/service/**/*.py"` —— **零命中**；**扫描范围** **不含** `app/**/tests/**`、`**/conftest.py`；② **与 R-SYNC-LLM** 同一套 **§5.1** 集成用例；③ **禁止** 以 `# arch-waiver` **绕过** ①：本仓库 **不接受** `service` 层对 `adapter.llm` 的 waiver（调试须在 **独立脚本** 或 **`examples/`**，**不得** 位于 `app/**/service/**`）。 |

---

### R-REC-LLM（P0）— 推荐域不得调用 LLM

| 字段 | 内容 |
|------|------|
| **规则描述** | `ProfileMatch` / `RecommendService`：**不得** `adapter.llm`；**不得** 使用 **`adapter.nlp`** 等 **在线重推理** 替代 **Topic 画像写路径**（Topic 侧 **Jieba 同步 + `keyword_jobs` LLM** 仍为真源）。 |
| **违规示例** | `recommend_service.py`：`from app.adapter.llm import ...`；`from app.adapter.nlp import extract_keywords` 对全库跑抽词写回。 |
| **检测方式** | ① **import-linter**（`app.recommendations.api` 已列入 **§4**）；② **`rg`** 于 `app/recommendations/**`：`adapter\.llm|from app\.adapter.*llm|from app\.adapter.*nlp|import app\.adapter` —— **零命中**。 |

---

### R-TASK-API（P0）— `TASK` 不得 import `API`

| 字段 | 内容 |
|------|------|
| **规则描述** | `app/task/**` **不得** import 任意 `**/api/**`，禁止 Worker 回调 HTTP 自身绕 DB。 |
| **违规示例** | `chat_jobs.py`：`from app.chat.api import something`。 |
| **检测方式** | **import-linter** `app.task` → `forbidden` 含 `app.chat.api` 等；**rg** `from app\.\w+\.api` 于 `app/task/`。 |

---

### R-UC-API（P0）— `UC` 不得 import `API`

| 字段 | 内容 |
|------|------|
| **规则描述** | `use_cases` **不得**依赖 Flask `request` 或 `api` 包。 |
| **违规示例** | `from flask import request` in `use_cases/chat_orchestration.py`。 |
| **检测方式** | ① **`rg-guard-uc-flask`**：`rg "flask\\.request|from app\\.\\w+\\.api|from flask import request" app/use_cases` —— **零命中**；② **import-linter**：`app.use_cases` → **`flask`** **forbidden**（**不设**「纯函数例外」；**测试夹具** 不得放在 `app/use_cases/` 内，应置于 `tests/`）。 |

---

### R-QUEUE-CONSIST（P0）— 入队与 DB 一致、禁止悬挂 pending

| 字段 | 内容 |
|------|------|
| **规则描述** | **先** 事务提交占位/任务行，**再** `enqueue`；失败须补偿为 **`failed` + error.code**；禁止长期 `pending` 无消费者。 |
| **违规示例** | `enqueue` 成功后再写 DB 且中间崩溃导致孤儿消息；入队失败后占位仍 `pending`。 |
| **检测方式** | ① **集成测试**：模拟 `enqueue` 抛错 → DB 行 **`failed`** 且 `QUEUE_UNAVAILABLE`；② **僵尸探针（可机判参数）**：`AsyncTaskStatus=pending` 且 `updated_at` **早于当前时间 30 分钟** 且无对应 broker 深度/消费者心跳解释的行 → **告警或 staging fail**（SQL/脚本路径：`scripts/ci/zombie_pending.sql` 或等价，**阈值 30 写死**，变更须同步改本句）。 |

---

### W2-DUP（P1）— `SVC` 不得承载 UC 级 Prompt 片段

| 字段 | 内容 |
|------|------|
| **规则描述** | 与 **W2**「`SVC` 不得复制 `UC` 内 Prompt/分块」一致；本条目给出 **可机判代理**。 |
| **违规示例** | `chat_service.py` 内含多行 `{"role":"system","content":"你是…"}`。 |
| **检测方式** | **`rg`** 于 `app/**/service/**/*.py`：`"role"\s*:\s*"system"|SYSTEM_PROMPT|PROMPT_` —— **命中即 CI fail**；修复方式：删除或 **整段迁至** `app/use_cases/`。 |

---

## 3. 必须规则（MUST）：描述 + 正向示例 + 检测方式

---

### M-QUEUE-WORKER — 必须使用 queue + worker（生产默认）

| 字段 | 内容 |
|------|------|
| **规则描述** | Chat、Document LLM、默认 PDF 解析、课题 LLM 抽词：**生产默认** 经 **Redis（或声明的 broker）+ 独立 Worker**；API 仅 **受理与查询状态**。 |
| **正向示例** | `docker-compose up web worker redis`；`chat_jobs` 仅在 worker 日志出现消费记录。 |
| **检测方式** | 与 **R-NO-QUEUE** 检测表 **全条相同**（**P0**）；**worker heartbeat / 健康检查**（**P1**，**不**作为合并门禁默认值，但 staging 建议启用）。 |

---

### M-CHAIN-WORKER — Worker 内 `adapter` 调用链须经过 `UC`

| 字段 | 内容 |
|------|------|
| **规则描述** | `PROC_WORKER` 执行 `chat_jobs` / `document_jobs` / `keyword_jobs` 时，**须**先调用 **`app.use_cases`** 中函数，**且** **`adapter` 仅允许在 `UC` 模块内 import**（与 **R-UC-SKIP** 一致）。**`reconcile_jobs`** 仍须满足 **§1.1 W4**（消费路径调用 **`app.use_cases`**），**不得** `import app.adapter`；编排裁决见 **`docs/arch/ADR-reconcile-jobs-and-w4.md`**。 |
| **正向示例** | `chat_jobs.handle` → `use_cases.chat_orchestration.run_turn(...)` →（**UC 内部**）`adapter.llm.complete`。 |
| **检测方式** | ① **R-UC-SKIP**（`app.task` **零** `app.adapter` import）；② **每个** `*_jobs.py` **`rg` `use_cases|app\.use_cases`** —— **至少一命中**；③ **集成（P0）**：消费单条 Chat/Document job 时 **`unittest.mock`** 断言 **至少一次** 调用 **`app.use_cases`** 中 **预定入口**（入口名写死在测试常量表，与 **R-UC-ONLY** 文档表对齐）。 |

---

### M-POLICY-ENQUEUE — 入队前 Policy + 入队顺序

| 字段 | 内容 |
|------|------|
| **规则描述** | Chat/Document/Keyword 入队前走 **PolicyGateway**；顺序 **commit → enqueue**（见 **`execution_plan.md` §9.2.1**）。 |
| **正向示例** | `policy.assert_can_enqueue(...)` → `db.session.commit()` → `queue.enqueue(...)`。 |
| **检测方式** | 集成测试 spy：`commit` 先于 `enqueue`；Policy 拒绝时 **无** enqueue 调用。 |

**M-POLICY-ENQUEUE 与 R-POLICY-SVC 划界**：**R-POLICY-SVC** 约束 **`SVC` 在入队前须调用 Policy 门面**（拒绝时 **429/503**、`error.code` 与契约一致）；**M-POLICY-ENQUEUE** 约束 **事务顺序 `commit → enqueue`** 与 **Policy 拒绝时不发生 enqueue**（顺序与副作用）。集成：**R-POLICY-SVC** 由 **`it-policy-deny-*`** 覆盖「可拒绝且 enqueue 未调用」；**M-POLICY-ENQUEUE** 可与 **R-QUEUE-CONSIST** 的 **`it-enqueue-order`** **合并断言** `commit` 先于 `enqueue`。

---

## 4. import-linter 合约草案（可直接抄入 `pyproject` / 专用 yaml）

以下名字为逻辑层 id，路径按 **§0** 调整。

```ini
# 逻辑说明：禁止 API 触碰 adapter / use_cases / task；禁止 task import api；禁止 use_cases import api。
[importlinter]
root_package = app

[importlinter:contract:forbidden_api_adapter]
name = API must not import adapter
type = forbidden
source_modules =
    app.identity.api
    app.terms.api
    app.taskboard.api
    app.chat.api
    app.document.api
    app.topic.api
    app.selection.api
    app.recommendations.api
forbidden_modules =
    app.adapter

[importlinter:contract:forbidden_api_use_cases]
name = API must not import use_cases
type = forbidden
source_modules =
    app.identity.api
    app.terms.api
    app.taskboard.api
    app.chat.api
    app.document.api
    app.topic.api
    app.selection.api
    app.recommendations.api
forbidden_modules =
    app.use_cases

[importlinter:contract:forbidden_api_task]
name = API must not import task package
type = forbidden
source_modules =
    app.identity.api
    app.terms.api
    app.taskboard.api
    app.chat.api
    app.document.api
    app.topic.api
    app.selection.api
    app.recommendations.api
forbidden_modules =
    app.task

[importlinter:contract:forbidden_task_api]
name = TASK must not import API layers
type = forbidden
source_modules =
    app.task
forbidden_modules =
    app.identity.api
    app.terms.api
    app.taskboard.api
    app.chat.api
    app.document.api
    app.topic.api
    app.selection.api
    app.recommendations.api

[importlinter:contract:forbidden_task_adapter]
name = TASK must not import adapter
type = forbidden
source_modules =
    app.task
forbidden_modules =
    app.adapter
```

**说明**：① `import-linter` 对「字符串动态 import」**无效**，须 **§5.1** 与 **R-API-LLM** 集成测兜底；② **ORM 直连** 由 **R-API-MODEL** 的 **`rg-guard-api-model`** 覆盖（**非** import-linter 默认能力）。

---

## 5. CI 建议任务矩阵（可复制到 README / CI yaml）

| Job | 命令 / 动作 | 覆盖规则 |
|-----|-------------|----------|
| `lint-imports` | `lint-imports` 或 `import-linter`（须含 **§4** 全部合约：`forbidden_api_*`（含 **`forbidden_api_task`**）、`forbidden_task_api`、`forbidden_task_adapter`） | R-API-ADAPTER、R-API-UC、**R-API-TASK**、R-TASK-API、R-REC-LLM、**R-UC-SKIP**、**forbidden_task_adapter** |
| `rg-guard-api` | `rg "from app\\.(adapter|use_cases)\\b" app/ -g "**/api/**/*.py"` | R-API-ADAPTER、R-API-UC |
| `rg-guard-api-task` | `rg "from app\\.task\\b|import app\\.task\\b" app/ -g "**/api/**/*.py"` —— **零命中** | **R-API-TASK** |
| `rg-guard-svc-llm` | `rg "adapter\\.llm|from app\\.adapter.*llm" app/ -g "**/service/**/*.py"` | R-SVC-LLM |
| `rg-guard-uc-flask` | `rg "flask\\.request|from flask import request|from app\\.\\w+\\.api" app/use_cases` | R-UC-API |
| `it-async-chat` | pytest：无 worker 时 Chat POST **202**、无厂商 HTTP | R-SYNC-LLM、M-QUEUE-WORKER |
| `it-async-document` | pytest：Document POST **202**；缺 `term_id` 时 **400**（与 `contract.yaml` multipart 必填一致） | R-SYNC-LLM、契约校验 |
| `it-topic-enqueue-errors` | pytest：Topic PATCH 触发入队且 mock 失败 → **503** + `QUEUE_UNAVAILABLE`（或契约等价） | R-QUEUE-CONSIST、M-POLICY-ENQUEUE |
| `it-enqueue-order` | pytest：commit 先于 enqueue；enqueue 失败补偿 | R-QUEUE-CONSIST、M-POLICY-ENQUEUE |
| `rg-guard-task-adapter` | `rg "from app\\.adapter|import app\\.adapter" app/task -g "**/*.py"` —— **零命中** | R-UC-SKIP |
| `rg-guard-api-model` | 同 **R-API-MODEL** 检测命令 | R-API-MODEL |
| `rg-guard-svc-uc-signals` | 同 **R-UC-ONLY** ② | R-UC-ONLY |
| `rg-guard-jobs-biz` | 同 **R-TASK-BIZ** ① | R-TASK-BIZ |
| `it-uc-skip-chain` | pytest：mock 消费 `chat_jobs` / `document_jobs`，断言 **调用** `app.use_cases` 预定入口 ≥1 次 | M-CHAIN-WORKER |
| `it-adapter-meter` | pytest：mock Adapter 前计量失败 → job **failed** 或 **重试次数 ≤K**（K 写死在测试） | M-ADAPTER-METER |
| `check-queue-keys` | `python scripts/ci/check_queue_contract_keys.py`（校验 `contract.yaml` → `x-task-contracts.queues` **含** `chat_jobs`、`document_jobs`、`pdf_parse`、`keyword_jobs`、`reconcile_jobs`） | R-QUEUE-ISO |
| `check-llm-entrypoints-doc` | PR：`python scripts/ci/check_llm_entrypoints_doc.py`；**main 保护分支**：同命令加 **`--with-diff`**（`app/use_cases/` 变更须同 PR 改 `docs/arch/llm_entrypoints.md`） | R-UC-ONLY |
| `rg-guard-app-examples` | `python scripts/ci/rg_guard_app_examples.py` | R-APP-EXAMPLES |
| `check-api-packages-in-linter` | `python scripts/ci/check_api_packages_in_linter.py`（磁盘 `app/*/api` ⊆ **§4** `forbidden_api_adapter.source_modules`） | R-API-ADAPTER、§4 完整性 |
| `check-policy-deny-tests` | `python scripts/ci/check_policy_deny_tests.py`（三文件存在、无 `pytest.skip`；有 `app/` 时 **必跑** 三测） | R-POLICY-SVC |
| `it-policy-deny-chat` | pytest：mock Policy **拒绝** → Chat POST messages **429/503** 且 **enqueue 未被调用** | R-POLICY-SVC |
| `it-policy-deny-document` | pytest：同上 → Document POST **429/503**、enqueue 未调用 | R-POLICY-SVC |
| `it-policy-deny-topic` | pytest：同上 → Topic 触发入队写路径 **429/503**、enqueue 未调用 | R-POLICY-SVC |

**说明（工程落地）**：上表 **`it-policy-deny-*`** 为 **P0 合并门禁**；代码仓库 **须** 提供对应 **`tests/`** 用例（**禁止**长期 `pytest.skip` 占位），否则 CI 与本文 **不一致**。

### §5.1 最小 PROC_API 集成用例（**R-API-LLM** / **R-SYNC-LLM** **P0 必跑**）

| # | 用例 | 断言 |
|---|------|------|
| 1 | **Chat POST** `/conversations/{id}/messages`，**不启动 Worker**，broker **可用** | **≤800ms** 返回 **202**；**无**对厂商 LLM HTTP |
| 2 | **Document POST** `/document-tasks`（multipart **含** `term_id`），同上 | **≤800ms** 返回 **202**；**无** LLM HTTP |
| 3 | **Topic PATCH** 触发 `keyword_jobs` 入队路径 | 返回 **200/201** 且 **无** LLM HTTP；入队失败时 **503** + `QUEUE_UNAVAILABLE`（与契约对齐） |
| 4 | **Policy 拒绝（三域）** | 与 **`it-policy-deny-*`** 相同断言集（**R-POLICY-SVC P0**；可与 §5 表合并执行） |

---

## 6. 状态命名与契约对齐

- 对外与 **`contract.yaml`**：`pending` \| `running` \| `done` \| `failed`（**`AsyncTaskStatus`**）。  
- DB 历史字段 `success` / `completed` 须在 **序列化层** 映射为 `done`，且 **API 不混用**。  
- **志愿填报等业务枚举**（`ApplicationFlowStatus`）可与 `AsyncTaskStatus` **取值重名**（如 `pending`），**响应体须分 schema**，客户端与测试勿用同一类型断言混过去。

---

## 7. 队列隔离与同会话顺序（可检规则）

### R-QUEUE-ISO（P0）— 队列名与契约真源一致

| 字段 | 内容 |
|------|------|
| **规则描述** | **`contract.yaml` → `x-task-contracts.queues`** 为队列名 **真源**；凡 **`enqueue(...)` 使用的队列名字面量** 须 **为该节已声明的键**（**含 `reconcile_jobs`**）。**`reconcile_jobs` 的特殊点**仅为 **无对外 REST**，**不是**「可不声明队列名」的豁免。 |
| **违规示例** | 代码中硬编码 `enqueue("chat-job")` 与契约 `chat_jobs` 不一致；或未在契约中声明即使用 `reconcile_jobs` 字面量以外的别名。 |
| **检测方式** | **`check-queue-keys`**（§5）：脚本解析 `contract.yaml` 并断言 **至少含** `chat_jobs`、`document_jobs`、`pdf_parse`、`keyword_jobs`、`reconcile_jobs`；另 **`rg`** `enqueue\\(|enqueue_` 于 `app/**/service/**/*.py` + `app/task/queue.py` 出现的 **字符串字面量队列名** 须 **⊆** 脚本输出的键集合（**脚本 `scripts/ci/check_queue_contract_keys.py` 由实现填充**，本 spec 要求 **CI 必跑**）。 |

### R-CHAT-JOB-ORDER（P0）— 同会话多 job 顺序策略须写死

| 字段 | 内容 |
|------|------|
| **规则描述** | 同 `conversation_id` 多 job **串行消费** 或 **过期丢弃** **二选一**，须在 **`docs/arch/chat_job_order.md`**、**`app/config.py` 常量 `CHAT_JOB_ORDER=`**，或 **`execution_plan.md` 固定小节「### Chat 同会话多 job 顺序（真源）」** 三选一写明；默认 **串行**（与 **`execution_plan.md`** 该小节及设计长文 §14.3 一致）。 |
| **违规示例** | 无上述任一落点、Worker 并行消费同会话导致乱序写库。 |
| **检测方式** | ① **CI（可机判）**：**三选一**——`test -f docs/arch/chat_job_order.md` **为真**，**或** `rg "^CHAT_JOB_ORDER\\s*=" app/config.py` **命中**，**或** `rg "^### Chat 同会话多 job 顺序（真源）" execution_plan.md` **命中**（仓库根路径）；② **集成（P1）**：同会话连发两条消息，断言 **完成顺序** 或第二条 **skipped/expired** 标记。 |

---

## 8. Policy、Adapter 与 TOCTOU（可检规则）

### R-POLICY-SVC（P0）— 入队路径须调用 Policy 门面

| 字段 | 内容 |
|------|------|
| **规则描述** | **`ChatService` / `DocumentService` / `TopicService` / `SelectionService`** 在 **执行任何生产路径 `enqueue(...)`**（**含** **`enqueue(reconcile_jobs)`**）上，**须**在 **`enqueue` 生效前** 通过 **PolicyGateway**（或 **`common.policy`** 等价门面），**或** 通过 **`task.queue` 内对 `contract.yaml` → `x-task-contracts.queues` 所含队列名（**含 `reconcile_jobs`**）执行的同等 broker/深度/Rules 检查**——**二者实现择一并写死**，且须与 **M-POLICY-ENQUEUE** 的 **`commit` → `enqueue`** 顺序兼容。 |
| **违规示例** | `DocumentService.create_task` 内直接 `enqueue` 无 `policy` 调用；`SelectionService.accept` 在 **`commit` 成功后** 裸调 **`enqueue(reconcile_jobs)`** 而无上述任一检查。 |
| **检测方式** | ① **P0 集成（必跑，三域）**：**`it-policy-deny-chat`**、**`it-policy-deny-document`**、**`it-policy-deny-topic`**（§5）— mock **PolicyGateway**（或等价门面）**拒绝** → HTTP **429 或 503**，且 **`enqueue` spy 零调用**；**`reconcile_jobs`**：在 **`it-enqueue-order`** 或专用集成用例中 **spy** `SelectionService`（或 `queue.enqueue`）路径，mock **Policy/统一入队门面拒绝** → **`enqueue(reconcile_jobs)` 零调用** 且 DB 侧 **`accept` 事务不提交入队副作用**（具体断言由测试写死）；② **M-POLICY-ENQUEUE**：`commit` 先于 `enqueue`、Policy 拒绝时无 enqueue（可与 ① 复用 spy）；③ **静态启发式（P1）**：`rg "enqueue"` 于 `app/chat/service/**/*.py`、`app/document/service/**/*.py`、`app/topic/service/**/*.py`、**`app/selection/service/**/*.py`** —— 同文件须 `rg "policy|PolicyGateway|assert_can_enqueue"` **至少一命中**（**非**合并唯一依据）。 |

### M-ADAPTER-METER（P1）— TOCTOU 与限重试可观测

| 字段 | 内容 |
|------|------|
| **规则描述** | **Adapter** 调用前 **计量/扣减**；失败须 **有限重试** 或 **failed**（execution_plan §14.2）。 |
| **违规示例** | 无限 `while True: retry_llm()`。 |
| **检测方式** | **集成**：**§5 `it-adapter-meter`**；**静态（辅助）**：`rg "while True"` 于 `app/task/**/*_jobs*.py` 与 `app/use_cases/**/*.py` —— **命中须 PR 说明**（**非唯一门禁**）。 |

---

## 9. 规则索引表（供测试用例 `@pytest.mark.arch` 映射）

| ID | 一句话 |
|----|--------|
| R-API-ADAPTER | API 不 import adapter |
| R-API-LLM | API 栈不调 LLM（含间接、动态 import） |
| R-API-UC | API 不 import use_cases |
| R-API-TASK | API 不 import app.task |
| R-API-MODEL | API 不直连 ORM models |
| R-APP-EXAMPLES | app 不 import examples |
| R-SYNC-LLM | API 进程不阻塞等 LLM |
| R-TASK-BIZ | job 无业务编排（P0 rg） |
| R-UC-SKIP | task 包不 import adapter；必经 UC |
| R-NO-QUEUE | 生产必须 broker+worker |
| R-UC-ONLY | 编排仅在 UC |
| R-SVC-LLM | service 不直连 LLM（生产） |
| R-REC-LLM | 推荐不调 llm/nlp 替代 Topic |
| R-TASK-API | task 不 import api |
| R-UC-API | UC 不 import api / request |
| R-QUEUE-CONSIST | 先入库再入队、失败补偿 |
| R-QUEUE-ISO | 队列键与 contract 一致 |
| R-CHAT-JOB-ORDER | 同会话 job 顺序策略写死 |
| R-POLICY-SVC | 入队路径须调 Policy |
| W2-DUP | SVC 无 UC 级 Prompt 片段 |
| M-QUEUE-WORKER | 生产 queue+worker |
| M-CHAIN-WORKER | Worker 经 UC；集成断言 UC 被调用 |
| M-POLICY-ENQUEUE | Policy + commit/enqueue 顺序 |
| M-ADAPTER-METER | TOCTOU+限重试可观测 |
