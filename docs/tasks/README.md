# 架构任务图（`docs/tasks/`）

| 文件 | 说明 |
|------|------|
| [architecture-task-graph.json](./architecture-task-graph.json) | 原子任务 DAG（`depends_on` = 前置边） |
| [architecture-task-graph.md](./architecture-task-graph.md) | 分层可读版（**由脚本生成**，勿手改） |
| [todolist.md](./todolist.md) | 数据模型与域实现清单（与 JSON 任务图互补） |

```bash
python scripts/gen_architecture_task_graph_md.py
```

返回 [文档索引](../README.md) · [系统架构](../architecture/system-architecture.md)
