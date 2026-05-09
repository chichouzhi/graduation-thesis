# 后端运行与实际操作文档

本文档面向本地开发和答辩演示，说明如何启动后端真实运行环境、验证接口、查看服务状态和停止服务。

## 后端组成

后端演示环境由 Docker Compose 启动：

- `postgres`：业务数据库。
- `redis`：队列 broker，同时用于 refresh token 状态。
- `web`：Flask API 服务。
- `worker`：消费 `chat_jobs`、`pdf_parse`、`document_jobs`、`keyword_jobs`、`reconcile_jobs`。

默认后端地址是 `http://127.0.0.1:5051`。脚本不直接使用宿主机 `5000`，避免本机已有 Flask 服务导致接口串台。

## 一键启动后端

在仓库根目录执行：

```powershell
.\scripts\start_backend_demo.ps1
```

脚本会完成：

- 生成临时 compose override：`$env:TEMP\gd-compose-port-5051.yml`。
- 启动 `postgres`、`redis`、`web`、`worker`。
- 等待 `/health` 返回 `healthy`。
- 默认重置并写入演示数据。
- 执行后端 API 烟测。

## 常用命令

```powershell
# 指定后端端口
.\scripts\start_backend_demo.ps1 -BackendPort 5051

# 保留已有数据库数据，只补齐演示种子
.\scripts\start_backend_demo.ps1 -KeepData

# 只启动服务，不写入演示数据
.\scripts\start_backend_demo.ps1 -SkipSeed

# 启动并播种，但跳过烟测
.\scripts\start_backend_demo.ps1 -SkipSmoke
```

## 演示账号

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 学生 | `api-login-user` | `correct-pass` |
| 教师 | `teacher-demo` | `teacher-pass` |
| 管理员 | `admin-demo` | `admin-pass` |

## 手动验证接口

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:5051/health
```

登录并调用当前用户接口：

```powershell
$login = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5051/api/v1/auth/login `
  -ContentType "application/json" `
  -Body (@{ username = "api-login-user"; password = "correct-pass" } | ConvertTo-Json)

Invoke-RestMethod `
  -Method Get `
  -Uri http://127.0.0.1:5051/api/v1/users/me `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

选题列表：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:5051/api/v1/topics?term_id=term-2026-spring&page=1&page_size=10" `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

## 查看状态和日志

```powershell
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" ps
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" logs --tail=100 web
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" logs --tail=100 worker
```

## 停止后端

保留数据库 volume：

```powershell
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" down
```

删除数据库 volume：

```powershell
docker compose -f docker-compose.yml -f "$env:TEMP\gd-compose-port-5051.yml" down -v
```

## 注意事项

- 默认 `LLM_PROVIDER=mock`，聊天 worker 会进入终态，但 mock 内容可能为空。
- 首次运行会拉镜像并在容器内安装依赖，耗时较长；答辩前建议提前预热。
- 如果端口冲突，使用 `-BackendPort 5052`，并让前端脚本的 `-BackendUrl` 同步指向新端口。
