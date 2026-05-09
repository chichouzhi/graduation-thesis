# 毕业设计（后端契约与分层）

规范与契约见 **`spec/`** 目录：**[`spec/contract.yaml`](spec/contract.yaml)**、**[`spec/architecture.spec.md`](spec/architecture.spec.md)**、**[`spec/execution_plan.md`](spec/execution_plan.md)**。

**文档索引**：[`docs/README.md`](docs/README.md) · **分类总目**：[`docs/DOCUMENT-CATALOG.md`](docs/DOCUMENT-CATALOG.md)  
**目录约定**：`spec/`（规范真源）· `docs/requirements/`（需求提炼）· `docs/architecture/`（系统架构）· `docs/tasks/`（任务 DAG + `todolist.md`）· `docs/arch/`（ADR，路径勿改）

## 启动与联调

一键启动完整演示环境（PostgreSQL、Redis、Flask web、worker、Vite 前端）：

```powershell
.\scripts\start_full_stack_demo.ps1
```

分开启动：

```powershell
.\scripts\start_backend_demo.ps1
.\scripts\start_frontend_demo.ps1
```

默认端口：后端 `http://127.0.0.1:5051`，前端 `http://127.0.0.1:5189`。详细说明见 [`docs/requirements/2026-05-09-compose-full-stack-integration.md`](docs/requirements/2026-05-09-compose-full-stack-integration.md)、[`docs/requirements/2026-05-09-backend-operation-readme.md`](docs/requirements/2026-05-09-backend-operation-readme.md)、[`docs/requirements/2026-05-09-frontend-operation-readme.md`](docs/requirements/2026-05-09-frontend-operation-readme.md)。
