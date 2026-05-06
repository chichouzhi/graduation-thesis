# 前端 Round 1：应用壳与静态骨架设计文档

## 背景

当前仓库已有 Flask 后端、异步聊天与异步文档处理能力，以及位于 `spec/contract.yaml` 的接口契约真源，但仓库下尚未存在独立前端工程。

已有总设计文档已经明确产品定位为“AI 学术助手工作台”，并建议前端按多轮次推进。本设计文档进一步收敛到第一轮实施范围，只覆盖：

- `frontend/` 独立前端工程初始化
- 应用壳布局
- 核心路由
- 学生端静态页面骨架

本轮目标不是联调接口，而是先把适合答辩演示的产品骨架搭稳。

## 目标

在仓库根目录下新增独立前端项目 `frontend/`，使用 React 技术栈实现一套可运行的学生端工作台骨架，并满足以下目标：

1. 项目可以本地启动并完成页面路由跳转。
2. 页面风格符合“AI 学术助手工作台”定位，而不是通用后台模板。
3. `dashboard`、`chat`、`documents` 三个核心页面能直接支撑后续演示链路。
4. 目录结构清晰，便于下一轮接入真实接口与异步状态逻辑。

## 非目标

本轮明确不做以下内容：

- 不接真实后端接口
- 不实现真实登录
- 不实现聊天发送、PDF 上传、任务轮询等业务逻辑
- 不完成契约类型的全量映射
- 不扩展教师端或管理员端多角色视角
- 不在本轮引入复杂状态机、权限系统或表单体系

## 用户视角

本轮默认采用学生端答辩演示视角，所有静态内容围绕“当前学期下，学生如何使用 AI 学术助手推进毕业设计工作”组织。

页面中的假数据应体现以下语义：

- 当前用户为学生
- 存在当前学期上下文
- 聊天、文档、选题、任务看板都属于“我的工作空间”
- 聊天和文档页要预留异步状态展示空间，便于下一轮接入 `pending / running / done / failed`

## 技术方案

前端项目采用以下技术栈：

- React
- Vite
- TypeScript
- React Router
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand
- Axios

本轮只完成这些依赖的基础接线与使用入口，不进行复杂业务封装。

## 目录结构

前端工程放置于：

```text
frontend/
```

推荐目录如下：

```text
frontend/
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  postcss.config.js
  tailwind.config.ts
  components.json
  src/
    app/
      app.tsx
      providers.tsx
      store.ts
      styles.css
    routes/
      index.tsx
      protected-layout.tsx
    pages/
      login/
        login-page.tsx
      dashboard/
        dashboard-page.tsx
      chat/
        chat-page.tsx
      documents/
        documents-page.tsx
      topics/
        topics-page.tsx
      taskboard/
        taskboard-page.tsx
    components/
      layout/
        app-shell.tsx
        app-sidebar.tsx
        app-header.tsx
        page-section.tsx
      shared/
        stat-card.tsx
        status-badge.tsx
        empty-state.tsx
        section-heading.tsx
      ui/
        ...
    features/
      auth/
        auth-store.ts
      dashboard/
        dashboard.mock.ts
      chat/
        chat.mock.ts
      documents/
        documents.mock.ts
      topics/
        topics.mock.ts
      taskboard/
        taskboard.mock.ts
    data/
      student-workspace.ts
    lib/
      axios.ts
      utils.ts
    types/
      app.ts
    main.tsx
```

目录边界约束如下：

- `app/` 只负责全局装配，不承担业务细节。
- `routes/` 只负责路由表与布局承载。
- `pages/` 作为页面组合层，不直接堆放大量共享基础组件。
- `components/layout/` 负责应用壳与结构布局。
- `components/shared/` 放跨页面的轻量展示组件。
- `features/*/*.mock.ts` 负责各页面的假数据来源，后续可平滑替换为真实 `api.ts` 与 `queries.ts`。
- `data/student-workspace.ts` 负责集中导出学生端答辩演示假数据与页面文案基线。

## 路由设计

本轮固定实现以下路由：

```text
/login
/app/dashboard
/app/chat
/app/documents
/app/topics
/app/taskboard
```

路由行为约束如下：

- `/login` 为独立入口页。
- `/app/*` 路由挂载在统一应用壳下。
- 登录按钮仅做前端假跳转，点击后进入 `/app/dashboard`。
- 左侧导航按展示优先级排序：
  1. Dashboard
  2. Chat
  3. Documents
  4. Topics
  5. Taskboard

## 应用壳设计

### 左侧导航

左侧导航承担模块切换与产品识别职责，设计要求：

- 顶部展示产品名称与短说明，如“Academic Copilot / AI 学术助手工作台”
- 导航项按演示顺序排列
- 当前路由有明显激活态
- 底部可放置学生身份摘要或学期信息

### 顶部栏

顶部栏承担页面上下文说明，设计要求：

- 左侧显示当前页面标题与一句辅助说明
- 右侧显示当前学期、学生身份标签、轻量头像入口
- 不采用重后台风格的密集工具栏

### 主内容区

主内容区应提供宽松但有层次的信息画布，要求：

- 页面整体以浅色主题为主
- 使用柔和背景层次，而不是单一纯白平面
- 通过区块、边框、阴影与留白建立阅读节奏

## 视觉方向

本轮视觉方向定义如下：

- 产品定位为“学术生产力工作台”
- 主色调采用纸张白、暖灰、石板灰与深青绿点缀
- 避免蓝紫科技风与通用 admin 模板观感
- 避免夸张 landing page Hero
- 使用克制的圆角、细边框和轻阴影建立质感

设计重点应聚焦在：

- 首页概览层次
- 聊天消息流的阅读感
- 异步状态标签
- 文档任务与结果卡片

## 页面骨架设计

### `/login`

目标是提供完整产品入口，但不做真实认证。

页面元素：

- 品牌标题与一句产品说明
- 学号或用户名输入框
- 密码输入框
- 登录按钮
- 一段简短提示文案，说明这是学生端工作台入口

交互行为：

- 点击登录后进入 `/app/dashboard`

### `/app/dashboard`

目标是作为答辩演示起点页，展示学生近期工作总览。

页面结构：

- 顶部欢迎区，展示当前阶段与工作建议
- 第一行统计卡片：会话数、文档任务数、进行中任务、本周完成数
- 第二行：左侧“近期工作”，右侧“异步任务状态总览”
- 第三行：最近活动、快捷入口

内容语义：

- 强调“最近在做什么”
- 强调“哪些 AI 任务仍在处理中”
- 强调“接下来去哪里继续工作”

### `/app/chat`

目标是预留后续异步聊天联调所需的完整版式。

页面结构：

- 左侧：会话列表
- 中间：消息流
- 右侧：当前会话摘要与状态说明
- 底部：输入区

静态内容要求：

- 至少展示一组用户消息与 assistant 回复
- assistant 消息中明确出现 `pending`、`running`、`done`、`failed` 样式示例
- 会话列表应体现“最近讨论主题”

本轮不实现消息发送，仅保留输入框与发送按钮视觉入口。

### `/app/documents`

目标是预留后续异步文档处理联调所需的完整版式。

页面结构：

- 顶部：上传入口与说明区
- 左侧：文档任务列表
- 右侧：当前任务详情、阶段状态、总结结果卡片

静态内容要求：

- 任务列表中体现不同状态任务
- 详情区域体现阶段、进度、摘要、失败提示等占位
- 结果卡片应适合后续承接 `summary`、`bullet_points` 等字段概念，但本轮不与契约强绑定

### `/app/topics`

目标是展示系统在毕业选题场景中的业务覆盖度。

页面结构：

- 顶部说明区
- 题目卡片列表
- 右侧或下方详情摘要

静态内容要求：

- 体现题目标题、摘要、要求、关键词、容量等信息层次
- 页面更像“选题辅助浏览”，而不是普通表格管理页

### `/app/taskboard`

目标是展示系统支持毕业过程管理。

页面结构：

- 顶部说明区
- 阶段列视图或纵向时间线
- 各阶段下放任务卡片

静态内容要求：

- 任务覆盖开题、调研、实现、论文、答辩准备等阶段
- 体现任务状态、截止时间、优先级等基础信息

## 数据策略

本轮全部使用静态假数据，不接真实接口。

数据组织要求：

- 每个页面的展示数据放在对应 `features/*/*.mock.ts`
- 可在 `data/student-workspace.ts` 汇总导出统一的演示上下文
- 字段命名尽量贴近 `spec/contract.yaml` 的语义，但不强制建立完整契约类型映射

## 状态策略

本轮只做轻量状态接线：

- Zustand 仅保留假登录态、当前用户摘要、当前学期摘要
- TanStack Query 完成 provider 装配，但不承担真实拉取任务
- Axios 只建立基础实例与后续扩展入口

明确不做：

- 真正的服务端缓存
- 状态驱动轮询
- 统一错误恢复流程

## 与后续轮次的衔接

本轮需要为后续联调预留稳定边界：

1. 下一轮可继续提升视觉完成度，而不改路由结构。
2. 聊天页与文档页版式要能自然容纳异步状态流。
3. 后续可在 `features/chat`、`features/documents` 下新增 `api.ts`、`queries.ts`，替换当前 mock 数据来源。
4. 统一的 `status-badge` 可直接承接 `pending / running / done / failed`。

## 风险与约束

### 风险一：过度工程化

如果这轮提前实现完整 API 层、复杂状态层和权限体系，会明显超出需求并增加返工成本。

缓解方式：

- 本轮只做应用壳、路由和静态骨架。

### 风险二：页面风格退化为通用后台

如果直接套用常见 admin 模板结构，答辩时产品辨识度会不足。

缓解方式：

- 在视觉、排版和内容组织上持续强调“学术工作台”而非“企业后台”。

### 风险三：后续异步能力无承载空间

如果聊天页和文档页只是静态占位，没有为状态流和结果视图预留区域，下一轮联调会被迫重构页面。

缓解方式：

- 本轮即按异步任务展示需求规划版式。

## 验收标准

本轮完成后，应满足以下验收条件：

1. `frontend/` 可独立安装依赖并启动开发服务器。
2. 所有目标路由均可正常访问。
3. `/app/*` 页面共享统一应用壳。
4. `dashboard`、`chat`、`documents`、`topics`、`taskboard` 都有清晰的静态骨架与学生端假数据。
5. 整体视觉呈现为浅色、理性、干净且有层次的“AI 学术助手工作台”。
6. 代码目录清晰，便于下一轮继续接入真实 API。

## 最终建议

本轮最合适的推进方式，是先在 `frontend/` 中搭建一套学生端“AI 学术助手工作台”骨架，用清晰路由、稳定应用壳和高可读的静态页面，把答辩演示主线先立起来。

在这套骨架稳定后，再按后续轮次接入真实登录、聊天异步任务、文档异步任务和状态驱动轮询，会明显更稳，也更容易控制演示质量。
