# LLM 编排唯一入口（`use_cases`）

> **P0 台账**：与 `architecture.spec.md` **R-UC-ONLY** 一致；**修改 `app/use_cases/**` 时须同步更新本表**。

| 用例域 | `app.use_cases` 入口（模块.可调用符号） | 调用方（`service` / `task/*_jobs`） | 备注 |
|--------|------------------------------------------|--------------------------------------|------|
| Chat 异步回复 | `chat_orchestration`（实现后填写具体函数名） | `ChatService`、`task/chat_jobs` | 仅 Worker 路径调 LLM |
| 文献分块/多段 | `document_pipeline`（实现后填写） | `DocumentService`、`task/document_jobs` | 与 `DocumentJobPayload.stage` 对齐 |
| 课题关键词 LLM | `topic_keywords`（实现后填写） | `task/keyword_jobs` | Topic 写路径 |

**占位说明**：实现阶段将上述「实现后填写」替换为 **真实 import 路径**；**CI** 运行 `scripts/ci/check_llm_entrypoints_doc.py` 校验本文件存在且含表格分隔符。

## Worker 编排入口（非 LLM；满足 W4 `*_jobs` → `use_cases`）

> 与 **`docs/arch/ADR-reconcile-jobs-and-w4.md`** 一致；**不调** `adapter.llm`。

| 用例域 | `app.use_cases` 入口（模块.可调用符号） | 调用方（`task/*_jobs`） | 备注 |
|--------|------------------------------------------|-------------------------|------|
| 志愿对账 | `selection_reconcile`（实现后填写具体函数名） | `task/reconcile_jobs` | 仅 DB 对账与观测写回 |
