# 前端 Round 4：Documents 联调设计文档

## 背景

当前仓库中的 `frontend/` 已完成两轮关键推进：

- Round 1：独立前端工程、应用壳与静态页面骨架
- Round 3：真实登录与 Chat 主链路联调

其中 `/app/documents` 已具备适合答辩演示的静态版式，但仍未接入真实文档任务接口。后端在 `spec/contract.yaml` 中已经明确了 Documents 相关契约，核心路径包括：

- `POST /api/v1/document-tasks`
- `GET /api/v1/document-tasks`
- `GET /api/v1/document-tasks/{task_id}`

同时，文档任务与聊天任务一样，都遵循统一异步状态：

- `pending`
- `running`
- `done`
- `failed`

因此，本轮最合适的推进方式，是把 Documents 这条异步主线从静态骨架推进到可真实演示的“上传受理 -> 状态推进 -> 结果回写”链路。

## 目标

在现有 `frontend/` 基础上，完成 `/app/documents` 的真实联调，并满足以下目标：

1. 支持真实上传 PDF 到 `POST /api/v1/document-tasks`
2. 支持加载真实任务列表
3. 支持加载单任务详情
4. 对当前选中任务执行状态驱动轮询
5. 上传成功后自动选中新任务并进入详情轮询
6. 在现有页面结构中明确呈现 `pending / running / done / failed`
7. 保持与 `spec/contract.yaml` 一致，不擅自扩展冲突字段

## 非目标

本轮明确不做：

- 不重做登录与 Chat 逻辑
- 不接入 Dashboard 真实统计
- 不接入 Topics / Taskboard 真实数据
- 不实现 Documents SSE 或 WebSocket
- 不实现多文件批量上传队列
- 不实现复杂后台并发调度面板
- 不做完整契约代码生成

## 范围

本轮仅覆盖：

- `/app/documents`
- 文档任务上传
- 文档任务列表
- 文档任务详情
- 文档任务状态驱动轮询

不扩散到其他页面。

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

状态职责延续 Round 3 的思路：

- Zustand：只保留登录态、用户摘要、当前学期
- TanStack Query：承接 Documents 的上传、列表、详情、轮询
- 页面局部状态：只保留 `selectedTaskId`、上传表单临时值、轻量错误提示

## 接口范围与契约约束

### 上传任务

使用：

- `POST /api/v1/document-tasks`

请求格式必须为 `multipart/form-data`，且遵守契约：

- `file`：必填
- `term_id`：必填
- `task_type`：可选，枚举 `summary | conclusions | compare`
- `language`：可选，枚举 `zh | en`

本轮建议在前端给出 `task_type` 与 `language` 的轻量可选项，但默认值必须符合契约语义：

- `task_type = summary`
- `language = zh`

成功时服务端返回 `202` 和完整 `DocumentTask`。

### 任务列表

使用：

- `GET /api/v1/document-tasks`

前端必须以 `DocumentTaskListItem` 为展示真源，不擅自发明与契约冲突的列表字段。重点展示：

- `id`
- `filename`
- `status`
- `current_stage`
- `task_type`
- `created_at`
- `updated_at`
- `result_preview`

### 单任务详情

使用：

- `GET /api/v1/document-tasks/{task_id}`

前端必须以 `DocumentTask` 为详情真源。重点消费以下字段：

- `id`
- `term_id`
- `status`
- `filename`
- `task_type`
- `language`
- `current_stage`
- `progress`
- `artifacts`
- `last_completed_chunk`
- `result.summary`
- `result.bullet_points`
- `result.raw_model`
- `error_code`
- `error_message`
- `retry_count`

## 页面交互设计

### 顶部上传区

页面顶部保留目前的“上传 PDF”视觉入口，但改为真实上传表单。

交互要求：

1. 用户选择 PDF 文件
2. 用户可选 `task_type` 与 `language`
3. 前端自动附带当前学期 `term_id`
4. 提交上传时按钮进入 loading 状态
5. 成功后立即：
   - 刷新任务列表
   - 自动选中新任务
   - 进入该任务详情轮询

上传成功后的默认行为已经明确为“自动聚焦新任务”，不需要再让用户手动到列表中查找。

### 左侧任务列表

左侧列表负责承接用户的任务概览与切换入口。

展示要求：

- 文件名优先展示
- 状态徽标醒目展示
- `current_stage` 用于体现当前推进环节
- `result_preview` 若存在，可作为二级信息
- 点击任意任务后，右侧切换到该任务详情

列表不承载复杂操作按钮，本轮以“浏览与切换”为主。

### 右侧任务详情

右侧详情区负责承接：

- 当前任务基础信息
- 当前主状态
- 当前阶段信息
- 处理结果
- 失败反馈

展示建议：

1. 顶部卡片显示 `filename`、`task_type`、`language`、主状态
2. 中部用阶段信息块展示 `current_stage`、`last_completed_chunk`、`retry_count`
3. 结果区展示 `result.summary` 与 `result.bullet_points`
4. 若任务失败，单独展示 `error_code`、`error_message`

详情区要明显比列表更强地表现异步状态变化，因为这里是答辩演示时的主观察面板。

## 数据流设计

### 页面初始化流

1. 页面进入 `/app/documents`
2. 拉取当前用户任务列表
3. 若列表非空，默认选中首个任务
4. 拉取该任务详情
5. 若该任务状态为 `pending` 或 `running`，启动轮询

### 上传流

1. 用户选择 PDF 并提交
2. 前端请求 `POST /api/v1/document-tasks`
3. 服务端返回 `202` 与 `DocumentTask`
4. 前端立即：
   - 清理上传表单临时状态
   - 将该任务设为 `selectedTaskId`
   - 刷新任务列表
   - 拉取该任务详情
5. 若返回状态为 `pending` 或 `running`，自动开始轮询

### 切换任务流

1. 用户点击左侧列表项
2. 页面更新 `selectedTaskId`
3. 请求该任务详情
4. 若该任务未到终态，则继续轮询

### 详情轮询流

1. 当前选中任务详情请求返回 `status`
2. 若状态为 `pending` 或 `running`，继续轮询
3. 若状态为 `done` 或 `failed`，停止轮询
4. 轮询期间适度刷新任务列表，以保持左侧概览同步

## 轮询策略

轮询规则必须写死为：

- `pending`：继续轮询
- `running`：继续轮询
- `done`：停止轮询
- `failed`：停止轮询

轮询只针对“当前选中的任务详情”执行，不对整个任务列表做高频轮询。

列表刷新策略：

- 上传成功后刷新一次
- 详情轮询期间可同步失效列表 query
- 但列表不作为主轮询对象

这样可以兼顾：

- 详情区状态实时性
- 列表区状态同步
- 实现复杂度可控

## 错误处理

前端继续统一适配 `ErrorEnvelope`。

### 上传区错误

- `413`：文件超限，提示 PDF 超出服务端限制
- `429`：系统繁忙或策略限流，提示稍后重试
- `503`：任务暂时无法受理，提示队列或服务不可用
- `VALIDATION_ERROR`：提示表单或上传参数不合法
- 其他错误：提示通用上传失败

### 列表区错误

- 列表加载失败时展示可重试错误块
- 不让页面完全空白

### 详情区错误

- 详情加载失败时展示错误提示与重试入口
- 任务 `failed` 时必须展示：
  - `error_code`
  - `error_message`

失败态不能只靠一个红色徽标表达，必须把失败原因显性写出来。

## UI 变化要求

本轮不重做视觉风格，只在现有 Documents 页面骨架上做真实状态替换。

重点要求：

- 上传按钮体现提交中状态
- 列表中不同任务状态有明确层次
- 详情区对 `pending / running / done / failed` 的展示过渡明确
- `done` 时结果区自然展开
- `failed` 时错误信息显式且不被结果区覆盖

页面整体依然保持“学术生产力工作台”的浅色、克制、理性风格，不做上传中心式后台表格感。

## 文件结构设计

推荐新增与修改如下：

```text
frontend/src/
  features/
    documents/
      documents.api.ts
      documents.queries.ts
      documents.types.ts
      documents.utils.ts
  pages/
    documents/documents-page.tsx
```

职责边界如下：

- `documents.types.ts`：只定义契约映射类型与轻量上传参数类型
- `documents.api.ts`：只处理 `/document-tasks` 相关 HTTP 请求
- `documents.queries.ts`：只组织 Query / Mutation / Polling
- `documents.utils.ts`：只放纯函数，如终态判断与结果提取
- `documents-page.tsx`：只做 UI 组合，不直接拼装底层请求逻辑

## 测试策略

本轮继续采用“轻量单测 + 强验证”的方式。

建议新增最小单测覆盖：

- `documents.utils.ts`
- 文档上传表单数据构造函数（若单独抽离）
- 文档结果提取或状态判断函数

强验证包括：

- `npm run test -- --run`
- `npm run build`
- 真实上传一个 PDF
- 验证任务自动进入列表
- 验证上传成功后自动选中新任务
- 验证 `pending / running / done / failed` 轮询规则正确

## 风险与缓解

### 风险一：上传参数与契约不一致

缓解方式：

- 严格按 `multipart/form-data` 与 `term_id/file/task_type/language` 提交

### 风险二：详情结果结构为空或尚未生成

缓解方式：

- `result` 允许为空
- 在 `pending/running` 时明确展示“结果尚未生成”

### 风险三：轮询只看详情导致列表不更新

缓解方式：

- 在详情轮询成功时同步失效列表 query

### 风险四：失败态展示不足

缓解方式：

- 明确将 `error_code` 与 `error_message` 放进详情区单独错误块

## 验收标准

本轮完成后，应满足以下条件：

1. 用户可在 `/app/documents` 真实上传 PDF
2. 上传成功后返回的新任务会被自动选中
3. 页面可加载真实任务列表
4. 页面可加载真实任务详情
5. 当前选中任务会按 `pending / running / done / failed` 做状态驱动轮询
6. 到终态后轮询停止
7. `done` 时能展示 `summary` 与 `bullet_points`
8. `failed` 时能展示失败原因
9. `npm run build` 通过

## 最终建议

Round 4 最合适的实现范围，是把 Documents 做成完整主链路联调：

- 上传
- 列表
- 详情
- 轮询

这样可以与 Round 3 的登录与 Chat 形成两条最有答辩说服力的异步能力主线：一条是“对话生成”，一条是“文档处理”。两者都完整跑通后，前端工作台就已经具备较强的演示完成度。
