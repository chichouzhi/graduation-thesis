# 规范真源（`spec/`）

本目录为仓库 **契约与门禁、交付计划** 的单一存放处（原在仓库根目录）。

| 文件 | 说明 |
|------|------|
| [contract.yaml](./contract.yaml) | OpenAPI：REST、错误体、异步任务与队列 payload |
| [architecture.spec.md](./architecture.spec.md) | 分层、禁止/必须规则、CI 矩阵 |
| [execution_plan.md](./execution_plan.md) | 四域 × 阶段交付与验收表述 |

**引用约定**：脚本与测试请使用 `Path(repo_root) / "spec" / "文件名"`，勿再假定三份文件在仓库根。

返回 [文档索引](../docs/README.md) · [分类总目](../docs/DOCUMENT-CATALOG.md)
