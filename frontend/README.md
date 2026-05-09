# Frontend

AI 学术助手工作台前端，使用 Vite + React + TypeScript。开发环境通过 Vite proxy 访问后端 `/api/v1`，推荐配合仓库根目录的全量联调脚本使用。

## Full-Stack Demo

在仓库根目录运行：

```powershell
.\scripts\start_full_stack_demo.ps1
```

也可以先启动后端，再单独启动前端：

```powershell
.\scripts\start_backend_demo.ps1
.\scripts\start_frontend_demo.ps1
```

默认访问：

- Frontend: `http://127.0.0.1:5189`
- Backend: `http://127.0.0.1:5051`
- Student: `api-login-user / correct-pass`
- Teacher: `teacher-demo / teacher-pass`

详细说明见 [`../docs/requirements/2026-05-09-frontend-operation-readme.md`](../docs/requirements/2026-05-09-frontend-operation-readme.md) 和 [`../docs/requirements/2026-05-09-compose-full-stack-integration.md`](../docs/requirements/2026-05-09-compose-full-stack-integration.md)。

## Run Frontend Only

```bash
npm install
npm run dev
```

如需指定后端代理目标：

```powershell
.\scripts\start_frontend_demo.ps1 -BackendUrl http://127.0.0.1:5051 -FrontendPort 5189
```

## Build

```bash
npm run build
```
