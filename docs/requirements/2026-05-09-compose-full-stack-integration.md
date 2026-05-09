# Compose 全量前后端联调说明

本文档记录“AI 学术助手工作台”的本地全量联调方式，覆盖 PostgreSQL、Redis、Flask web、worker 和 Vite 前端。

## 一键启动

在仓库根目录执行：

```powershell
.\scripts\start_full_stack_demo.ps1
```

如果需要分开控制后端与前端，使用：

```powershell
.\scripts\start_backend_demo.ps1
.\scripts\start_frontend_demo.ps1
```

脚本默认行为：

- 使用 Docker Compose 启动 `postgres`、`redis`、`web`、`worker`。
- 生成临时 compose override，将 Flask 容器发布到宿主机 `5051`。
- 初始化演示数据，默认会重置 compose PostgreSQL 表结构和演示数据。
- 启动 Vite 前端到 `http://127.0.0.1:5189`。
- 执行后端 API 烟测和前端 `/api/v1` proxy 烟测。

## 默认访问地址

- 后端：`http://127.0.0.1:5051`
- 前端：`http://127.0.0.1:5189`
- 健康检查：`http://127.0.0.1:5051/health`

为什么不用 `5000`：本机开发时可能已有旧 Flask 服务占用或抢答 `127.0.0.1:5000`，会造成联调假阳性。脚本默认使用 `5051` 避开串台。

## 演示账号

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 学生 | `api-login-user` | `correct-pass` |
| 教师 | `teacher-demo` | `teacher-pass` |
| 管理员 | `admin-demo` | `admin-pass` |

## 演示数据

脚本会写入以下稳定数据：

- 学期：`term-2026-spring`
- 学生：`user-student-demo`
- 教师：`user-teacher-demo`
- 题目：`topic-1`
- 志愿：`application-1`
- 指导关系：`assignment-1`
- 里程碑：`milestone-1`

这些数据用于验证 dashboard、topics、taskboard 和 selection 相关页面的真实接口联通。

## 常用参数

```powershell
# 指定端口
.\scripts\start_full_stack_demo.ps1 -BackendPort 5051 -FrontendPort 5189

# 只启动后端 compose，不启动前端
.\scripts\start_full_stack_demo.ps1 -SkipFrontend

# 启动并播种，但跳过烟测
.\scripts\start_full_stack_demo.ps1 -SkipSmoke

# 保留已有数据，只补齐或更新演示种子
.\scripts\start_full_stack_demo.ps1 -KeepData
```

分离脚本常用参数：

```powershell
.\scripts\start_backend_demo.ps1 -BackendPort 5051 -KeepData
.\scripts\start_frontend_demo.ps1 -BackendUrl http://127.0.0.1:5051 -FrontendPort 5189
```

## 手动前端启动

如果只想单独启动前端：

```powershell
.\scripts\start_frontend_demo.ps1 -BackendUrl http://127.0.0.1:5051
```

前端 Axios 使用相对路径 `/api/v1`，Vite proxy 会把请求转发到 `VITE_API_PROXY_TARGET`。

## 停止环境

脚本结束时会打印停止命令，默认是：

```powershell
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" down
```

如果需要同时删除 Postgres volume，可追加 `-v`。谨慎使用，因为会删除本地 compose 数据：

```powershell
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" down -v
```

## 验证点

脚本烟测覆盖：

- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `GET /api/v1/topics`
- `GET /api/v1/recommendations/topics`
- `GET /api/v1/applications`
- `GET /api/v1/assignments`
- `GET /api/v1/milestones`
- `POST /api/v1/conversations`
- `POST /api/v1/conversations/{conversation_id}/messages`
- `GET /api/v1/chat/jobs/{job_id}`
- 前端同源 `/api/v1/auth/login` proxy
- 前端同源 `/api/v1/users/me` proxy

聊天链路中，`POST /messages` 应返回 `202`，assistant 初始状态为 `pending`，worker 消费后 `chat_job.status` 应进入 `done` 或 `failed` 终态。

当前默认 `LLM_PROVIDER=mock`，mock LLM 返回空内容。因此验证重点是异步受理、队列消费和状态终态，而不是生成文本质量。

## 常见问题

### 登录命中了错误用户

如果 `127.0.0.1:5000` 上还有旧 Flask 进程，直接访问 `5000` 可能打到旧服务。使用脚本默认的 `5051`，并确保前端 `VITE_API_PROXY_TARGET` 指向 `http://127.0.0.1:5051`。

### Docker Desktop 未启动

先启动 Docker Desktop，再运行：

```powershell
docker version
docker compose version
```

两条命令都能正常输出后，再执行联调脚本。

### 首次启动很慢

当前 compose 使用 `python:3.11-slim` 并在容器启动时安装依赖。首次拉取镜像和安装依赖会较慢，后续会快一些。答辩前建议提前运行脚本预热环境。

### 前端端口已被占用

换一个端口：

```powershell
.\scripts\start_full_stack_demo.ps1 -FrontendPort 5190
```

### 保留数据联调

默认会重置演示数据。如果要保留已有 compose 数据：

```powershell
.\scripts\start_full_stack_demo.ps1 -KeepData
```
