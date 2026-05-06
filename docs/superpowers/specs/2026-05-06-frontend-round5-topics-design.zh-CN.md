# 前端 Round 5：Topics 列表与详情联调设计文档

## 背景

当前仓库中的 `frontend/` 已完成以下几轮关键推进：

- Round 1：独立前端工程、应用壳与静态页面骨架
- Round 3：登录与 Chat 主链路联调
- Round 4：Documents 上传、列表、详情、状态驱动轮询联调

其中 `/app/topics` 仍然是基于本地 mock 的静态骨架页，只具备展示题目卡片和占位详情的能力。与此同时，后端在 `spec/contract.yaml` 中已经提供了稳定的 Topic 读取契约：

- `GET /api/v1/topics`
- `GET /api/v1/topics/{topic_id}`

因此，下一步最合适的推进，是把 `Topics` 做成一条真实的“题目浏览 -> 详情查看”主链路，补齐工作台在“学术选题”维度的展示能力。

## 目标

在现有 `frontend/` 基础上，完成 `/app/topics` 的真实列表与详情联调，并满足以下目标：

1. 支持拉取当前学期题目列表
2. 支持查看单个题目详情
3. 保持当前双栏浏览体验，适合答辩演示
4. 页面默认选中首个题目，并支持在列表中切换
5. 保持与 `spec/contract.yaml` 一致，不擅自扩展冲突字段
6. 统一复用现有 `ErrorEnvelope` 错误适配方式

## 非目标

本轮明确不做：

- 不实现学生志愿提交
- 不实现“我的志愿状态”展示
- 不接入 `/recommendations/topics`
- 不实现教师创建、修改、提交审核、管理员审核
- 不实现 Topic 侧异步关键词任务的轮询
- 不扩展新的页面路由

## 范围

本轮仅覆盖：

- `/app/topics`
- 题目列表
- 题目详情
- 页面内选中项切换

不扩散到 `selection`、`applications`、`recommendations` 等相关能力。

## 技术方案

延续现有前端工程的分层与技术栈：

- React
- Vite
- TypeScript
- React Router
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand
- Axios

状态职责保持与 Chat、Documents 一致：

- Zustand：只负责登录态、当前用户、当前学期
- TanStack Query：负责 Topics 的列表与详情服务器状态
- 页面局部状态：只保留 `selectedTopicId`

## 接口范围与契约约束

### 题目列表

使用：

- `GET /api/v1/topics`

本轮前端应至少附带以下查询参数：

- `term_id=currentTerm.id`
- `page=1`
- `page_size=50`

必要时可保留契约中的 `status`、`teacher_id`、`q` 作为后续扩展空间，但本轮不实现筛选与搜索 UI。

返回体是分页列表，`items` 中每一项都符合 `Topic` 契约。

### 题目详情

使用：

- `GET /api/v1/topics/{topic_id}`

详情区必须以服务端 `Topic` 返回结果为真源，不再沿用本地 mock 详情。

### Topic 契约重点字段

根据 `spec/contract.yaml`，本轮重点消费以下字段：

- `id`
- `title`
- `summary`
- `requirements`
- `tech_keywords`
- `capacity`
- `selected_count`
- `teacher_id`
- `term_id`
- `status`
- `portrait.keywords`
- `llm_keyword_job_status`
- `created_at`
- `updated_at`

其中：

- `status` 为业务状态，枚举值为 `draft | pending_review | published | rejected | closed`
- `llm_keyword_job_status` 才是异步任务状态，枚举值沿用 `pending | running | done | failed`

本轮不应把 `Topic.status` 误当成异步轮询状态。

## 页面交互设计

### 整体结构

页面继续保持当前 `/app/topics` 单路由和双栏布局：

- 左栏：题目浏览列表
- 右栏：题目详情摘要

不新增 `/app/topics/:topicId` 路由，避免在这一轮扩大范围。

### 页面初始化流

1. 页面进入 `/app/topics`
2. 拉取当前学期题目列表
3. 若列表非空且当前没有选中项，默认选中第一条
4. 以 `selectedTopicId` 请求题目详情
5. 右栏展示真实详情数据

### 切换题目流

1. 用户点击左侧列表项
2. 页面更新 `selectedTopicId`
3. 请求新的题目详情
4. 右栏切换为新题目内容

### 空状态流

1. 若列表为空，左栏展示“暂无题目”
2. 若未选中题目，右栏展示“请选择题目”
3. 若详情暂时不可用，右栏展示错误块和重试入口

## 数据流设计

### 列表数据

新增 `useTopicsQuery(enabled, termId)`：

- 由登录态和当前学期驱动
- 请求 `/topics`
- 返回分页后的前端模型列表

### 详情数据

新增 `useTopicQuery(topicId, enabled)`：

- 由当前 `selectedTopicId` 驱动
- 请求 `/topics/{topic_id}`
- 不做轮询

### 选中行为

页面只维护一个本地状态：

- `selectedTopicId: string | null`

行为约束：

- 列表从无到有时，如果当前未选中，自动选中第一条
- 当前已选中的题目仍存在于列表中时，不应被新的列表响应重置
- 若列表变为空，选中项清空

## 展示规则

### 左栏列表

每个题目项建议展示：

- 标题
- 摘要
- `techKeywords`
- 状态标签
- `selectedCount / capacity`

列表强调“浏览与对比”，不加入复杂操作按钮。

### 右栏详情

详情区建议展示：

- 标题
- 题目状态
- 摘要
- 研究要求
- 技术关键词
- 容量与当前已选人数
- 教师 ID
- 学期 ID
- 最近更新时间

如果 `portrait.keywords` 存在，可单独展示为“系统抽取关键词”；若不存在，则只展示 `techKeywords`。

如果 `llmKeywordJobStatus` 存在，可作为轻量辅助信息展示，如：

- `pending`：关键词抽取待处理
- `running`：关键词抽取进行中
- `done`：关键词抽取已完成
- `failed`：关键词抽取失败

但该状态不是本轮主视觉，也不触发自动轮询。

## 前端数据建模

参考 Documents 当前做法，本轮在 feature 边界完成 DTO 到前端模型的映射。

推荐新增：

- `TopicDto`
- `Topic`
- `TopicPortraitDto`
- `TopicPortrait`
- `PaginatedResponseDto<T>`
- `PaginatedResponse<T>`

映射规则：

- 后端 snake_case 字段映射为前端 camelCase
- 页面与工具函数只消费前端模型
- API 层返回已映射的数据，不让页面直接感知 DTO

## 状态与文案映射

本轮建议将 `Topic.status` 映射为以下中文标签：

- `draft` -> 草稿
- `pending_review` -> 待审核
- `published` -> 可选题
- `rejected` -> 已驳回
- `closed` -> 已关闭

本轮推荐优先展示 `published`、`closed`、`pending_review` 的业务含义，而不是机械回显英文状态。

## 错误处理

前端继续统一适配 `ErrorEnvelope`。

### 列表区错误

- 列表加载失败时，左栏展示 `EmptyState`
- 提供“重试”按钮
- 页面右栏不应因列表失败而渲染崩坏

### 详情区错误

- 详情加载失败时，右栏展示 `EmptyState`
- 提供“重试”按钮
- 若已存在旧详情缓存，可按现有 Query 行为自然显示缓存；本轮不额外设计复杂保留逻辑

### 空数据提示

- 列表为空：提示当前学期暂无可浏览题目
- 无选中项：提示从左侧选择一个题目

## UI 变化要求

本轮不重做整体视觉，只在现有 Topics 骨架上替换为真实状态。

重点要求：

- 保持“学术生产力工作台”的浅色、克制、理性风格
- 左栏卡片更像研究主题浏览，而不是后台表格
- 右栏详情应适合答辩演示时讲解“研究内容、要求、容量、状态”
- 页面天然为后续接入志愿提交留出空间，但本轮不提前放操作按钮

## 文件结构设计

推荐新增与修改如下：

```text
frontend/src/
  features/
    topics/
      topics.api.ts
      topics.queries.ts
      topics.types.ts
      topics.utils.ts
      topics.utils.test.ts
  pages/
    topics/topics-page.tsx
```

职责边界如下：

- `topics.types.ts`：定义 DTO、前端模型与映射函数
- `topics.api.ts`：处理 `/topics` 相关 HTTP 请求
- `topics.queries.ts`：组织列表与详情 Query
- `topics.utils.ts`：放状态标签、容量文案、关键词选择等纯函数
- `topics.utils.test.ts`：覆盖纯函数行为
- `topics-page.tsx`：负责 UI 组合与页面局部状态

## 测试策略

本轮继续采用“轻量单测 + 构建验证”的方式。

建议覆盖：

- `topics.utils.ts`
- DTO 到前端模型的关键映射
- 状态标签、容量展示、关键词来源选择

强验证包括：

- `cd frontend && npm run test -- --run`
- `cd frontend && npm run build`

若后端本地可运行，再补最小人工验证：

- 登录后进入 `/app/topics`
- 列表可正常加载
- 首条题目自动选中
- 点击其他题目后详情切换正常
- 列表和详情错误态均有重试入口

## 风险与缓解

### 风险一：把 Topic 业务状态误当作异步状态

缓解方式：

- 明确区分 `status` 与 `llm_keyword_job_status`
- 本轮不为 `Topic.status` 增加轮询逻辑

### 风险二：页面继续依赖 mock 数据

缓解方式：

- 页面改为以 `/topics` 与 `/topics/{topic_id}` 为唯一数据真源
- 删除或停止使用现有 `topics.mock.ts`

### 风险三：列表与详情字段命名混乱

缓解方式：

- 在 feature 边界统一做 snake_case 到 camelCase 映射
- 页面只消费前端模型

### 风险四：当前学期未带入查询导致结果失真

缓解方式：

- 列表请求默认附带 `currentTerm.id`
- 将“当前学期”作为页面辅助信息显式展示

## 验收标准

本轮完成后，应满足以下条件：

1. `/app/topics` 不再依赖 mock 题目数据
2. 页面可真实加载当前学期题目列表
3. 页面可真实加载单个题目详情
4. 页面默认选中首个题目
5. 用户点击左侧题目后，右侧详情可正确切换
6. 列表和详情的加载失败都有明确错误反馈与重试入口
7. `npm run test -- --run` 通过
8. `npm run build` 通过

## 最终建议

Round 5 最合适的实现范围，是把 `Topics` 做成“真实列表 + 真实详情”的展示主链路，而不是提前扩展到志愿提交或推荐结果。

这样做有三个好处：

1. 与当前用户确认的范围完全一致
2. 能快速补齐工作台的“选题浏览”核心体验
3. 为下一轮接入志愿提交或推荐能力保留清晰边界

在 `Chat` 与 `Documents` 之后，这一轮会让前端工作台的“学术交流、文档处理、选题浏览”三条答辩主线更加完整。
