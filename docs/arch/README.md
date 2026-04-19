# 架构决策与入口表（`docs/arch/`）

本目录为 **ADR** 与 **LLM 编排入口表** 等运维/评审真源。

**注意**：`llm_entrypoints.md` 及部分 ADR 路径被 **`spec/architecture.spec.md`**、**`scripts/ci/check_llm_entrypoints_doc.py`** 等硬编码引用，**请勿整体搬迁目录或改名**，除非同步修改 CI 与规格。

| 文件 | 说明 |
|------|------|
| [ADR-document-pdf-parse-to-document-jobs.md](./ADR-document-pdf-parse-to-document-jobs.md) | `pdf_parse` → `document_jobs` |
| [ADR-reconcile-jobs-and-w4.md](./ADR-reconcile-jobs-and-w4.md) | `reconcile_jobs` 与 W4 |
| [ADR-W3b-uc-enqueue.md](./ADR-W3b-uc-enqueue.md) | W3b UC 入队 |
| [llm_entrypoints.md](./llm_entrypoints.md) | LLM 编排唯一入口（R-UC-ONLY） |

返回 [文档索引](../README.md)
