# 前端运行与实际操作文档

本文档说明如何启动前端、连接真实后端、完成页面操作验证，以及如何排查代理问题。

## 前端组成

前端位于 `frontend/`，技术栈为 Vite、React、TypeScript、React Router、TanStack Query、Zustand、Axios、Tailwind CSS 和 shadcn/ui 风格组件。

前端 Axios 使用相对路径 `/api/v1`，开发环境由 Vite proxy 转发到真实后端。默认后端代理目标是 `http://127.0.0.1:5051`。

## 推荐启动方式

先启动后端：

```powershell
.\scripts\start_backend_demo.ps1
```

再启动前端：

```powershell
.\scripts\start_frontend_demo.ps1
```

默认前端地址：

```text
http://127.0.0.1:5189
```

## 常用命令

```powershell
# 指定后端和前端端口
.\scripts\start_frontend_demo.ps1 -BackendUrl http://127.0.0.1:5051 -FrontendPort 5189

# 后端暂时不可用时，只启动页面
.\scripts\start_frontend_demo.ps1 -SkipBackendCheck -SkipProxySmoke
```

## 手动启动方式

```powershell
cd frontend
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:5051"
npm run dev -- --host 127.0.0.1 --port 5189
```

## 页面操作路径

访问：

```text
http://127.0.0.1:5189/login
```

学生账号：

```text
api-login-user / correct-pass
```

教师账号：

```text
teacher-demo / teacher-pass
```

建议演示顺序：

1. 登录学生账号，进入 `/app/dashboard` 查看近期工作、指导关系和任务状态。
2. 进入 `/app/topics` 查看题目列表、题目详情和推荐结果。
3. 进入 `/app/chat` 发送一条消息，观察异步 assistant 占位和任务状态。
4. 进入 `/app/documents` 查看文档任务状态区域。
5. 进入 `/app/taskboard` 查看并操作里程碑。
6. 切换教师账号，进入 `/app/topics` 查看教师侧题目和志愿处理入口。

## 验证前端代理

脚本会自动验证：

- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`

如果需要手动验证：

```powershell
$login = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5189/api/v1/auth/login `
  -ContentType "application/json" `
  -Body (@{ username = "api-login-user"; password = "correct-pass" } | ConvertTo-Json)

Invoke-RestMethod `
  -Method Get `
  -Uri http://127.0.0.1:5189/api/v1/users/me `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

返回的 `id` 应为 `user-student-demo`。

## 质量检查

在 `frontend/` 下执行：

```powershell
npm run lint
npm run build
npx vitest run --maxWorkers 1 --minWorkers 1
```

当前存在 React `act(...)` 测试环境 warning，但测试应通过。

## 常见问题

### 登录后数据不对

确认前端代理指向的是 `5051`。如果旧 Vite 进程仍在运行，停止后重新执行：

```powershell
.\scripts\start_frontend_demo.ps1 -BackendUrl http://127.0.0.1:5051
```

### 页面能打开但接口失败

先检查后端：

```powershell
Invoke-RestMethod http://127.0.0.1:5051/health
```

如果后端未启动，执行：

```powershell
.\scripts\start_backend_demo.ps1
```

### 前端端口冲突

```powershell
.\scripts\start_frontend_demo.ps1 -FrontendPort 5190
```
