# 规范提取 — REST 路径子表

> **文档导航**：[分类总目](../DOCUMENT-CATALOG.md) · [文档索引](../README.md) · [规范提取（完整）](./spec-extraction-full.md) · [后台任务子表](./spec-extraction-background-tasks.md)  
> **真源**：`spec/contract.yaml`（`servers[0].url` 为 `https://{host}/api/v1`）。  
> 下列路径均相对于 **`/api/v1`**。完整上下文见 [spec-extraction-full.md](./spec-extraction-full.md)。

| 方法 | 路径 | 域 / 摘要 |
|------|------|-----------|
| `POST` | `/auth/login` | identity — 登录 |
| `POST` | `/auth/refresh` | identity — 刷新令牌 |
| `POST` | `/auth/logout` | identity — 登出 |
| `GET` | `/users/me` | identity — 当前用户 |
| `PATCH` | `/users/me` | identity — 更新资料 |
| `GET` | `/terms` | terms — 学期列表 |
| `POST` | `/terms` | terms — 管理员新建学期 |
| `GET` | `/terms/{term_id}` | terms — 学期详情 |
| `PATCH` | `/terms/{term_id}` | terms — 更新学期 |
| `GET` | `/terms/{term_id}/llm-config` | terms — 读 LLM 配置 |
| `PATCH` | `/terms/{term_id}/llm-config` | terms — 更新 LLM 配置 |
| `GET` | `/milestones` | taskboard — 里程碑列表 |
| `POST` | `/milestones` | taskboard — 学生创建 |
| `GET` | `/milestones/{milestone_id}` | taskboard — 详情 |
| `PATCH` | `/milestones/{milestone_id}` | taskboard — 更新 |
| `DELETE` | `/milestones/{milestone_id}` | taskboard — 删除 |
| `GET` | `/conversations` | chat — 会话列表 |
| `POST` | `/conversations` | chat — 新建会话（须 `term_id`） |
| `GET` | `/conversations/{conversation_id}` | chat — 会话元数据 |
| `DELETE` | `/conversations/{conversation_id}` | chat — 软删/归档（可选实现） |
| `GET` | `/conversations/{conversation_id}/messages` | chat — 分页历史消息 |
| `POST` | `/conversations/{conversation_id}/messages` | chat — 发消息（**202**） |
| `GET` | `/chat/jobs/{job_id}` | chat — 查询异步任务（可选） |
| `GET` | `/conversations/{conversation_id}/stream` | chat — 可选 SSE |
| `POST` | `/document-tasks` | document — 上传创建任务（**202**，multipart） |
| `GET` | `/document-tasks` | document — 任务列表 |
| `GET` | `/document-tasks/{task_id}` | document — 单任务详情 |
| `GET` | `/topics` | topic — 课题列表 |
| `POST` | `/topics` | topic — 创建草稿 |
| `GET` | `/topics/{topic_id}` | topic — 详情 |
| `PATCH` | `/topics/{topic_id}` | topic — 更新 |
| `DELETE` | `/topics/{topic_id}` | topic — 删除/撤回 |
| `POST` | `/topics/{topic_id}/submit` | topic — 提交审核 |
| `POST` | `/topics/{topic_id}/review` | topic — 管理员审核 |
| `POST` | `/applications` | selection — 新增志愿 |
| `GET` | `/applications` | selection — 志愿列表 |
| `DELETE` | `/applications/{application_id}` | selection — 撤销 |
| `PATCH` | `/applications/{application_id}` | selection — 修改优先级等 |
| `POST` | `/applications/{application_id}/decisions` | selection — 教师接受/拒绝 |
| `GET` | `/assignments` | selection — 指导关系列表 |
| `GET` | `/assignments/{assignment_id}` | selection — 指导关系详情 |
| `GET` | `/recommendations/topics` | recommendations — Top-N（须 `term_id`） |

## 契约要点（仅 REST 相关）

- **202**：`POST .../messages`、`POST /document-tasks`。
- **429 / 503**：Chat/Document/Topic 等与 Policy、入队失败对齐 **`ErrorEnvelope`**。
- **Document multipart 必填**：`file`、`term_id`。
- **推荐 query 必填**：`term_id`。
- **消息列表游标**：`after_message_id` 与 `before_message_id` 互斥。
