# 前端 Round 3：登录与 Chat 联调设计文档

## 背景

当前仓库的 `frontend/` 已完成 Round 1 的独立工程初始化、应用壳布局与静态页面骨架，`dashboard`、`chat`、`documents`、`topics`、`taskboard` 已具备演示级的页面结构。

后端方面，认证、会话、消息发送与 chat job 状态查询已在 `spec/contract.yaml` 中具备明确契约，并且项目测试中已大量覆盖：

- `POST /api/v1/auth/login`
- `GET /api/v1/conversations`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}/messages`
- `POST /api/v1/conversations/{conversation_id}/messages`
- `GET /api/v1/chat/jobs/{job_id}`

基于总设计文档中的“Round 3：接入主演示链路 API”，本轮聚焦最有演示价值的一条主线：真实登录与异步聊天。

## 目标

在现有 `frontend/` 基础上，完成以下联调目标：

1. 登录页接入真实 `POST /api/v1/auth/login`。
2. 登录成功后保存 `access_token` 并恢复登录态。
3. Chat 页面接入真实会话列表与消息列表。
4. 支持真实发送消息，并处理 `202` 异步受理响应。
5. 基于 `job_id` 查询 chat job 状态，并按 `pending / running / done / failed` 做状态驱动轮询。
6. 在现有 UI 中显式呈现聊天异步状态，而不改变整体应用壳结构。

## 非目标

本轮明确不做：

- 不接入 Documents API
- 不接入 Dashboard 真实统计数据
- 不接入 Topics / Taskboard 真实数据
- 不尝试 SSE 流式方案
- 不实现 refresh token 完整前端策略
- 不实现多角色权限差异化前端逻辑
- 不做完整契约代码生成

## 范围

本轮仅覆盖以下页面与模块：

- `/login`
- `/app/chat`
- 登录态存储与恢复
- 基础 Axios 鉴权注入
- Chat 相关 Query / Mutation / Polling

## 技术方案

沿用既有前端技术栈：

- React
- Vite
- TypeScript
- React Router
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand
- Axios

本轮不新增重型状态管理或额外数据层框架。

## 接口范围与契约约束

### 登录

使用：

- `POST /api/v1/auth/login`

请求体：

- `username`
- `password`

前端必须以真实响应为准，不擅自扩展登录返回结构。

### 会话

使用：

- `GET /conversations`
- `POST /conversations`

注意：

- `CreateConversationRequest` 要求包含 `term_id`
- 若需要自动创建会话，前端应从当前学期上下文中读取 `term_id`
- 默认创建 `context_type = general` 的学生端通用会话即可

### 消息

使用：

- `GET /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/messages`

前端必须按契约处理：

- `POST` 返回 `202`
- 响应包含 `job_id`
- 响应同时返回 `user_message` 与 `assistant_message`
- `assistant_message.status` 可能为 `pending` 或 `running`

### Chat Job

使用：

- `GET /chat/jobs/{job_id}`

状态机必须遵守契约：

- `pending`
- `running`
- `done`
- `failed`

轮询必须由状态驱动，并在终态后停止。

## 路由与交互

### `/login`

行为变更：

- 从假登录跳转改为真实请求
- 登录成功后跳转 `/app/dashboard`
- 登录失败时在表单区域显示贴近错误反馈

登录状态策略：

- `access_token` 使用 `localStorage` 持久化
- 用户摘要与登录态同步到 Zustand
- 刷新页面时从本地恢复登录态

### `/app/chat`

行为变更：

- 左侧会话列表改为真实数据
- 中间消息流改为真实消息列表
- 输入区发送真实消息
- 右侧摘要区展示当前会话上下文和最近异步状态说明

若用户没有任何会话：

- 前端自动创建一个 `general` 会话
- 创建成功后立即进入该会话

## 文件结构设计

推荐新增与修改如下：

```text
frontend/src/
  app/
    store.ts
  features/
    auth/
      auth-store.ts
      auth.api.ts
      auth.storage.ts
      auth.types.ts
    chat/
      chat.api.ts
      chat.queries.ts
      chat.types.ts
      chat.utils.ts
  lib/
    axios.ts
    api-error.ts
  pages/
    login/login-page.tsx
    chat/chat-page.tsx
```

职责边界如下：

- `auth.api.ts` 只处理认证请求
- `auth.storage.ts` 只处理本地 token / user 持久化
- `chat.api.ts` 只处理 chat 相关 HTTP 请求
- `chat.queries.ts` 只处理 Query / Mutation / Polling 组织
- `chat.utils.ts` 只放轻量纯函数，如终态判断
- 页面层负责组合状态与展示，不直接拼接底层请求逻辑

## 数据流设计

### 登录流

1. 用户在 `/login` 输入用户名和密码。
2. 页面调用 `auth.api.ts` 中的登录请求。
3. 成功后把 `access_token` 与 `user` 写入 `localStorage`。
4. Zustand 同步更新：
   - `isAuthenticated`
   - `accessToken`
   - `currentUser`
5. 页面跳转到 `/app/dashboard`。

### Chat 初始化流

1. Chat 页面加载会话列表。
2. 若列表为空，则自动调用创建会话接口。
3. 选中默认会话后加载消息列表。
4. 当前会话 id 存在页面局部状态中。

### 发送消息流

1. 用户提交输入框内容。
2. 前端调用 `POST /conversations/{conversation_id}/messages`。
3. 前端立即把返回的：
   - `user_message`
   - `assistant_message`
   插入当前消息流。
4. 若 `assistant_message.status` 为 `pending` 或 `running`，启动 job 轮询。
5. 每次 job 查询成功后刷新消息列表。
6. 进入 `done` 或 `failed` 时停止轮询。

## 状态策略

### Zustand

仅用于：

- `isAuthenticated`
- `accessToken`
- `currentUser`
- `currentTerm`
- 登录恢复

不用于：

- 会话列表缓存
- 消息列表缓存
- job 轮询缓存

### TanStack Query

用于：

- 登录 mutation
- 会话列表 query
- 会话消息列表 query
- 发消息 mutation
- chat job query / polling

### 页面局部状态

仅用于：

- `selectedConversationId`
- 输入框内容
- 轻量 UI 错误提示可见性

## 轮询策略

轮询规则必须写死为：

- 当 job `status` 为 `pending` 或 `running` 时继续轮询
- 当 job `status` 为 `done` 或 `failed` 时停止

刷新规则：

- job 状态变化后，重新请求当前会话消息列表
- 以消息列表中的 assistant 实际内容作为最终展示真源

本轮不做：

- 多 job 并发复杂调度
- 页面离开后的后台持续轮询
- SSE fallback

## 错误处理

前端必须统一适配 `ErrorEnvelope`。

建议新增共享错误解析函数，抽取：

- `code`
- `message`
- `details`

页面级行为：

### 登录页

- `401` 或无效凭据：在表单区展示错误
- `VALIDATION_ERROR`：展示输入提示
- 其他错误：展示通用登录失败文案

### Chat 页

- 会话加载失败：展示可重试错误块
- 消息加载失败：在消息区展示错误提示
- 发消息失败：在输入区附近展示错误
- job 失败：在 assistant 消息状态处展示 `failed`

## UI 变化要求

本轮不重做视觉风格，只在现有页面上做真实状态替换。

重点要求：

- 登录按钮需体现提交中状态
- 会话列表需体现真实更新时间或标题
- assistant 占位消息在 `pending / running / done / failed` 之间过渡明确
- 失败消息不能静默消失

## 测试策略

本轮采用“轻量测试 + 强验证”的方式。

建议新增最小测试覆盖：

- `auth.storage.ts`
- `lib/api-error.ts`
- `chat.utils.ts`

若当前前端工程还没有测试框架，可引入 `Vitest` 作为最小单元测试工具。

本轮强验证包括：

- `npm run build`
- 真实登录请求验证
- Chat 页面真实会话加载验证
- 真实发送消息与 job 状态变化验证

## 风险与缓解

### 风险一：登录响应结构与前端假设不一致

缓解方式：

- 以真实返回体为准，仅做最小字段映射

### 风险二：创建会话时缺少 `term_id`

缓解方式：

- 从当前学期上下文读取真实 `term_id`
- 若当前前端默认学期值仅为 mock，也要保证字段名与契约一致

### 风险三：job 完成但 assistant 内容未立即在 job 响应中体现

缓解方式：

- job 只作为状态真源
- assistant 最终内容通过重新拉取消息列表回填

### 风险四：错误反馈不统一

缓解方式：

- 所有 HTTP 错误统一先过 `ErrorEnvelope` 解析层

## 验收标准

本轮完成后，应满足以下条件：

1. 用户可通过真实 `/auth/login` 登录。
2. 登录后刷新页面仍保留登录态。
3. Chat 页面能加载真实会话列表。
4. 无会话时能自动创建一个通用会话。
5. 用户可真实发送消息，并拿到 `202` 返回。
6. `pending / running / done / failed` 状态能在 UI 中体现。
7. chat job 轮询在终态后停止。
8. `npm run build` 通过。

## 最终建议

本轮应只聚焦“登录 + Chat”这条主演示链路，用最小但完整的真实联调，把异步聊天能力从静态骨架推进到可演示的真实交互。

在这一轮稳定后，再单独进入 Documents 联调，会比同时铺开两条异步主线更稳，也更容易控制答辩节奏。
