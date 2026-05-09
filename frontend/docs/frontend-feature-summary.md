# 前端功能梳理与答辩演示说明

本文档用于说明当前前端已经完成的功能、对应后端契约、答辩演示链路和后续风险。前端定位是“AI 学术助手工作台”，重点不是通用后台管理，而是围绕毕业设计选题匹配、AI 分析和过程跟踪形成完整论文逻辑。

## 当前实现范围

### 应用基础

- 已基于 React、Vite、TypeScript、React Router、TanStack Query、Zustand、Axios、Tailwind CSS 和 shadcn/ui 风格组件搭建独立前端。
- 前端位于 `frontend/`，与 Flask 后端解耦。
- 已建立应用壳：左侧导航、顶部栏、主内容区。
- 已实现基础认证态存储、受保护路由和错误信息适配。

### 页面完成情况

- `/login`：登录入口，支持保存认证态。
- `/app/dashboard`：工作台首页，聚合题目、文档、任务、聊天和指导关系数据。
- `/app/chat`：异步聊天页面，支持会话、消息、聊天 job 状态轮询。
- `/app/documents`：文档任务页面，支持 PDF 任务列表、详情和状态驱动轮询。
- `/app/topics`：选题核心页面，包含题目浏览、老师分析、学生推荐、学生志愿、教师处理志愿。
- `/app/taskboard`：毕业过程任务看板，支持里程碑列表、创建、状态更新、删除，并能按指导关系学生查看任务。

## 核心论文逻辑

当前系统已经形成一条完整的毕业设计选题闭环：

1. 老师录入毕业设计题目。
2. 后端大模型或分析逻辑生成题目画像，包括难度、能力要求、关键词、风险和适合学生类型。
3. 学生维护个人画像，包括兴趣、技能、关键词、目标和每周投入时间。
4. 系统基于学生画像和题目画像返回可解释推荐。
5. 学生从推荐题目中提交第一或第二志愿。
6. 老师在题目分析页查看学生志愿，并接受或拒绝。
7. 接受后形成指导关系。
8. Dashboard 展示指导关系和答辩演示链路。
9. Taskboard 按指导关系中的学生查看和维护毕业过程任务。

这条链路回应了老师提出的问题：选题系统不能只是盲目匹配，而要让大模型能力对应毕业设计选题中的真实需求。当前前端把“大模型分析题目”和“学生画像推荐”放在同一条业务闭环里，能在答辩中说明系统的必要性和可解释性。

## 已接入接口

接口字段以 `spec/contract.yaml` 为准，前端 DTO 保持 snake_case，页面模型使用 camelCase。

### Auth / Users

- 用户登录和认证态保存。
- `GET /users/me`：读取当前用户及学生画像。
- `PATCH /users/me`：保存学生画像，用于后续推荐。

### Topics / Recommendations

- `GET /topics`：读取当前学期题目列表。
- `GET /topics/{topic_id}`：读取题目详情。
- `POST /topics`：老师创建题目。
- `PATCH /topics/{topic_id}`：老师更新题目。
- `GET /recommendations/topics`：基于学生画像和题目画像返回推荐题目。

### Selection

- `GET /applications`：读取学生志愿或指定题目的志愿列表。
- `POST /applications`：学生提交题目志愿。
- `PATCH /applications/{application_id}`：更新志愿优先级。
- `DELETE /applications/{application_id}`：撤销志愿。
- `POST /applications/{application_id}/decisions`：老师接受或拒绝志愿。
- `GET /assignments`：读取当前用户相关指导关系。

### Taskboard

- `GET /milestones`：读取里程碑列表；老师查看指导学生时使用 `student_id` 参数。
- `POST /milestones`：创建毕业过程里程碑。
- `PATCH /milestones/{milestone_id}`：更新里程碑状态。
- `DELETE /milestones/{milestone_id}`：删除里程碑。

### Chat / Documents

- 聊天 job 和文档 task 均按 pending、running、done、failed 处理。
- 轮询由状态驱动，进入 done 或 failed 后停止。
- Dashboard 已聚合聊天会话、文档任务和里程碑状态。

## 关键页面说明

### Dashboard

Dashboard 是答辩时的首屏，强调“学术生产力工作台”而不是后台模板。

- 展示当前重点、统计卡片、近期工作、异步状态总览、快捷入口。
- 展示“答辩演示链路”，把系统价值讲成四步：老师题目画像、学生画像推荐、教师接受志愿、任务看板跟踪。
- 展示指导关系，让老师接受志愿后的结果能直接在首页看到。

### Topics

Topics 是论文创新点最集中的页面。

- 题目浏览：查看当前学期题目、容量和关键词。
- 老师分析：录入或导入题目，展示题目画像结果。
- 学生推荐：保存学生画像后请求推荐结果。
- 志愿提交：学生可提交第一或第二志愿。
- 志愿处理：老师查看当前题目的学生志愿，并接受或拒绝。

### Taskboard

Taskboard 用于把选题结果落到毕业设计过程管理。

- 显示指导课题上下文。
- 若存在指导关系，默认按该指导关系的学生 ID 查询里程碑。
- 支持任务创建、状态流转和删除。
- 保持与契约一致，没有擅自给 milestone 请求增加 `assignment_id` 或 `topic_id`。

### Chat / Documents

Chat 和 Documents 展示后端异步能力。

- Chat 展示异步聊天 job 状态和消息流。
- Documents 展示 PDF 处理任务状态、进度和结果预览。
- 两者都为后续论文问答、文献总结和过程材料沉淀预留空间。

## 答辩演示建议

建议按下面顺序演示，逻辑会比较顺：

1. 打开 Dashboard，说明系统不是通用后台，而是 AI 学术助手工作台。
2. 指出“答辩演示链路”，先讲完整业务闭环。
3. 进入 Topics 的老师分析，展示题目画像如何把老师题目转成结构化需求。
4. 切到学生推荐，展示学生画像如何驱动推荐和解释。
5. 提交志愿，再回到老师分析页处理志愿。
6. 回到 Dashboard，展示指导关系已经形成。
7. 进入 Taskboard，说明后续毕业设计过程可以按指导学生持续跟踪。
8. 补充 Documents 和 Chat，说明系统还覆盖文档处理和学术问答等辅助能力。

## 当前验证情况

最近一轮已通过：

- `npm run lint`
- `npm run build`
- `npx vitest run --maxWorkers 1 --minWorkers 1`

当前测试覆盖重点：

- Dashboard 聚合数据和答辩链路展示。
- Topics 题目画像、学生推荐、志愿提交、教师接受志愿。
- Taskboard 里程碑创建、状态更新、删除、按指导关系学生查看任务。
- Selection DTO 映射，包括 Application、Assignment 和 Decision response。
- Chat、Documents、Topics、Taskboard 的工具函数和轮询判断。

测试运行中仍存在一个既有的 React `act(...)` 环境警告，当前不影响测试结果，但后续可以单独清理测试环境配置。

## 剩余风险与建议

### 建议优先补充

- 补一轮真实后端联调记录，记录每个核心接口的请求、响应和异常情况。
- 在 Topics 页面继续拆分大组件，当前页面功能较多，后续维护成本会上升。
- 给 Dashboard 和 Topics 增加更明确的加载错误重试路径，提升答辩演示稳定性。
- 清理测试环境中的 `act(...)` 警告，减少评审时的噪音。

### 暂不建议扩展

- 暂不建议给 milestone 增加前端自定义关联字段，因为当前契约没有 `assignment_id` 或 `topic_id`。
- 暂不建议引入复杂权限 UI，当前以当前用户身份和后端权限校验为主。
- 暂不建议把选题系统拆成独立微前端；毕业设计答辩更需要链路完整和演示顺畅。

## 结论

当前前端已经具备答辩演示的核心闭环：老师题目分析、学生画像推荐、志愿处理、指导关系、任务看板、异步聊天和文档处理。后续重点不是继续堆页面，而是做真实联调、稳定性收口和论文表述整理。
