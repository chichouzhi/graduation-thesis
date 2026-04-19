# 架构任务图（分层 Todo）

> **文档导航**：[分类总目](../DOCUMENT-CATALOG.md) · [文档索引](../README.md) · [系统架构](../architecture/system-architecture.md) · [规范提取（完整）](../requirements/spec-extraction-full.md) · [JSON 真源](./architecture-task-graph.json)

机器可读真源：[architecture-task-graph.json](./architecture-task-graph.json)（`tasks[].depends_on` 即 DAG 边：所列 **全部** 前置任务完成后方可开始本项）。

约束：每项 **原子**（预估 **≤2 天**）、**禁止合并**为多交付物；优先级 **P0 / P1 / P2**。

---

## 分层：`bootstrap`

### AG-001

- **标题**：Flask 应用工厂骨架（无业务域路由）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：无

### AG-002

- **标题**：`app/extensions.py` 挂载 db/migrate/jwt 等扩展（占位可 import）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-003

- **标题**：`app/config.py`：production 缺 broker URL 时启动失败（R-NO-QUEUE）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-004

- **标题**：注册 `/api/v1` 与 8 域 Blueprint 空壳（路由文件可空）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

## 分层：`common`

### AG-005

- **标题**：全局 `ErrorEnvelope` 序列化与 `error.code` 常量（对齐 contract 枚举）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-006

- **标题**：`PolicyGateway` / `assert_can_enqueue` 门面签名与依赖注入点
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-005

### AG-007

- **标题**：Policy 拒绝 → HTTP 429/503 与 `POLICY_QUEUE_DEPTH`/`QUEUE_UNAVAILABLE` 映射单元测骨架
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-006

## 分层：`model`

### AG-008

- **标题**：`users` 及角色枚举 ORM（对齐 `UserSummary`/`UserMe` 最小字段）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-002

### AG-009

- **标题**：`terms` 表 ORM（含选题窗口字段）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-002

### AG-010

- **标题**：按 `term_id` 的 `LlmConfig` 持久化 ORM（独立表或列二选一写死）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-009

### AG-011

- **标题**：`conversations` ORM（`term_id` 非空、索引）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-009

### AG-012

- **标题**：`messages` ORM（assistant 占位、`delivery_status` 或等价列）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-011

### AG-013

- **标题**：`chat_jobs` ORM（`job_id`、重试、`error_*`、列表索引）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-012

### AG-014

- **标题**：`document_tasks` ORM（`term_id`、锁、断点、`result_*`、`error_*`）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-009

### AG-015

- **标题**：`topics` ORM（审核状态枚举）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-009

### AG-016

- **标题**：`topic_portraits` 或等价 JSON 列 ORM
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-015

### AG-017

- **标题**：`applications` ORM（唯一约束与 `ApplicationFlowStatus`）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-015, AG-008

### AG-018

- **标题**：`assignments` 真源 ORM 及与 `applications` 外键
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-017

### AG-019

- **标题**：`milestones` ORM（`sort_order`、`is_overdue` 策略写死）
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-008

### AG-020

- **标题**：Alembic 迁移：identity + terms + llm_config 相关表
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-008, AG-009, AG-010

### AG-021

- **标题**：Alembic 迁移：chat（conversations/messages/chat_jobs）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-011, AG-012, AG-013

### AG-022

- **标题**：Alembic 迁移：document_tasks
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-014

### AG-023

- **标题**：Alembic 迁移：topics + topic_portraits
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-015, AG-016

### AG-024

- **标题**：Alembic 迁移：applications + assignments
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-017, AG-018

### AG-025

- **标题**：Alembic 迁移：milestones
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-019

## 分层：`adapter`

### AG-026

- **标题**：`app.adapter` 包布局与对外导入约定（子包 llm/pdf/nlp/storage）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-027

- **标题**：`adapter.llm`：协议/客户端基类（无厂商 HTTP 亦可 mock）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-026

### AG-028

- **标题**：`adapter.llm`：具体厂商 HTTP 实现（单文件）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-027

### AG-029

- **标题**：`adapter.pdf`：解析入口封装（供 UC/worker 调用）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-026

### AG-030

- **标题**：`adapter.storage`：上传/读取路径封装（Document 落盘）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-026

### AG-031

- **标题**：`adapter.nlp`：Jieba 同步分词封装（Topic 画像，禁止全库写回）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-026

## 分层：`use_cases`

### AG-032

- **标题**：`chat_orchestration`：从入参构建 messages 列表（无 IO、无 LLM）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-033

- **标题**：`chat_orchestration`：token 级裁剪与配置读取挂钩
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-032, AG-003

### AG-034

- **标题**：`document_pipeline`：`stage`/`chunk_index` 幂等键与计划数据结构（纯函数为主）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-035

- **标题**：`document_pipeline`：chunk 并行度上限读取与校验
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-034, AG-003

### AG-036

- **标题**：`topic_keywords`：快照文本 → 调 `adapter.llm` 编排（仅 Worker 路径使用）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-027, AG-028

### AG-037

- **标题**：`reconcile_assignments`（或 ADR 命名）：`assignments` 与 `selected_count` 对账编排入口
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-018

## 分层：`task_queue`

### AG-038

- **标题**：`app/task/queue.py`：`enqueue_chat_jobs` 使用契约字面量 `chat_jobs`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-003, AG-006

### AG-039

- **标题**：`queue.py`：`enqueue_pdf_parse`（`pdf_parse` 字面量）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-038

### AG-040

- **标题**：`queue.py`：`enqueue_document_jobs`（`document_jobs` 字面量）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-038

### AG-041

- **标题**：`queue.py`：`enqueue_keyword_jobs`（`keyword_jobs` 字面量）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-038

### AG-042

- **标题**：`queue.py`：`enqueue_reconcile_jobs`（`reconcile_jobs` 字面量 + Policy/同等检查挂钩点）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-038, AG-006

## 分层：`jobs`

### AG-043

- **标题**：`task/chat_jobs.py`：handler → 预定 `use_cases` 入口 → 回写（无 Prompt 字符串）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-032, AG-038, AG-013

### AG-044

- **标题**：`task/pdf_parse_jobs.py`：`PdfJobPayload` 校验 → `document_pipeline`/`adapter.pdf` 路径挂钩
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-034, AG-029, AG-039, AG-014

### AG-045

- **标题**：`task/document_jobs.py`：按 `stage` 分派 → `document_pipeline` + LLM 回写挂钩
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-034, AG-040, AG-014

### AG-046

- **标题**：`task/keyword_jobs.py`：→ `topic_keywords` → 画像 ORM 回写
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-036, AG-041, AG-016

### AG-047

- **标题**：`task/reconcile_jobs.py`：→ `reconcile_assignments` UC → 计数/对账回写
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-037, AG-042, AG-018

## 分层：`worker_runtime`

### AG-048

- **标题**：Worker 进程入口：连接 broker、注册 `chat_jobs` 消费
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-043, AG-003

### AG-049

- **标题**：Worker：注册 `pdf_parse` / `document_jobs` 消费
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-044, AG-045, AG-048

### AG-050

- **标题**：Worker：注册 `keyword_jobs` / `reconcile_jobs` 消费
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-046, AG-047, AG-048

## 分层：`service`

### AG-051

- **标题**：`IdentityService`：凭据校验与用户加载
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-008

### AG-052

- **标题**：`IdentityService`：access token 签发与过期策略
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-051

### AG-053

- **标题**：`IdentityService`：refresh token / HttpOnly Cookie 与轮换
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-052

### AG-054

- **标题**：`IdentityService`：logout 作废 refresh 与 Cookie 清除语义
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-053

### AG-055a

- **标题**：`IdentityService`：`GET /users/me` 读取当前用户资料
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-008, AG-051

### AG-055b

- **标题**：`IdentityService`：`PATCH /users/me` 更新资料（含画像字段）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-008, AG-051

### AG-056

- **标题**：`TermService`：学期列表与单条详情（含角色可见裁剪）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-009, AG-051

### AG-057

- **标题**：`TermService`：管理员创建/更新学期
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-056

### AG-058

- **标题**：`TermService`：`LlmConfig` 读取（单一真源）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-010, AG-056

### AG-059

- **标题**：`TermService`：`LlmConfig` 更新（管理员）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-058

### AG-060

- **标题**：`MilestoneService`：学生创建/更新/删除里程碑
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-019, AG-051

### AG-061

- **标题**：`MilestoneService`：教师列表查询 + `student_id` 指导关系校验
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-060

### AG-062a

- **标题**：`ChatService`：会话列表（当前用户）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-011, AG-051

### AG-062b

- **标题**：`ChatService`：创建会话（`term_id` 必填）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-011, AG-051

### AG-062c

- **标题**：`ChatService`：读取会话元数据
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-011, AG-051

### AG-062d

- **标题**：`ChatService`：软删除或归档会话
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-011, AG-051

### AG-063

- **标题**：`ChatService`：消息分页与 `after_message_id`/`before_message_id` 互斥校验
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-012, AG-062c

### AG-064

- **标题**：`ChatService`：发消息路径调用 `chat_orchestration` 仅组装（不调 LLM）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-063, AG-033

### AG-065

- **标题**：`ChatService`：Policy → 占位事务 → `commit` → `enqueue_chat_jobs`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-064, AG-006, AG-038, AG-012, AG-013

### AG-066

- **标题**：`ChatService`：`enqueue` 失败补偿为 `failed` + `QUEUE_UNAVAILABLE`（占位/任务行）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-065

### AG-067

- **标题**：`DocumentService`：multipart 校验与 `term_id` 必填语义
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-014, AG-051

### AG-068

- **标题**：`DocumentService`：`adapter.storage` 落盘与 `storage_path` 写入任务行
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-067, AG-030

### AG-069

- **标题**：`DocumentService`：Policy → `document_tasks(pending)` → `commit` → `enqueue_pdf_parse`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-068, AG-006, AG-039

### AG-070

- **标题**：`DocumentService`：`enqueue` 失败补偿与 **202** `DocumentTask` 形状（契约字段）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-069, AG-005

### AG-071

- **标题**：`TopicService`：课题 CRUD（不含 LLM）与删除/撤回规则
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-015, AG-051

### AG-072

- **标题**：`TopicService`：`adapter.nlp`（Jieba）同步写画像字段
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-071, AG-031, AG-016

### AG-073

- **标题**：`TopicService`：`keyword_jobs` 路径 Policy → `commit` → `enqueue_keyword_jobs`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-072, AG-006, AG-041

### AG-074

- **标题**：`TopicService`：提交审核/管理员审核状态迁移（无 LLM）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-071

### AG-075a

- **标题**：`SelectionService`：创建志愿（唯一约束与 `term_id`）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-017, AG-009, AG-051

### AG-075b

- **标题**：`SelectionService`：志愿列表与过滤（教师 `topic_id` 等）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-017, AG-051

### AG-075c

- **标题**：`SelectionService`：撤销志愿（窗口与状态规则）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-017, AG-009, AG-051

### AG-075d

- **标题**：`SelectionService`：修改志愿优先级（允许窗口内）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-017, AG-051

### AG-076

- **标题**：`SelectionService`：教师 `reject` 单事务与状态回写
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-075b, AG-018

### AG-077

- **标题**：`SelectionService`：教师 `accept` — `assignments` + `selected_count` 同事务
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-075b, AG-018

### AG-078

- **标题**：`SelectionService`：`accept` **commit 成功后** Policy/同等检查 → `enqueue_reconcile_jobs`（P0）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-077, AG-042

### AG-079

- **标题**：`RecommendService`：Top-N 打分查询（只读 SQL/内存，无 LLM）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-015, AG-016, AG-051

### AG-080

- **标题**：`RecommendService`：`explain` 分支与 **403** 角色守卫
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-079

## 分层：`document_enqueue_chain`

### AG-081

- **标题**：`pdf_parse` 成功路径：由 `document_pipeline`/UC 决策触发 `enqueue_document_jobs`（对齐 ADR）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-044, AG-034, AG-040

## 分层：`api`

### AG-082

- **标题**：`app.identity.api`：`POST /auth/login` 仅转 `IdentityService`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-051

### AG-083

- **标题**：`app.identity.api`：`POST /auth/refresh`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-082, AG-053

### AG-084

- **标题**：`app.identity.api`：`POST /auth/logout`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-083, AG-054

### AG-085a

- **标题**：`app.identity.api`：`GET /users/me`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-084, AG-055a

### AG-085b

- **标题**：`app.identity.api`：`PATCH /users/me`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-085a, AG-055b

### AG-086a

- **标题**：`app.terms.api`：`GET /terms`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-056

### AG-086b

- **标题**：`app.terms.api`：`POST /terms`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-086a, AG-057

### AG-087a

- **标题**：`app.terms.api`：`GET /terms/{term_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-086b, AG-056

### AG-087b

- **标题**：`app.terms.api`：`PATCH /terms/{term_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-087a, AG-057

### AG-088a

- **标题**：`app.terms.api`：`GET /terms/{term_id}/llm-config`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-087b, AG-058

### AG-088b

- **标题**：`app.terms.api`：`PATCH /terms/{term_id}/llm-config`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-088a, AG-059

### AG-089a

- **标题**：`app.taskboard.api`：`GET /milestones`
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-004, AG-060

### AG-089b

- **标题**：`app.taskboard.api`：`POST /milestones`
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-089a, AG-060

### AG-090a

- **标题**：`app.taskboard.api`：`GET /milestones/{milestone_id}`
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-089b, AG-060

### AG-090b

- **标题**：`app.taskboard.api`：`PATCH /milestones/{milestone_id}`
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-090a, AG-060

### AG-090c

- **标题**：`app.taskboard.api`：`DELETE /milestones/{milestone_id}`
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-090a, AG-060

### AG-091

- **标题**：`app.taskboard.api`：`GET /milestones` 教师分支（`student_id`）与 `MilestoneService` 校验
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-089a, AG-061

### AG-092a

- **标题**：`app.chat.api`：`GET /conversations`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-062a

### AG-092b

- **标题**：`app.chat.api`：`POST /conversations`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-092a, AG-062b

### AG-092c

- **标题**：`app.chat.api`：`GET /conversations/{conversation_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-092b, AG-062c

### AG-092d

- **标题**：`app.chat.api`：`DELETE /conversations/{conversation_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-092c, AG-062d

### AG-093

- **标题**：`app.chat.api`：`GET /conversations/{conversation_id}/messages`（分页与游标）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-092d, AG-063

### AG-094

- **标题**：`app.chat.api`：`POST .../messages` 返回 **202** 与契约响应体
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-093, AG-066

### AG-095

- **标题**：`app.chat.api`：`GET /chat/jobs/{job_id}`（可选）
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-094, AG-013

### AG-096a

- **标题**：`app.document.api`：`POST /document-tasks`（**202**）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-070

### AG-096b

- **标题**：`app.document.api`：`GET /document-tasks`（列表）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-096a, AG-070

### AG-097

- **标题**：`app.document.api`：`GET /document-tasks/{task_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-096b

### AG-098a

- **标题**：`app.topic.api`：`GET /topics`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-071

### AG-098b

- **标题**：`app.topic.api`：`POST /topics`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-098a, AG-073

### AG-099a

- **标题**：`app.topic.api`：`GET /topics/{topic_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-098a, AG-071

### AG-099b

- **标题**：`app.topic.api`：`PATCH /topics/{topic_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-099a, AG-071, AG-073

### AG-099c

- **标题**：`app.topic.api`：`DELETE /topics/{topic_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-099a, AG-071

### AG-100a

- **标题**：`app.topic.api`：`POST /topics/{topic_id}/submit`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-099a, AG-074

### AG-100b

- **标题**：`app.topic.api`：`POST /topics/{topic_id}/review`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-099a, AG-074

### AG-101a

- **标题**：`app.selection.api`：`POST /applications`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-075a

### AG-101b

- **标题**：`app.selection.api`：`GET /applications`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-101a, AG-075b

### AG-102a

- **标题**：`app.selection.api`：`DELETE /applications/{application_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-101b, AG-075c

### AG-102b

- **标题**：`app.selection.api`：`PATCH /applications/{application_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-101b, AG-075d

### AG-103

- **标题**：`app.selection.api`：`POST /applications/{application_id}/decisions`（**200** 载荷形状）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-102b, AG-076, AG-077, AG-078

### AG-104a

- **标题**：`app.selection.api`：`GET /assignments`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-103, AG-018

### AG-104b

- **标题**：`app.selection.api`：`GET /assignments/{assignment_id}`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-104a, AG-018

### AG-105

- **标题**：`app.recommendations.api`：`GET /recommendations/topics`
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004, AG-079

### AG-106

- **标题**：`app.recommendations.api`：`explain` 与 **403** 走 `RecommendService` 分支
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-105, AG-080

## 分层：`api_optional`

### AG-107

- **标题**：`app.chat.api`：`GET .../stream` SSE 占位（**501/404** JSON `ErrorEnvelope`，未启用默认）
- **优先级**：P2
- **耗时上限**：2 天
- **依赖**：AG-094, AG-005

## 分层：`ci_docs`

### AG-108

- **标题**：CI：`lint-imports` 覆盖 `architecture.spec` §4 合约
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-004

### AG-109

- **标题**：CI：`rg-guard-api` / `rg-guard-api-task` / `rg-guard-task-adapter` 脚本接入
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-108

### AG-110

- **标题**：CI：`check_queue_contract_keys.py` 断言五队列键
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-001

### AG-111

- **标题**：集成测：`it-async-chat`（202、≤800ms、无 LLM HTTP）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-094, AG-003

### AG-112

- **标题**：集成测：`it-async-document`（202、缺 `term_id` 400）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-096a, AG-003

### AG-113

- **标题**：集成测：`it-policy-deny-chat` / `document` / `topic`（429/503 + enqueue 未调用）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-094, AG-096a, AG-099b, AG-007

### AG-114

- **标题**：集成测：`it-enqueue-order`（`commit` 先于 `enqueue`；失败补偿）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-065, AG-069

### AG-115

- **标题**：集成测：`it-uc-skip-chain`（mock 消费 `chat_jobs` 断言调用 `use_cases`）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-043

### AG-116

- **标题**：`docs/arch/llm_entrypoints.md` 建立非空入口表（R-UC-ONLY）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-032, AG-034, AG-036, AG-037

### AG-117

- **标题**：同会话 `CHAT_JOB_ORDER` 真源三选一落地（md/config/execution_plan 节）
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-043

### AG-118

- **标题**：`docker-compose`（或等价）含 **web + worker + redis** 关键字共现
- **优先级**：P0
- **耗时上限**：2 天
- **依赖**：AG-048

### AG-119

- **标题**：集成测：`it-adapter-meter`（P1：计量失败 → failed 或重试≤K）
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-043, AG-028

### AG-120

- **标题**：`openapi-spec-validator` 校验 `contract.yaml` 接入 CI
- **优先级**：P1
- **耗时上限**：2 天
- **依赖**：AG-001
