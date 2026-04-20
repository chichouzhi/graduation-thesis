# LLM 编排唯一入口（`use_cases`）

> **P0 台账**：与 `architecture.spec.md` **R-UC-ONLY** 一致；**修改 `app/use_cases/**` 时须同步更新本表**。

| 用例域 | `app.use_cases` 入口（模块.可调用符号） | 调用方（`service` / `task/*_jobs`） | 备注 |
|--------|------------------------------------------|--------------------------------------|------|
| Chat 异步回复 | `chat_orchestration.run_turn`（LLM）、`chat_orchestration.build_messages`（组装+粗估 token 裁剪）、`trim_messages_to_token_budget` / `total_tokens_for_messages`（可选复用） | `ChatService`、`task/chat_jobs` | 预算默认 `Config.CHAT_CONTEXT_TOKEN_BUDGET`（`CHAT_CONTEXT_TOKEN_BUDGET`）；`build_messages` 无 IO/LLM；`run_turn` 仅 Worker 调 LLM |
| 文献分块/多段 | `document_pipeline.expand_default_document_job_plan`、`format_document_job_idempotency_key`、`chunk_summarize_waves`、`resolve_document_chunk_max_parallel` 等 | `DocumentService`、`task/pdf_parse_jobs`、`task/document_jobs` | 与 `DocumentJobPayload.stage` / `chunk_index` 对齐；并行度默认 `Config.DOCUMENT_CHUNK_MAX_PARALLEL`（`DOCUMENT_CHUNK_MAX_PARALLEL`） |
| 课题关键词 LLM | `topic_keywords.run_keyword_extraction`、`topic_keywords.run_keyword_extraction_from_payload`、`topic_keywords.build_keyword_extraction_messages` | `task/keyword_jobs`（待接）；Topic 写路径经队列 | 仅 Worker 调 LLM；快照字段对齐 `KeywordJobPayload` |

**占位说明**：实现阶段将上述「实现后填写」替换为 **真实 import 路径**；**CI** 运行 `scripts/ci/check_llm_entrypoints_doc.py` 校验本文件存在且含表格分隔符。

## Worker 编排入口（非 LLM；满足 W4 `*_jobs` → `use_cases`）

> 与 **`docs/arch/ADR-reconcile-jobs-and-w4.md`** 一致；**不调** `adapter.llm`。

| 用例域 | `app.use_cases` 入口（模块.可调用符号） | 调用方（`task/*_jobs`） | 备注 |
|--------|------------------------------------------|-------------------------|------|
| 志愿对账 | `selection_reconcile.reconcile_assignments`（由 `task.reconcile_jobs.run` 注入 `session`） | `task/reconcile_jobs` | ``selected_count`` 与 active ``assignments`` 对齐；不调 LLM |
